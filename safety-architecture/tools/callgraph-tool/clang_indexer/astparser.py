#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import re

import logging
import importlib
import importlib.util
import ctypes

import utils

###############################################################################

_LOGGER = logging.getLogger(utils.LOGGER_NAME)

###############################################################################


def set_clang_bindings_and_lib(bindings, libclang):
    if not bindings:
        raise ValueError("Invalid bindings file: %s" % bindings)
    _LOGGER.debug("Setting python bindings: %s" % bindings)

    # Raise ImortError if clang.cindex module was loaded from somewhere else
    # prior to calling this function
    if 'clang.cindex' in sys.modules:
        raise ImportError(
            "Module 'clang.cindex' has been loaded outside astparser.py")

    # Import the python bindings to global scope
    cindex_path = os.path.join(os.path.dirname(bindings), '..')
    sys.path.insert(0, cindex_path)
    import clang.cindex as cindex
    global cl
    cl = cindex

    # Set libclang library file
    if not libclang:
        raise ValueError("Invalid libclang file: %s" % libclang)
    _LOGGER.debug("Setting libclang: %s" % libclang)
    cl.Config.set_compatibility_check(True)
    cl.Config.set_library_file(libclang)


###############################################################################

class AstParser():

    def __init__(self, compdb, append_arg="", srcfile=None, projroot=None, exclude=None):
        if 'cl' not in globals():
            raise ImportError(
                "Attempt to intialize AstParser prior to importing module "
                "clang.cindex")
        self.compdbpath = os.path.dirname(os.path.abspath(compdb))
        self.projroot = projroot if projroot else self.compdbpath
        self.append_args = list(append_arg.split(" "))
        self.append_args = [x for x in self.append_args if x]
        self.srcfile = srcfile
        self.indexed = set()
        self.conf = cl.Config()
        self.lib = self.conf.lib
        self._register_clang_functions()
        self.callback = None
        exclude = exclude.split(',') if exclude else []
        self.exclude = [self.projroot + '/' + ex for ex in exclude]

        cxstring = self.lib.clang_getClangVersion()
        version = self.lib.clang_getCString(cxstring)
        _LOGGER.info("Using %s" % version)
        _LOGGER.debug("Using python bindings: %s" % str(cl))

    def _register_clang_functions(self):
        function_name = "clang_getClangVersion"
        _LOGGER.debug("Registering: %s" % function_name)
        function = getattr(self.lib, "clang_getClangVersion")
        function.restype = cl._CXString

    def walk_tree(self, callback):
        assert callback is not None
        self.callback = callback
        # Paths in compile_commands.json are relative so we need to chdir
        cwd = os.getcwd()
        os.chdir(self.compdbpath)
        self._parse()
        # Change working directory back to where it was
        os.chdir(cwd)

    def get_ast_tree(self):
        ast_tree = AstTree()
        self.ast_tree = ast_tree
        self.walk_tree(self._build_ast_tree)
        self.ast_tree = None
        return ast_tree

    def _build_ast_tree(self, clang_node, treenode_parent=None):
        if self.is_indexed(str(clang_node.location.file)):
            return

        # Add new treenode
        treenode = self.ast_tree.add_astnode(clang_node, treenode_parent)
        treenode = treenode if treenode else treenode_parent

        # Recursively iterate all clang_node children
        children = list(clang_node.get_children())
        for child in children:
            self._build_ast_tree(clang_node=child, treenode_parent=treenode)

    def _parse(self):
        index = cl.Index.create()
        compdb = cl.CompilationDatabase.fromDirectory(self.compdbpath)
        if self.srcfile:
            commands = compdb.getCompileCommands(self.srcfile)
        else:
            commands = compdb.getAllCompileCommands()

        blacklist_args = []

        for cc in commands:
            # Don't process if file is blacklisted
            filepath = cc.directory + '/' + cc.filename
            if utils.blacklist_file(filepath, self.exclude):
                _LOGGER.info(f"Skipping blacklisted file: {filepath}")
                continue

            # Arguments from compdb
            arglist = [arg for arg in cc.arguments]
            # Additional arguments from command line
            arglist = arglist + self.append_args
            # Remove first argument (cc)
            arglist.pop(0)

            # Parse index
            tu = self._parse_index(index, arglist, blacklist_args)
            if tu:
                self.callback(tu.cursor)
                self._mark_indexed(tu.get_includes())

    def is_indexed(self, filename):
        return filename in self.indexed

    def _mark_indexed(self, includes):
        for fileinc in includes:
            self.indexed.add(fileinc.include.name)

    def _parse_index(self, index, arglist, blacklist_args):
        # Blacklist using the current blacklist_args list
        arglist = utils.filter_list(arglist, blacklist_args)

        # Try to parse
        try:
            # None for filename - it's already in the arglist
            tu = index.parse(None, args=arglist)
        except cl.TranslationUnitLoadError:
            _LOGGER.warning("Parsing translation unit failed: %s" % arglist[-1])
            return

        _LOGGER.info("Translation unit: %s" % tu.spelling)

        # Check for diagnostics errors
        RE_UNKNOWN_ARG = re.compile(r'.*error: unknown argument: \'(?P<arg>.*)\'$')
        RE_UNSUPPORTED_OPT = re.compile(
            r'.*error: unsupported option \'(?P<arg>.*)\' for target')
        RE_ERROR = re.compile(r'.*error:(?P<error>.*)')
        reparse = False
        diagnostics = list(tu.diagnostics)
        for diag in diagnostics:
            diag_str = str(diag)
            match = None

            # Add new unknown args to blacklist
            if not match:
                match = RE_UNKNOWN_ARG.match(diag_str)
                if match:
                    unknown_arg = match.group('arg')
                    _LOGGER.info("Adding unknown arg: %s" % unknown_arg)
                    blacklist_args.append(unknown_arg)
                    reparse = True

            # Add new unsupported args to blacklist
            if not match:
                match = RE_UNSUPPORTED_OPT.match(diag_str)
                if match:
                    unsupported_arg = match.group('arg')
                    _LOGGER.info("Adding unsupported arg: %s" % unsupported_arg)
                    blacklist_args.append(unsupported_arg)
                    reparse = True

            # Other errors are fatal
            if not match:
                match = RE_ERROR.match(diag_str)
                if match:
                    _LOGGER.debug("Error parsing translation unit: \"%s\"" %
                                  diag_str)

        if reparse:
            # Try to parse again with the new arglist
            _LOGGER.info("Reparsing: %s" % tu.spelling)
            return self._parse_index(index, arglist, blacklist_args)
        else:
            return tu


