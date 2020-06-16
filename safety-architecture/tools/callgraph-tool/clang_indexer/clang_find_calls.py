#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import logging

from enum import Enum, unique, auto
from typing import NamedTuple
import astparser
from astparser import AstNode
import utils

_LOGGER = logging.getLogger(utils.LOGGER_NAME)
_FILEDIR = os.path.dirname(os.path.realpath(__file__))

################################################################################

# TODO: handle clang download in CI
# TODO: add mips support

################################################################################


class StateMachine():
    """Simple state machine implementation."""

    def start(self, startstate, max_state_changes=50):
        """Start running the state machine from function :startstate:.
        :startstate: should return the next state function, or None to
        indicate end of execution. """

        _LOGGER.log(utils.LOG_SPAM, "Starting StateMachine")
        self.state_changes = 0
        self.max_state_changes = max_state_changes
        state = startstate
        while True:
            self.state_changes += 1
            if self.state_changes > self.max_state_changes:
                _LOGGER.warning("Max state changes reached")
                return
            newstate = state()
            if newstate is None:
                _LOGGER.log(utils.LOG_SPAM, "reached end state")
                return
            state = newstate

    def get_remaining_state_changes(self):
        return self.max_state_changes - self.state_changes


class FunctionNameResolver():
    def __init__(self):
        self.statemachine = StateMachine()

    def resolve(self, node):
        assert node is not None
        self.funcname = ""
        self.startnode = node
        self.node = node
        self.statemachine.start(self._funcname_find, max_state_changes=10)
        return self.funcname

    def _funcname_find(self):
        if self.node is None:
            self._funcname_unresolved()

        _LOGGER.log(utils.LOG_SPAM, self.node.dbg())
        next_state = None

        if self.node.astnode.kind is None:
            self.funcname = ""

        elif self.node.astnode.kind == astparser.cl.CursorKind.FUNCTION_DECL.value:
            self.funcname = self.node.astnode.name

        elif self.node.astnode.kind == astparser.cl.CursorKind.FIELD_DECL.value:
            self.funcname = self.node.astnode.name
            next_state = self._funcname_find

        elif self.node.astnode.kind == astparser.cl.CursorKind.STRUCT_DECL.value:
            self.funcname = self.node.astnode.name + "." + self.funcname

        elif self.node.astnode.kind == astparser.cl.CursorKind.VAR_DECL.value:
            self.funcname = self.node.astnode.name

        elif self.node.astnode.kind == astparser.cl.CursorKind.PARM_DECL.value:
            self.funcname = self.node.astnode.name

        elif self.node.astnode.kind == astparser.cl.CursorKind.CALL_EXPR.value:
            self.funcname = self.node.astnode.name

        else:
            self._funcname_unresolved()

        self.node = self.node.parent
        return next_state

    def _funcname_unresolved(self):
        _LOGGER.warn("Failed finding funcname %s" % (
            self.startnode.dbg()))
        self.funcname = ""


