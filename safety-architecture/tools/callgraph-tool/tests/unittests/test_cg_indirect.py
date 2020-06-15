# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys

callgraphtool_path = os.path.dirname(os.path.abspath(__file__)) + '/../..'
sys.path.append(callgraphtool_path)

from cg_indirect import *  # noqa E402

irq_domain_mutex_mems = "\
%struct.atomic64_t zeroinitializer, \
%struct.spinlock zeroinitializer, \
%struct.optimistic_spin_queue zeroinitializer, \
%struct.list_head { %struct.list_head* bitcast (i8* getelementptr (i8, i8* bitcast \
(%struct.mutex* @irq_domain_mutex to i8*), i64 16) to %struct.list_head*), \
%struct.list_head* bitcast (i8* getelementptr (i8, i8* bitcast (%struct.mutex* \
@irq_domain_mutex to i8*), i64 16) to %struct.list_head*) }"
irq_domain_mutex = "@irq_domain_mutex = \
    internal global %struct.mutex { " + irq_domain_mutex_mems + " }, align 8, !dbg !5052"
x86_vector_domain_ops_mems = "\
i32 (%struct.irq_domain*, %struct.device_node*, i32)* null, \
i32 (%struct.irq_domain*, %struct.irq_fwspec*, i32)* null, \
i32 (%struct.irq_domain*, i32, i64)* null, \
void (%struct.irq_domain*, i32)* null, \
i32 (%struct.irq_domain*, %struct.device_node*, i32*, i32, i64*, i32*)* null, \
i32 (%struct.irq_domain*, i32, i32, i8*)* @x86_vector_alloc_irqs, \
void (%struct.irq_domain*, i32, i32)* @x86_vector_free_irqs, \
i32 (%struct.irq_domain*, %struct.irq_data*, i1)* @x86_vector_activate, \
void (%struct.irq_domain*, %struct.irq_data*)* @x86_vector_deactivate, \
i32 (%struct.irq_domain*, %struct.irq_fwspec*, i64*, i32*)* null"

x86_vector_domain_ops = "@x86_vector_domain_ops = \
    internal constant %struct.irq_domain_ops { " + x86_vector_domain_ops_mems + "}, align 8, !dbg !4575"


def test_tokenize_members1():
    tokens = tokenize_members(irq_domain_mutex_mems)
    assert len(tokens) == 4
    assert tokens[0] == '%struct.atomic64_t zeroinitializer'
    assert tokens[1] == '%struct.spinlock zeroinitializer'
    assert tokens[2] == '%struct.optimistic_spin_queue zeroinitializer'
    assert '%struct.list_head' in tokens[3]


def test_tokenize_members2():
    tokens = tokenize_members(x86_vector_domain_ops_mems)
    assert len(tokens) == 10
    assert tokens[0] == 'i32 (%struct.irq_domain*, %struct.device_node*, i32)* null'
    assert tokens[4] == 'i32 (%struct.irq_domain*, %struct.device_node*, i32*, i32, i64*, i32*)* null'
    assert tokens[9] == 'i32 (%struct.irq_domain*, %struct.irq_fwspec*, i64*, i32*)* null'


def test_decode_struct_mems1():
    mems = decode_struct_mems(irq_domain_mutex_mems)
    assert len(mems) == 4
    assert all([m is '' for m in mems])


def test_decode_struct_mems2():
    mems = decode_struct_mems(x86_vector_domain_ops_mems)
    assert len(mems) == 10
    assert sum([int(m is '') for m in mems]) == 6
    assert mems[5] == 'x86_vector_alloc_irqs'
    assert mems[6] == 'x86_vector_free_irqs'
    assert mems[7] == 'x86_vector_activate'
    assert mems[8] == 'x86_vector_deactivate'