################################################################################

def intern(s):
    if s is not None and type(s) in [str]:
        return sys.intern(s)
    return s


class AstNode():
    def __init__(self, clang_node=None):
        # TODO: there must be a better way to do this
        if not clang_node:
            self.kind = None
            self.filename = None
            self.line = None
            self.col = None
            self.name = None
            self.usr = None
            self.hash = None
            self.debug_str = None
            return

        cn = clang_node
        self.kind = cn.kind.value
        self.filename = intern(str(cn.location.file))
        self.line = cn.location.line
        self.col = cn.location.column
        self.name = intern(cn.spelling) if cn.spelling else intern(cn.displayname)
        self.usr = intern(cn.get_usr())
        self.hash = intern(self._hash())
        self.debug_str = None

    def _hash(self):
        return "%s:%s:%s:%s:%s:%s" % (
            self.kind,
            self.filename,
            self.line,
            self.col,
            self.name,
            self.usr)

    def dbg(self):
        if not self.debug_str:
            s = str(cl.CursorKind._kinds[self.kind]) if self.kind else ""
            if self.name:
                s += " '%s'" % self.name
            if self.usr:
                s += " [usr = %s]" % self.usr
            s += " <%s:%s:%s>" % (self.filename, self.line, self.col)
            self.debug_str = intern(s)
        return self.debug_str


