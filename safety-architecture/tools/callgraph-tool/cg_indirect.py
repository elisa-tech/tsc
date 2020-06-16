# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import numpy as np
import re


class Resolver:

    def __init__(self, labels):
        self.labels = labels
        self.globals = []
        self.locals = []
        self.structs = []

    def resolve_one(self, label):
        if label in self.labels:
            self.labels[label].resolve(self)
            return self.labels[label]
        return None

    def resolve_all(self):
        for label in self.labels:
            self.labels[label].resolve(self)

    def get_resolved(self):
        resolved = {}
        for gl in self.globals:
            if gl.type is not None:
                resolved[gl.name] = [gl]
        for loc in self.locals:
            if loc.type is not None:
                if loc.name in resolved:
                    resolved[loc.name].append(loc)
                else:
                    resolved[loc.name] = [loc]
        return resolved

    def find_ops_structures(self, indirect_func_names):
        # contains only subset of those that match structs_and_member_indices
        structs_and_member_names = {}
        structs_and_member_indices = {}
        if indirect_func_names is None:
            return structs_and_member_indices, structs_and_member_names

        for operation in indirect_func_names:
            struct_name, op_name = operation.split('.')
            for struct in self.structs:
                if struct.name == struct_name:
                    if struct_name not in structs_and_member_names:
                        structs_and_member_names[struct_name] = []
                        structs_and_member_indices[struct_name] = []
                    for idx, member in enumerate(struct.get_members()):
                        if member.name == op_name:
                            structs_and_member_names[struct_name].append(op_name)
                            structs_and_member_indices[struct_name].append(idx)

        return structs_and_member_indices, structs_and_member_names

    def activate(self, rtype, label):
        if label not in self.labels:
            return None

        lv = self.labels[label]
        return lv.resolve(self)


def is_subroutine_ptr(elem):
    return isinstance(elem, Subroutine)


class Member:
    def __init__(self, name, base_type, flags=None):
        self.name = name
        self.idx = int(base_type)
        self.base_type = base_type
        self.resolved = False
        self.flags = flags

    def resolve(self, resolver):
        if not self.resolved:
            self.resolved = True
            self.base_type = resolver.activate(Member.__name__, self.base_type)
        return self

    def is_subroutine_ptr(self):
        return is_subroutine_ptr(self.base_type)

    def is_bitfield(self):
        return self.flags == 'DIFlagBitField'


class OpStruct:
    def __init__(self, name, elements):
        self.name = name
        self.elements = elements
        self.resolved = False

    def resolve(self, r):
        if not self.resolved:
            self.resolved = True
            r.structs.append(self)
            self.elements = r.activate(OpStruct.__name__, self.elements)
        return self

    def _has_own_subroutine_ptrs(self):
        for elem in self.elements:
            if elem is None:
                return False
        return any(elem.is_subroutine_ptr() for elem in self.elements if elem is not None)

    def _has_child_subroutine_ptrs(self):
        return any(
            elem.has_subroutine_ptrs() for elem in self.elements if isinstance(elem, OpStruct)
        )

    def has_subroutine_ptrs(self):
        child_subroutine_ptr = self._has_child_subroutine_ptrs()
        own_subroutine_ptr = self._has_own_subroutine_ptrs()
        return own_subroutine_ptr or child_subroutine_ptr

    def get_subroutine_ptrs(self):
        subroutine_ptrs = []
        for elem in self.elements:
            if isinstance(elem, Subroutine):
                subroutine_ptrs.append(elem)
        return subroutine_ptrs

    def get_members(self):
        return self.elements

    def get_mapping(self):
        bfs = [elem.is_bitfield() for elem in self.elements]
        prev_bfs = False
        mapping = [-1]
        for bf in bfs:
            if prev_bfs and bfs:
                mapping.append(mapping[-1])
            else:
                mapping.append(mapping[-1] + 1)
            prev_bfs = bf
        return mapping[1:]

    def count_members(self):
        if self.elements is None:
            return 0
        bfs = [elem.is_bitfield() for elem in self.elements]
        bfs = np.array(bfs, dtype=np.int8)
        # count distinct bitfield groups
        bfs_count = (bfs[1:] > bfs[:-1]).sum() + bfs[0]
        return len(self.elements) - bfs.sum() + bfs_count


