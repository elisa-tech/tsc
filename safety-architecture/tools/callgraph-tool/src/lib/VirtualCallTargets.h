// SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved
//
// SPDX-License-Identifier: LicenseRef-Apache-2.0-with-LLVM

#ifndef VIRTUAL_CALL_TARGETS_H
#define VIRTUAL_CALL_TARGETS_H

#include "llvm/IR/Dominators.h"
#include "llvm/IR/Instructions.h"
#include "llvm/Transforms/IPO/WholeProgramDevirt.h"

#include <unordered_map>
#include <unordered_set>

namespace virtcall {

using FunctionSet = llvm::SmallPtrSet<llvm::Function *, 8>;

////////////////////////////////////////////////////////////////////////////////

class VirtualCallTargetsResult {
public:
  void addVirtualCallCandidates(llvm::CallInst *call, FunctionSet &&candidates);
  void addVirtualInvokeCandidates(llvm::InvokeInst *call,
                                  FunctionSet &&candidates);
  bool hasVirtualCallCandidates(llvm::Instruction *instr) const;
  const FunctionSet &getVirtualCallCandidates(llvm::Instruction *instr) const;
  void dump();

private:
  void addCandidates(llvm::Instruction *instr, FunctionSet &&candidates);
  std::unordered_map<llvm::Instruction *, FunctionSet> m_virtualCallCandidates;
  FunctionSet m_emptyFunctionSet;
}; // class VirtualCallTargetsResult

////////////////////////////////////////////////////////////////////////////////

class VirtualCallResolver {

public:
  static void ResolveVirtualCalls(llvm::Module &M,
                                  VirtualCallTargetsResult &result);
};

////////////////////////////////////////////////////////////////////////////////

} // end namespace virtcall

#endif