class TreeNode():
    def __init__(self, astnode, treenode_parent=None, treenode_referenced=None):
        # AstNode object for storing the node data
        self.astnode = astnode
        # Parent TreeNode object
        self.parent = treenode_parent
        # List of children TreeNode objects
        self.children = []
        # TreeNode object this node references to
        self.referenced = treenode_referenced
        # TreeNode objects that reference this node
        self.referrers = []
        # Debug string for debugging
        self.debug_str = None

    def add_child(self, treenode):
        self.children.append(treenode)

    def add_referrer(self, treenode):
        self.referrers.append(treenode)

    def dbg(self):
        if not self.debug_str:
            s = self.astnode.dbg()
            if self.referenced:
                s += " [ref = %s]" % self.referenced.astnode.usr
            self.debug_str = intern(s)
        return self.debug_str

    def walk_descendants(self):
        """Depth-first preorder walk over the TreeNode descendants"""
        for child in self.children:
            yield child
            for descendant in child.walk_descendants():
                yield descendant

    def walk_ancestors(self):
        """Walk over the TreeNode ancestors until root is reached"""
        if self.parent:
            yield self.parent
            for ancestor in self.parent.walk_ancestors():
                yield ancestor

    def find_first_ancestor(self, kinds):
        _LOGGER.log(
            utils.LOG_SPAM, "kind=%s node=%s" % (kinds, self.dbg()))
        parent = self.parent
        while parent is not None:
            if parent.astnode.kind in kinds:
                return parent
            parent = parent.parent
        _LOGGER.log(utils.LOG_SPAM, "Ancestor not found")
        return None

    def find_descendants(self, kinds):
        _LOGGER.log(
            utils.LOG_SPAM, "kind=%s node=%s" % (kinds, self.dbg()))
        ret_list = []
        for child in self.walk_descendants():
            if child.astnode.kind in kinds:
                ret_list.append(child)
        return ret_list

    def find_referrers(self, kinds):
        _LOGGER.log(
            utils.LOG_SPAM, "kind=%s node=%s" % (kinds, self.dbg()))
        ret_list = []
        for referrer in self.referrers:
            if referrer.astnode.kind in kinds:
                ret_list.append(referrer)
        return ret_list

    def find_first_child_leaf(self):
        _LOGGER.log(utils.LOG_SPAM, self.dbg())
        children = self.children
        while children:
            if not children[0].children:
                return children[0]
            else:
                children = children[0].children
        return self

    def find_first_ref(self):
        _LOGGER.log(utils.LOG_SPAM, self.dbg())
        if self.referenced:
            return self.referenced
        children = self.children
        while children:
            if children[0].referenced:
                return children[0].referenced
            else:
                children = children[0].children
        return None

    def find_var_value_at(self, call_expr, field_decl, init=True):
        _LOGGER.log(
            utils.LOG_SPAM, "self=%s call_expr=%s" % (
                self.dbg(), call_expr.dbg()))
        if field_decl:
            _LOGGER.log(
                utils.LOG_SPAM, "field_decl=%s" % field_decl.dbg())
            assert field_decl.astnode.kind == cl.CursorKind.FIELD_DECL.value

        if (self.astnode.kind != cl.CursorKind.VAR_DECL.value and
                self.astnode.kind != cl.CursorKind.PARM_DECL.value):
            _LOGGER.log(utils.LOG_SPAM, "Unexpected self.astnode")
            return None

        ret = None
        if init:
            if (call_expr.referenced.astnode.kind == cl.CursorKind.FUNCTION_DECL.value and
                    field_decl):
                ret = self._find_field_init_value(field_decl)
            elif call_expr.referenced.astnode.kind == cl.CursorKind.FUNCTION_DECL.value:
                ret = self._find_var_init_value()
            elif call_expr.referenced.astnode.kind == cl.CursorKind.FIELD_DECL.value:
                ret = self._find_field_init_value(call_expr.referenced)
            elif call_expr.referenced.astnode.kind == cl.CursorKind.VAR_DECL.value:
                ret = self._find_var_init_value()
            else:
                _LOGGER.log(utils.LOG_SPAM, "Unexpected call_expr.referenced")
                return None

        # Find locations that might have changed the value after init
        # looking backwards from the location closest to call_expr
        kinds = [cl.CursorKind.DECL_REF_EXPR.value]
        for referrer in reversed(self.referrers):
            if referrer.astnode.kind not in kinds:
                # Reject if kinds don't match
                continue
            elif referrer.astnode.filename != call_expr.astnode.filename:
                # Reject if filenames don't match
                continue
            elif referrer.astnode.line > call_expr.astnode.line:
                # Reject if referrer line is after the before_node
                continue
            elif (referrer.astnode.line == call_expr.astnode.line and
                    referrer.astnode.col > call_expr.astnode.col):
                # Reject if referrer column is after the before_node
                continue
            elif (referrer.astnode.line == call_expr.astnode.line and
                    referrer.astnode.col == call_expr.astnode.col):
                # Reject if referrer is on the same location (same node?)
                continue
            elif referrer._is_assignment():
                return referrer._find_assignment_rval()
        if ret is None:
            _LOGGER.log(utils.LOG_SPAM, "returning None")
        return ret

    def _find_var_init_value(self):
        _LOGGER.log(utils.LOG_SPAM, self.dbg())
        refs = self.find_descendants(kinds=[cl.CursorKind.DECL_REF_EXPR.value])
        if len(refs) == 0:
            return None
        # We expect VAR_DECL init to have exactly one DECL_REF_EXPR
        if len(refs) > 1:
            _LOGGER.log(utils.LOG_SPAM, "expecting VAR_DECL with one DECL_REF_EXPR")
            return None

        return refs[0]

    def _find_field_init_value(self, field_decl):
        _LOGGER.log(utils.LOG_SPAM, self.dbg())
        if (self.astnode.kind != cl.CursorKind.VAR_DECL.value and
                self.astnode.kind != cl.CursorKind.PARM_DECL.value):
            return None
        init_list = self.find_descendants(
            kinds=[cl.CursorKind.INIT_LIST_EXPR.value])
        if len(init_list) == 0:
            return None
        if len(init_list) > 1:
            _LOGGER.log(utils.LOG_SPAM, "expecting one INIT_LIST_EXPR")
            return None
        init_list_expr = init_list[0]

        # Find the field_decl order in the struct
        fieldmap = {}
        type_ref = self.find_first_child_leaf()
        if type_ref.astnode.kind != cl.CursorKind.TYPE_REF.value:
            _LOGGER.log(utils.LOG_SPAM, "expecting TYPE_REF")
            return None

        decl = type_ref.referenced
        field_order = 0
        found_it = False
        for child in decl.children:
            if child.astnode.kind != cl.CursorKind.FIELD_DECL.value:
                continue
            fieldmap[child] = field_order
            if child == field_decl:
                found_it = True
                break
            field_order += 1

        if not found_it:
            _LOGGER.log(utils.LOG_SPAM, "failed to find field_order")
            return None

        if len(init_list_expr.children) <= 0:
            _LOGGER.log(utils.LOG_SPAM, "empty init_list_expr")
            return None

        # Find the field_order:th value in the struct initialization
        init_order = 0
        for init in init_list_expr.children:
            if (init.children and
                    len(init.children) >= 1 and
                    init.children[0].astnode.kind == cl.CursorKind.MEMBER_REF.value):
                member_ref = init.children[0]
                init_order = fieldmap.get(member_ref.referenced, None)
                if init_order is None:
                    _LOGGER.warn("Init_order not found: %s" % init.dbg())
                    return None
            if init_order == field_order:
                assert len(init.children) >= 1
                if init.children[0].astnode.kind == cl.CursorKind.MEMBER_REF.value:
                    assert len(init.children) == 2
                    init = init.children[1]
                field_val = init.find_first_child_leaf()
                _LOGGER.log(utils.LOG_SPAM, "found it: %s" % field_val.dbg())
                return field_val
            init_order += 1
        return None

    def _is_assignment(self):
        _LOGGER.log(utils.LOG_SPAM, self.dbg())
        # TODO: this is dubious: We should see if libclang provides a function
        # that could be used for this instead
        binop = self.find_first_ancestor(kinds=[cl.CursorKind.BINARY_OPERATOR.value])
        if (binop is not None):
            return True
        else:
            return False

    def _find_assignment_rval(self):
        _LOGGER.log(utils.LOG_SPAM, self.dbg())
        # TODO: this is dubious: We should see if libclang provides a function
        # that could be used for this instead
        binop = self.find_first_ancestor(kinds=[cl.CursorKind.BINARY_OPERATOR.value])
        call_exprs = binop.find_descendants(kinds=[cl.CursorKind.CALL_EXPR.value])
        if call_exprs and len(call_exprs) > 0:
            _LOGGER.log(utils.LOG_SPAM, "CALL_EXPR in assignment not supported")
            return None
        refs = binop.find_descendants(kinds=[cl.CursorKind.DECL_REF_EXPR.value])
        # TODO: support for chained assignments (a = b = c)?
        # assert len(refs) == 2
        return refs[-1]