class IndirectResolver():
    unknown_node = astparser.TreeNode(astnode=AstNode(clang_node=None))

    def __init__(self):
        self.statemachine = StateMachine()

    def resolve(self, node):
        assert node is not None
        self.startnode = node
        self.node = node
        assert self.node.astnode is not None
        assert self.node.astnode.kind == astparser.cl.CursorKind.CALL_EXPR.value
        self.call_expr = node
        self.resolved = []
        self.statedata = None
        _LOGGER.log(utils.LOG_SPAM, self.node.dbg())
        self.statemachine.start(self._resolve_call_expr, max_state_changes=20)
        return self.resolved

    def _resolve_call_expr(self):
        if self.node is None:
            _LOGGER.warn("_resolve_call_expr: self.node is None")
            return None
        _LOGGER.log(utils.LOG_SPAM, self.node.dbg())
        # First CALL_EXPR child leaf DECL_REF_EXPR specifies the type of
        # call expression
        call_leaf = self.node.find_first_child_leaf()
        assert call_leaf is not None
        if call_leaf.astnode.kind != astparser.cl.CursorKind.DECL_REF_EXPR.value:
            # _LOGGER.error(call_leaf.dbg())
            _LOGGER.log(utils.LOG_SPAM, call_leaf.dbg())
            self._indirect_unresolved_error()
            return None

        next_state = None
        if call_leaf.referenced.astnode.kind != astparser.cl.CursorKind.PARM_DECL.value:
            self.node = call_leaf.referenced
            next_state = self._resolve_nonparam_call
        else:
            self.node = call_leaf.referenced
            next_state = self._resolve_param_call
        return next_state

    def _resolve_nonparam_call(self):
        _LOGGER.log(utils.LOG_SPAM, self.node.dbg())

        if self.node.astnode.kind != astparser.cl.CursorKind.VAR_DECL.value:
            self._indirect_unresolved_error()
            return None

        assert self.call_expr is not None
        field_decl = None
        if self.startnode.referenced.astnode.kind == astparser.cl.CursorKind.FIELD_DECL.value:
            field_decl = self.startnode.referenced
        node = self.node.find_var_value_at(
            call_expr=self.call_expr, field_decl=field_decl)
        if not node:
            self._indirect_unresolved_error()
            return None
        _LOGGER.log(utils.LOG_SPAM, "Node: %s" % self.node.dbg())
        _LOGGER.log(utils.LOG_SPAM, "Location_node: %s" % self.call_expr.dbg())
        _LOGGER.log(utils.LOG_SPAM, "Value: %s" % node.dbg())
        next_state = None
        if node.astnode.kind == astparser.cl.CursorKind.DECL_REF_EXPR.value:
            self.node = node.referenced
            next_state = self._resolve_nonparam_var_ref
        else:
            _LOGGER.log(utils.LOG_SPAM, "Unexpected value: %s" % node.dbg())
            self._indirect_unresolved_error()
            next_state = None
        return next_state

    def _resolve_nonparam_var_ref(self):
        if self.node is None:
            _LOGGER.warn("_resolve_nonparam_var_ref: self.node is None")
            self._indirect_unresolved_error()
            return None

        _LOGGER.log(utils.LOG_SPAM, self.node.dbg())
        if self.node.astnode.kind == astparser.cl.CursorKind.FUNCTION_DECL.value:
            self._add_resolved(self.node)
        else:
            self._indirect_unresolved_error()
        return None

    def _resolve_param_call(self):
        _LOGGER.log(utils.LOG_SPAM, self.node.dbg())

        if self.node.astnode.kind != astparser.cl.CursorKind.PARM_DECL.value:
            self._indirect_unresolved_error()
            return None
        param_decl = self.node

        # See if the value of param was changed in this function
        assert self.call_expr is not None
        field_decl = None
        if self.startnode.referenced.astnode.kind == astparser.cl.CursorKind.FIELD_DECL.value:
            field_decl = self.startnode.referenced
        node = self.node.find_var_value_at(
            call_expr=self.call_expr, field_decl=field_decl, init=False)
        if node:
            if (node.referenced is None):
                _LOGGER.warn("Missing referenced node: %s" % node.dbg())
                return None
            elif (node.astnode.kind == astparser.cl.CursorKind.DECL_REF_EXPR.value and
                    node.referenced.astnode.kind == astparser.cl.CursorKind.PARM_DECL.value):
                param_decl = node.referenced
            elif node.astnode.kind == astparser.cl.CursorKind.DECL_REF_EXPR.value:
                self.node = node.referenced
                return self._resolve_nonparam_var_ref
            else:
                _LOGGER.log(utils.LOG_SPAM, "Unexpected value: %s" % node.dbg())
                self._indirect_unresolved_error()
                return None

        # Otherwise, find the value of PARM_DECL
        function_decl = self.node.parent
        assert param_decl.astnode.kind == astparser.cl.CursorKind.PARM_DECL.value
        assert function_decl.astnode.kind == astparser.cl.CursorKind.FUNCTION_DECL.value

        # Find the PARM_DECL order in the function declaration
        arg_order = 0
        found_it = False
        for child in function_decl.children:
            if child.astnode.kind != astparser.cl.CursorKind.PARM_DECL.value:
                continue
            if child == param_decl:
                found_it = True
                break
            arg_order += 1

        if not found_it:
            self._indirect_unresolved_error()
            return None

        # Find where FUNCTION_DECL is called
        call_exprs = function_decl.find_referrers(
            kinds=[astparser.cl.CursorKind.CALL_EXPR.value])

        # Resolve each found call separately
        call_refs = []
        for call_expr in call_exprs:
            _LOGGER.log(utils.LOG_SPAM, "call_expr: %s" % call_expr.dbg())
            # For each call expression, find the arg_order:th argument
            arg = self._find_call_expr_nth_argument(call_expr, arg_order)
            if arg:
                _LOGGER.log(utils.LOG_SPAM, "arg: %s" % arg.dbg())
                # Append the pair of (call_expr, arg) to call_refs: each pair
                # will be resolved separately
                # We want to know the value of arg when call_expr is called
                call_refs.append({'call_expr': call_expr, 'arg': arg})
            if len(call_refs) > 100:
                # In case there are a too many call_refs
                self._max_call_refs_error()
                break
        next_state = None
        if call_refs:
            self.statedata = call_refs
            next_state = self._resolve_param_call_ref
        else:
            self._indirect_unresolved_error()
            next_state = None
        return next_state

    def _resolve_param_call_ref(self):
        if self.node is None:
            _LOGGER.warn("_resolve_param_call_ref: self.node is None")
            self._indirect_unresolved_error()
            return None

        _LOGGER.log(utils.LOG_SPAM, self.node.dbg())
        assert self.statedata is not None
        if len(self.statedata) <= 0:
            _LOGGER.log(utils.LOG_SPAM, "resolved all references")
            return None
        call_ref = self.statedata.pop(0)
        call_expr = call_ref['call_expr']
        arg = call_ref['arg']
        _LOGGER.log(utils.LOG_SPAM, "call_expr: %s" % call_expr.dbg())
        _LOGGER.log(utils.LOG_SPAM, "arg: %s" % arg.dbg())

        if (arg.astnode.kind != astparser.cl.CursorKind.DECL_REF_EXPR.value or
                arg.referenced is None):
            _LOGGER.log(utils.LOG_SPAM, "unexpected arg")
            self._indirect_unresolved_error()
            return None

        arg_ref = arg.referenced
        _LOGGER.log(utils.LOG_SPAM, "arg_ref: %s" % arg_ref.dbg())

        # We are trying to find the value of arg when call_expr is called
        next_state = None
        if (arg_ref.astnode.kind == astparser.cl.CursorKind.VAR_DECL.value or
                arg_ref.astnode.kind == astparser.cl.CursorKind.PARM_DECL.value):
            self.node = arg
            self.call_expr = call_expr
            # Re-start the state machine from _resolve_call_expr
            max_state_changes = self.statemachine.get_remaining_state_changes()
            self.statemachine.start(self._resolve_call_expr, max_state_changes)
            next_state = self._resolve_param_call_ref
        elif arg_ref.astnode.kind == astparser.cl.CursorKind.FUNCTION_DECL.value:
            self._add_resolved(arg_ref)
            next_state = self._resolve_param_call_ref
        else:
            self._indirect_unresolved_error()
            next_state = None
        return next_state

    def _add_resolved(self, node):
        self.resolved.append(node)

    # TODO: to astparser?
    def _find_call_expr_nth_argument(self, call_expr, n):
        _LOGGER.log(utils.LOG_SPAM, self.node.dbg())
        arg_n = 0
        for child in call_expr.children:
            if arg_n - 1 == n:
                return child.find_first_child_leaf()
            arg_n += 1

    def _indirect_unresolved_error(self):
        _LOGGER.warn("Failed finding indirect call %s" % (
            self.startnode.dbg()))
        self._add_resolved(IndirectResolver.unknown_node)

    def _max_call_refs_error(self):
        _LOGGER.warn("Max call refs reached in resolving %s" % (
            self.startnode.dbg()))
        self._add_resolved(IndirectResolver.unknown_node)


