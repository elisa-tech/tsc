// SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved
//
// SPDX-License-Identifier: LicenseRef-Apache-2.0-with-LLVM

#include "VirtualCallTargets.h"

#include "llvm/Analysis/TypeMetadataUtils.h"
#include "llvm/IR/Dominators.h"
#include "llvm/IR/Intrinsics.h"
#include "llvm/InitializePasses.h"

#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"

#include "llvm/Analysis/AssumptionCache.h"
#include "llvm/Transforms/IPO/WholeProgramDevirt.h"

#include <string>
#include <unordered_map>
#include <unordered_set>

#include "Common.h"

using namespace llvm;
using namespace std;
using namespace virtcall;

////////////////////////////////////////////////////////////////////////////////
//
// Based on: llvm/lib/Transforms/IPO/WholeProgramDevirt.cpp
//
////////////////////////////////////////////////////////////////////////////////

#if __clang_major__ <= 10

namespace llvm {
void initializeVirtualCallTargetsPass(PassRegistry &);
void initializeDominatorTreeWrapperPassPass(PassRegistry &);
} // end namespace llvm

namespace virtcall {

////////////////////////////////////////////////////////////////////////////////

void VirtualCallTargetsResult::addVirtualCallCandidates(
    CallInst *call, FunctionSet &&candidates) {
  addCandidates(call, move(candidates));
}

void VirtualCallTargetsResult::addVirtualInvokeCandidates(
    InvokeInst *call, FunctionSet &&candidates) {
  addCandidates(call, move(candidates));
}

bool VirtualCallTargetsResult::hasVirtualCallCandidates(
    Instruction *instr) const {
  return m_virtualCallCandidates.find(instr) != m_virtualCallCandidates.end();
}

const FunctionSet &
VirtualCallTargetsResult::getVirtualCallCandidates(Instruction *instr) const {
  if (hasVirtualCallCandidates(instr)) {
    auto pos = m_virtualCallCandidates.find(instr);
    return pos->second;
  } else {
    return m_emptyFunctionSet;
  }
}

void VirtualCallTargetsResult::dump() {
  for (const auto &item : m_virtualCallCandidates) {
    dbgs() << "Virtual call: " << *item.first << " candidates:\n";
    for (const auto &candidate : item.second) {
      dbgs() << "    " << candidate->getName() << "\n";
    }
  }
}

void VirtualCallTargetsResult::addCandidates(Instruction *instr,
                                             FunctionSet &&candidates) {
  m_virtualCallCandidates[instr].insert(candidates.begin(), candidates.end());
}

////////////////////////////////////////////////////////////////////////////////

class VirtualCallTargets : public llvm::AnalysisInfoMixin<VirtualCallTargets> {
public:
  static llvm::AnalysisKey Key;
  using Result = VirtualCallTargetsResult;
  Result run(llvm::Module &M, llvm::ModuleAnalysisManager &);
  Result runOnModule(llvm::Module &M);

private:
  // A slot in a set of virtual tables. The TypeID identifies the set of virtual
  // tables, and the ByteOffset is the offset in bytes from the address point to
  // the virtual function pointer.
  struct VTableSlot {
    llvm::Metadata *TypeID;
    uint64_t ByteOffset;
  };

  // A virtual call site. VTable is the loaded virtual table pointer, and CS is
  // the indirect virtual call.
  struct VirtualCallSite {
    llvm::Value *VTable;
    llvm::CallSite CS;
  };

  class VTableSlotEqual {
  public:
    bool operator()(const VTableSlot &slot1, const VTableSlot &slot2) const {
      return slot1.TypeID == slot2.TypeID &&
             slot1.ByteOffset == slot2.ByteOffset;
    }
  };

  class VTableSlotHasher {
  public:
    unsigned long operator()(const VTableSlot &slot) const {
      return std::hash<llvm::Metadata *>{}(slot.TypeID) ^
             std::hash<uint64_t>{}(slot.ByteOffset);
    }
  };

  using VirtualCallSites = std::vector<VirtualCallSite>;
  using VTableSlotCallSitesMap =
      std::unordered_map<VTableSlot, VirtualCallSites, VTableSlotHasher,
                         VTableSlotEqual>;

  void scanTypeTestUsers(llvm::Function *TypeTestFunc);
  void buildTypeIdentifierMap(
      llvm::Module &M, std::vector<llvm::wholeprogramdevirt::VTableBits> &Bits,
      llvm::DenseMap<llvm::Metadata *,
                     std::set<llvm::wholeprogramdevirt::TypeMemberInfo>>
          &TypeIdMap);
  bool tryFindVirtualCallTargets(
      llvm::Module &M,
      std::vector<llvm::wholeprogramdevirt::VirtualCallTarget> &TargetsForSlot,
      const std::set<llvm::wholeprogramdevirt::TypeMemberInfo> &TypeMemberInfos,
      uint64_t ByteOffset);
  void
  updateResults(const std::vector<VirtualCallSite> &S,
                const std::vector<llvm::wholeprogramdevirt::VirtualCallTarget>
                    TargetsForSlot);