class UnionType:
    def __init__(self, name, elements):
        self.name = name
        self.elements = elements
        self.resolved = False

    def resolve(self, resolver):
        if not self.resolved:
            self.resolved = True
            self.elements = resolver.activate(UnionType.__name__, self.elements)
        return self

    def get_members(self):
        return self.elements


class DerivedType:
    def __init__(self, baseType):
        self.baseType = baseType
        self.resolved = False

    def resolve(self, resolver):
        if not self.resolved:
            self.resolved = True
            self.baseType = resolver.activate(DerivedType.__name__, self.baseType)
        return self.baseType


class Elements:
    def __init__(self, elements):
        elements = re.findall(r'!\d+', elements)
        self.elements = [elem.strip('!') for elem in elements]
        self.resolved = False

    def resolve(self, resolver):
        if not self.resolved:
            self.resolved = True
            elems = []
            for element in self.elements:
                res = resolver.activate(Elements.__name__, element)
                elems.append(res)
            self.elements = elems
        return self.elements


class Subroutine:
    def __init__(self, types):
        self.types = types
        self.resolved = False

    def resolve(self, resolver):
        if not self.resolved:
            self.resolved = True
            self.types = []
        return self


class LocalVariable:
    def __init__(self, name, gtype):
        self.name = name
        self.type = gtype
        self.resolved = False

    def resolve(self, r):
        if not self.resolved:
            self.resolved = True
            self.type = r.activate(LocalVariable.__name__, self.type)
            # keep tabs on the local struct variables with member pointers
            if self.is_composite_type():
                if self.type.has_subroutine_ptrs():
                    r.locals.append(self)

        return self

    def is_composite_type(self):
        return isinstance(self.type, OpStruct)  # or isinstance(self.type, UnionType)


class GlobalVariable:
    def __init__(self, name, gtype):
        self.name = name
        self.type = gtype
        self.resolved = False

    def resolve(self, r):
        if not self.resolved:
            self.resolved = True
            r.globals.append(self)
            self.type = r.activate(GlobalVariable.__name__, self.type)
        return self

    def is_struct(self):
        return isinstance(self.type, OpStruct)


def detect_ops_structures(llvm_file):
    re_global_var = re.compile(
        r'!(?P<label>\d+).*!DIGlobalVariable\(name: "(?P<name>\w+)".*type: !(?P<type>\d+)'
    )
    re_local_var = re.compile(
        r'!(?P<label>\d+).*!DILocalVariable\(name: "(?P<name>\w+)".*type: !(?P<type>\d+)'
    )
    re_derived_type = re.compile(r'!(?P<label>\d+).*!DIDerivedType.*baseType: !(?P<baseType>\d+)')
    re_structure_type = re.compile(
        r'!(?P<label>\d+).*DW_TAG_structure_type, (?:name: "(?P<name>\w+)")?.*, elements: !(?P<elements>\d+)')
    re_elements = re.compile(r'!(?P<label>\d+) = !{(?P<elements>[!\d\s,]*)}')
    re_member = re.compile(
        r'!(?P<label>\d+) = .*DW_TAG_member, (?:name: "(?P<name>\w+)")?.*, '
        r'baseType: !(?P<baseType>\d+)(?:.*, flags: (?P<flags>\w+))?'
    )
    re_union_type = re.compile(
        r'!(?P<label>\d+).*DW_TAG_union_type, .*elements: !(?P<elements>\d+)')
    re_subroutine = re.compile(r'!(?P<label>\d+) = !DISubroutineType\(types: !(?P<types>\d+)\)')

    labels = {}
    llvm_file.seek(0)
    for line in llvm_file:
        if line.startswith('!llvm.dbg.cu = '):
            break
    for line in llvm_file:
        if line.startswith('\n'):
            break
    for line in llvm_file:
        m = re_structure_type.search(line)
        if m:
            label = m.group('label')
            labels[label] = OpStruct(m.group('name'), m.group('elements'))
            continue

        m = re_elements.search(line)
        if m:
            label = m.group('label')
            labels[label] = Elements(m.group('elements'))
            continue

        m = re_member.search(line)
        if m:
            label = m.group('label')
            labels[label] = Member(m.group('name'), m.group('baseType'), m.group('flags'))
            continue

        m = re_subroutine.search(line)
        if m:
            label = m.group('label')
            labels[label] = Subroutine(m.group('types'))
            continue

        m = re_derived_type.search(line)
        if m:
            label = m.group('label')
            labels[label] = DerivedType(m.group('baseType'))
            continue
        m = re_local_var.search(line)
        if m:
            label = m.group('label')
            labels[label] = LocalVariable(m.group('name'), m.group('type'))
            continue

        m = re_global_var.search(line)
        if m:
            label = m.group('label')
            labels[label] = GlobalVariable(m.group('name'), m.group('type'))
            continue
        m = re_union_type.search(line)
        if m:
            label = m.group('label')
            labels[label] = UnionType('', m.group('elements'))
            continue

    llvm_file.seek(0)
    resolver = Resolver(labels)
    resolver.resolve_all()
    res = resolver.get_resolved()
    return res, resolver