class NodeFields(NamedTuple):
    filename: str
    line: str
    function: str
    calltype: str


class FunctionCallFinder():
    unknown_node = astparser.TreeNode(astnode=AstNode(clang_node=None))

    def __init__(self):
        self.funcname_resolver = FunctionNameResolver()
        self.indirect_resolver = IndirectResolver()

    def find_function_calls(
            self, csvfile, compdb, append_arg=None, srcfile=None, projroot=None, exclude=None):
        self.csvwriter = utils.CsvWriter(csvfile)
        self._write_header()

        # Let AstParser parse the AST tree, calling
        # self.ast_tree_walk() for all the translation unit root nodes
        self.astparser = astparser.AstParser(compdb, append_arg, srcfile, projroot, exclude)
        self.ast_tree = self.astparser.get_ast_tree()
        self.ast_tree.walk_tu_heads(self.ast_tree_walk)
        self.csvwriter.close()

    def _write_header(self):
        members = [m for m in vars(NodeFields).keys() if not m.startswith("_")]
        caller_header = ["caller_%s" % s for s in members]
        callee_header = ["callee_%s" % s for s in members]
        header = caller_header + callee_header
        self.csvwriter.write_arr(header)

    def _to_csv_row(self, caller_nodefields, callee_nodefields):
        caller_values = list(caller_nodefields)
        callee_values = list(callee_nodefields)
        row = caller_values + callee_values
        self.csvwriter.write_arr(row)

    def _node_to_csv_fields(self, node, call_location=None):
        _LOGGER.log(utils.LOG_SPAM, node.dbg())
        if call_location:
            filename = call_location.astnode.filename
            line = call_location.astnode.line
        else:
            filename = node.astnode.filename
            line = node.astnode.line
        if node.astnode.kind == astparser.cl.CursorKind.FUNCTION_DECL.value:
            calltype = "direct"
        elif node.astnode.kind is None:
            calltype = "unknown"
        elif node.astnode.kind == astparser.cl.CursorKind.CALL_EXPR.value:
            calltype = "unknown"
            filename = ""
            line = ""
        else:
            calltype = "indirect"
        function = self.funcname_resolver.resolve(node)
        return NodeFields(filename, line, function, calltype)

    def ast_tree_walk(self, treenode):
        callee_fields = None

        # Direct function call
        if treenode.astnode.kind == astparser.cl.CursorKind.CALL_EXPR.value:
            caller = treenode.find_first_ancestor(
                [astparser.cl.CursorKind.FUNCTION_DECL.value])
            if not caller:
                _LOGGER.debug("No caller: %s" % treenode.dbg())
                caller = FunctionCallFinder.unknown_node
            caller_fields = self._node_to_csv_fields(caller, treenode)
            if treenode.referenced is None:
                treenode.referenced = treenode.find_first_ref()
            callee = treenode.referenced
            if not callee:
                callee = treenode
            callee_fields = self._node_to_csv_fields(callee)
            self._to_csv_row(caller_fields, callee_fields)

        # Callee is indirect
        if callee_fields and callee_fields.calltype == "indirect":
            _LOGGER.debug("Indirect callee: %s" % treenode.dbg())
            # If callee is indirect, we write another entry to the csv
            # database now resolving the indirect call. Each resolved
            # indirect call creates one new entry to the csv database.
            # For these entries, the original indirect callee is registered as
            # caller. The new caller location is set to the location of the
            # original caller.
            caller_fields = self._node_to_csv_fields(callee, treenode)
            # Resolve the indirect callees
            callees = self.indirect_resolver.resolve(treenode)
            for callee in callees:
                _LOGGER.debug("Resolved indirect: %s" % callee.dbg())
                callee_fields = self._node_to_csv_fields(callee)
                self._to_csv_row(caller_fields, callee_fields)

        # Recursively iterate all children
        children = treenode.children
        for child in children:
            self.ast_tree_walk(child)


################################################################################


def add_args(parser):
    desc = \
        "Dump function calls from clang AST tree based on compilation "\
        "database (compile_commands.json)."

    epil = "Example: ./%s --compdb ~/linux-stable/compile_commands.json" % \
        os.path.basename(__file__)
    parser.description = desc
    parser.epilog = epil

    help = "Exclude from processing if path to a file contains specified string"
    parser.add_argument('--exclude', help=help, default='tools,scripts')

    help = "Set the output file name, default is 'calls.csv'"
    parser.add_argument('--out', nargs='?', help=help, default='calls.csv')

    return parser


################################################################################

def find_function_calls(parser):
    args = parser.parse_args()
    utils.handle_common_args(parser, args)

    astparser.set_clang_bindings_and_lib(args.cindexpy, args.libclang)
    from astparser import cl

    finder = FunctionCallFinder()
    finder.find_function_calls(
        csvfile=args.out,
        compdb=args.compdb,
        append_arg=args.append_arg,
        srcfile=args.file,
        projroot=args.projroot,
        exclude=args.exclude
    )


if __name__ == "__main__":
    parser = utils.clang_common_args(_FILEDIR)
    add_args(parser)
    find_function_calls(parser)


################################################################################