  llvm::function_ref<llvm::DominatorTree &(llvm::Function &)> LookupDomTree;
  VTableSlotCallSitesMap CallSlots;
  VirtualCallTargetsResult m_results;
};

////////////////////////////////////////////////////////////////////////////////

void VirtualCallTargets::scanTypeTestUsers(Function *TypeTestFunc) {
  // Find all virtual calls via a virtual table pointer %p under an assumption
  // of the form llvm.assume(llvm.type.test(%p, %md)). This indicates that %p
  // points to a member of the type identifier %md. Group calls by (type ID,
  // offset) pair (effectively the identity of the virtual function) and store
  // to CallSlots.
  DenseSet<CallSite> SeenCallSites;
  for (auto I = TypeTestFunc->use_begin(), E = TypeTestFunc->use_end();
       I != E;) {
    auto CI = dyn_cast<CallInst>(I->getUser());
    ++I;
    if (!CI)
      continue;

    // Search for virtual calls based on %p and add them to DevirtCalls.
    SmallVector<DevirtCallSite, 1> DevirtCalls;
    SmallVector<CallInst *, 1> Assumes;
    auto &DT = LookupDomTree(*CI->getFunction());
    findDevirtualizableCallsForTypeTest(DevirtCalls, Assumes, CI, DT);

    if (Assumes.empty()) {
      return;
    }
    unordered_set<Value *> SeenPtrs;
    Metadata *TypeId =
        cast<MetadataAsValue>(CI->getArgOperand(1))->getMetadata();
    Value *Ptr = CI->getArgOperand(0)->stripPointerCasts();
    if (!SeenPtrs.insert(Ptr).second) {
      continue;
    }
    for (const auto &Call : DevirtCalls) {
      CallSlots[{TypeId, Call.Offset}].push_back(
          {CI->getArgOperand(0), Call.CS});
    }
  }
}

void VirtualCallTargets::buildTypeIdentifierMap(
    Module &M, vector<wholeprogramdevirt::VTableBits> &Bits,
    DenseMap<Metadata *, set<wholeprogramdevirt::TypeMemberInfo>> &TypeIdMap) {
  DenseMap<GlobalVariable *, wholeprogramdevirt::VTableBits *> GVToBits;
  Bits.reserve(M.getGlobalList().size());
  SmallVector<MDNode *, 2> Types;
  for (GlobalVariable &GV : M.globals()) {
    Types.clear();
    GV.getMetadata(LLVMContext::MD_type, Types);
    if (GV.isDeclaration() || Types.empty())
      continue;

    wholeprogramdevirt::VTableBits *&BitsPtr = GVToBits[&GV];
    if (!BitsPtr) {
      Bits.emplace_back();
      Bits.back().GV = &GV;
      Bits.back().ObjectSize =
          M.getDataLayout().getTypeAllocSize(GV.getInitializer()->getType());
      BitsPtr = &Bits.back();
    }

    for (MDNode *Type : Types) {
      auto TypeID = Type->getOperand(1).get();

      uint64_t Offset =
          cast<ConstantInt>(
              cast<ConstantAsMetadata>(Type->getOperand(0))->getValue())
              ->getZExtValue();

      TypeIdMap[TypeID].insert({BitsPtr, Offset});
    }
  }
}

bool VirtualCallTargets::tryFindVirtualCallTargets(
    Module &M, vector<wholeprogramdevirt::VirtualCallTarget> &TargetsForSlot,
    const set<wholeprogramdevirt::TypeMemberInfo> &TypeMemberInfos,
    uint64_t ByteOffset) {
  for (const wholeprogramdevirt::TypeMemberInfo &TM : TypeMemberInfos) {
    if (!TM.Bits->GV->isConstant())
      return false;

    Constant *Ptr = getPointerAtOffset(TM.Bits->GV->getInitializer(),
                                       TM.Offset + ByteOffset, M);
    if (!Ptr)
      return false;

    auto Fn = dyn_cast<Function>(Ptr->stripPointerCasts());
    if (!Fn)
      return false;

    // We can disregard __cxa_pure_virtual as a possible call target, as
    // calls to pure virtuals are UB.
    if (Fn->getName() == "__cxa_pure_virtual")
      continue;

    LOG_FMT("%s ==> %s\n", Fn->getName().str().c_str(),
            TM.Bits->GV->getName().str().c_str());

    TargetsForSlot.push_back({Fn, &TM});
  }

  // Give up if we couldn't find any targets.
  return !TargetsForSlot.empty();
}

void VirtualCallTargets::updateResults(
    const vector<VirtualCallSite> &S,
    const vector<wholeprogramdevirt::VirtualCallTarget> TargetsForSlot) {
  for (const auto &cs : S) {
    FunctionSet candidates;
    for (const auto &slot : TargetsForSlot) {
      candidates.insert(slot.Fn);
    }
    if (cs.CS.isCall()) {
      m_results.addVirtualCallCandidates(
          dyn_cast<CallInst>(cs.CS.getInstruction()), move(candidates));
    } else if (cs.CS.isInvoke()) {
      m_results.addVirtualInvokeCandidates(
          dyn_cast<InvokeInst>(cs.CS.getInstruction()), move(candidates));
    }
  }
}

VirtualCallTargetsResult VirtualCallTargets::runOnModule(Module &M) {
  m_results = VirtualCallTargetsResult();
  Function *TypeTestFunc =
      M.getFunction(Intrinsic::getName(Intrinsic::type_test));
  Function *AssumeFunc = M.getFunction(Intrinsic::getName(Intrinsic::assume));

  if ((!TypeTestFunc || TypeTestFunc->use_empty() || !AssumeFunc ||
       AssumeFunc->use_empty())) {
    WARN_FMT("Missing required intrinsic functions%s", "\n");
    return m_results;
  }

  if (TypeTestFunc && AssumeFunc) {
    LOG_FMT("Type test Function: %s\n", TypeTestFunc->getName().str().c_str());
    scanTypeTestUsers(TypeTestFunc);
  }

  // Rebuild type metadata into a map for easy lookup.
  vector<wholeprogramdevirt::VTableBits> Bits;
  DenseMap<Metadata *, set<wholeprogramdevirt::TypeMemberInfo>> TypeIdMap;
  buildTypeIdentifierMap(M, Bits, TypeIdMap);
  if (TypeIdMap.empty()) {
    return m_results;
  }
  for (auto &S : CallSlots) {
    vector<wholeprogramdevirt::VirtualCallTarget> TargetsForSlot;
    if (!tryFindVirtualCallTargets(M, TargetsForSlot, TypeIdMap[S.first.TypeID],
                                   S.first.ByteOffset)) {
      continue;
    }
    updateResults(S.second, TargetsForSlot);
  }
  return m_results;
}

VirtualCallTargetsResult VirtualCallTargets::run(Module &M,
                                                 ModuleAnalysisManager &AM) {
  auto &FAM = AM.getResult<FunctionAnalysisManagerModuleProxy>(M).getManager();
  this->LookupDomTree = [&FAM](Function &F) -> DominatorTree & {
    return FAM.getResult<DominatorTreeAnalysis>(F);
  };
  return runOnModule(M);
}

////////////////////////////////////////////////////////////////////////////////

struct VirtualCallWrapper : public AnalysisInfoMixin<VirtualCallWrapper> {
  VirtualCallTargetsResult *result;