class AstTree():
    def __init__(self):
        # Key: AstNode.hash, Value: Astnode object
        self.astnode_tree = {}
        # Key: AstNode.hash, Value: Treenode object (USRs)
        self.usrnode_tree = {}
        # List of root TreeNode objects, one for each translation unit
        self.tu_heads = []
        # Only add node kinds we actually need, i.e.:
        # grep -r -oE "CursorKind\.[A-Z_]{5,}\b" *.py | cut -d":" -f2 | sort | uniq
        self.include_kinds = [
            cl.CursorKind.BINARY_OPERATOR.value,
            cl.CursorKind.CALL_EXPR.value,
            cl.CursorKind.DECL_REF_EXPR.value,
            cl.CursorKind.FIELD_DECL.value,
            cl.CursorKind.FUNCTION_DECL.value,
            cl.CursorKind.INIT_LIST_EXPR.value,
            cl.CursorKind.MEMBER_REF.value,
            cl.CursorKind.PARM_DECL.value,
            cl.CursorKind.STRUCT_DECL.value,
            cl.CursorKind.TRANSLATION_UNIT.value,
            cl.CursorKind.TYPE_REF.value,
            cl.CursorKind.VAR_DECL.value,
        ]

    def add_astnode(self, clang_node, treenode_parent=None):
        if self._can_ignore_clang_node(clang_node, treenode_parent):
            return None

        astnode = AstNode(clang_node)

        # If the same astnode object (as defined by astnode.hash) already
        # exists, simply refrence to the earlier data
        if astnode.hash in self.astnode_tree:
            astnode = self.astnode_tree[astnode.hash]
        else:
            self.astnode_tree[astnode.hash] = astnode
        # If this astnode has a reference, get the referenced treenode
        treenode_referenced = self._get_referenced_treenode(clang_node, astnode)
        # Create a new treenode
        treenode = TreeNode(astnode, treenode_parent, treenode_referenced)
        # Add USR node to usrnode_tree
        if astnode.usr:
            self.usrnode_tree[astnode.hash] = treenode
        # Add treenode as a child to its parent
        if treenode_parent:
            treenode_parent.add_child(treenode)
        # Add treenode as a referrer to referenced treenode
        if treenode_referenced:
            treenode_referenced.add_referrer(treenode)
        # If this astnode is TRANSLATION_UNIT, add it to the tu_heads
        if astnode.kind == cl.CursorKind.TRANSLATION_UNIT.value:
            self.tu_heads.append(treenode)
        return treenode

    def walk_tu_heads(self, callback):
        if not callback:
            raise ValueError("Callback must be set")
        for tu in self.tu_heads:
            callback(tu)

    def _can_ignore_clang_node(self, clang_node, treenode_parent):
        if treenode_parent:
            if treenode_parent.astnode.kind in [
                    cl.CursorKind.INIT_LIST_EXPR.value,
                    cl.CursorKind.CALL_EXPR.value]:
                return False
            if treenode_parent.find_first_ancestor(kinds=[
                    cl.CursorKind.INIT_LIST_EXPR.value]):
                return False
        if clang_node.kind.value in self.include_kinds:
            return False
        else:
            return True

    def _get_referenced_treenode(self, clang_node, astnode):
        # This is a hack: we interpret the INIT_LIST_EXPR semantic parent
        # as a reference to make it possible to later resolve possible
        # indirect call via list initialized array or struct
        clang_node_referenced = None
        if (clang_node.kind == cl.CursorKind.INIT_LIST_EXPR.value and
                clang_node.semantic_parent):
            clang_node_referenced = clang_node.semantic_parent
        else:
            clang_node_referenced = clang_node.referenced

        if not clang_node_referenced:
            return None
        elif clang_node_referenced.get_usr() is None:
            raise ValueError("No USR in referenced: %s" % astnode.dbg())

        astnode_referenced = AstNode(clang_node_referenced)
        if astnode_referenced.hash == astnode.hash:
            # Ignore self-reference
            return None
        if astnode_referenced.hash not in self.usrnode_tree:
            _LOGGER.log(utils.LOG_SPAM, "Referenced not in USR tree: %s" % astnode.dbg())
            return None

        treenode_referenced = self.usrnode_tree[astnode_referenced.hash]
        return treenode_referenced


################################################################################