def decode_struct_mems(entry):
    members = tokenize_members(entry)
    names = []
    for member in members:
        # padding insertions are ignored ([ x ] undef)
        if member.endswith('] undef'):
            continue
        if member.startswith('%struct'):
            mname = member.split(' ')[0]
            if not mname.endswith('*'):
                # for now, ignore members of type struct
                # pointers are OK
                names.append('')
                continue
        et_idx = member.find(' @')
        if et_idx >= 0:
            end_idx = member.find(',', et_idx + 2)
            if end_idx == -1:
                name = member[et_idx + 2:]
            else:
                name = member[et_idx + 2:end_idx]
            names.append(name)
            continue
        names.append('')
    return names


def tokenize_members(entry):
    tokend = {')': '(', ']': '[', '}': '{'}
    tokens = {')', '(', ']', '[', '}', '{'}

    mem_list = []
    stack = []
    begin, end = 0, 0
    conststr = False
    for (i, c) in enumerate(entry):
        end = i
        if c == '"' and i > 0:
            conststr = True if entry[i - 1] == 'c' else False

        if conststr:
            # ignore the chars inside of constant string
            continue

        if c == ',':
            if not stack:
                mem_list.append(entry[begin:end])
                begin = i + 2  # accomodate for comma and space
            continue
        # c is token
        if c in tokens:
            if c in tokend:
                if stack:
                    stack.pop()
                else:
                    # error
                    return []
            else:
                stack.append(c)

    if begin < end:
        mem_list.append(entry[begin:])

    return mem_list


def get_indirect(llvm_file, resolved):
    llvm_file.seek(0)
    re_structure_def = re.compile(
        r'@(?P<name>\w+) = [^{.]*?%struct.(?P<struct>\w+) { (?P<members>.*) },'
    )
    indirect_nodes = {}
    for idx, line in enumerate(llvm_file):
        m = re_structure_def.search(line)
        if m:
            name = m.group('name')
            if name in resolved:
                struct = m.group('struct')
                r = None
                for rn in resolved[name]:
                    if rn.type is None:
                        continue
                    if rn.type.name == struct:
                        r = rn
                        break
                if r is None:
                    continue
                members = m.group('members')
                if not r.type.has_subroutine_ptrs():
                    continue
                members = decode_struct_mems(members)
                member_defs = r.type.get_members()

                mapping = np.arange(0, len(member_defs))
                if len(members) != len(member_defs):
                    # legitimate if struct uses bitfield
                    if len(members) != r.type.count_members():
                        _ = decode_struct_mems(members)
                        print("STRUCT: ", struct, " : ", llvm_file)
                        print(len(members), " vs ", len(member_defs))
                        print("Line: ", idx, " : ", line)
                        continue
                    mapping = r.type.get_mapping()
                for i, memd in enumerate(member_defs):
                    if memd.is_subroutine_ptr():
                        if members[mapping[i]]:
                            key = struct + '.' + memd.name
                            value = members[mapping[i]]
                            if key in indirect_nodes:
                                if value not in indirect_nodes[key]:
                                    indirect_nodes[key].append(value)
                            else:
                                indirect_nodes[key] = [value]

    llvm_file.seek(0)
    return indirect_nodes