  VirtualCallWrapper(VirtualCallTargetsResult *memloc) : result(memloc) {}

  llvm::PreservedAnalyses run(Module &M, ModuleAnalysisManager &MAM) {
    if (result) {
      (*result) = MAM.getResult<virtcall::VirtualCallTargets>(M);
    }
    return llvm::PreservedAnalyses::all();
  }
};

void VirtualCallResolver::ResolveVirtualCalls(
    Module &M, VirtualCallTargetsResult &result) {
  //
  // This function is based on: llvm/tools/opt/NewPMDriver.cpp
  //
  auto LAM = LoopAnalysisManager();
  auto FAM = FunctionAnalysisManager();
  auto CGAM = CGSCCAnalysisManager();
  auto MAM = ModuleAnalysisManager();
  MAM.registerPass([&] { return virtcall::VirtualCallTargets(); });

  // Create a module pass manager and add VirtualCallWrapper to it.
  ModulePassManager MPM;
  VirtualCallWrapper VirtualWrapper(&result);
  MPM.addPass(VirtualWrapper);

  // Manually set up pass pipeline
  PassBuilder PB;
  PB.registerModuleAnalyses(MAM);
  PB.registerCGSCCAnalyses(CGAM);
  PB.registerFunctionAnalyses(FAM);
  PB.registerLoopAnalyses(LAM);
  PB.crossRegisterProxies(LAM, FAM, CGAM, MAM);

  // Finally, run the passes registered with MPM
  LOG("Calling MPM.run()");
  MPM.run(M, MAM);
}

////////////////////////////////////////////////////////////////////////////////

} // namespace virtcall

AnalysisKey VirtualCallTargets::Key;

////////////////////////////////////////////////////////////////////////////////

#endif //  __clang_major__ <= 10
