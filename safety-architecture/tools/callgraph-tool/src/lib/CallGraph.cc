// SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved
//
// SPDX-License-Identifier: LicenseRef-LLVM

//===-- CallGraph.cc - Build global call-graph------------------===//
//
// This pass builds a global call-graph. The targets of an indirect
// call are identified based on two-layer type-analysis.
//
// First layer: matching function type
// Second layer: matching struct type
//
//===-----------------------------------------------------------===//

#include "llvm/Demangle/Demangle.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/TypeFinder.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

#include "CallGraph.h"

using namespace llvm;
using namespace std;

DenseMap<size_t, FuncSet> CallGraphPass::typeFuncsMap;
unordered_map<size_t, set<size_t>> CallGraphPass::typeConfineMap;
unordered_map<size_t, set<size_t>> CallGraphPass::typeTransitMap;
// TODO: typeTransitTypeMap should be build in a separate pass
unordered_map<size_t, set<Type *>> CallGraphPass::typeTransitTypeMap;
unordered_map<std::string, set<Type *>> CallGraphPass::structTypeMap;
set<size_t> CallGraphPass::typeEscapeSet;

#include <llvm/IR/DebugInfo.h>
#include <llvm/IR/DebugInfoMetadata.h>
#include <llvm/IR/DebugLoc.h>

struct CallGraphDebugInfo {
  string caller_line = "";
  string callee_inlined_from_file = "";
  string callee_inlined_from_line = "";
};

CallGraphDebugInfo readDebugInfo(CallInst *caller_cinst,
                                 string caller_filename) {

  struct CallGraphDebugInfo info;
  Instruction *caller_inst = dyn_cast<Instruction>(caller_cinst);
  if (!caller_inst) {
    return info;
  }
  const llvm::DebugLoc &debugInfo = caller_inst->getDebugLoc();
  if (!debugInfo) {
    return info;
  }

  info.caller_line = to_string(debugInfo->getLine());

  // If it's inlined, find the file and line the inlining originated from
  for (DILocation *inlined_at = debugInfo->getInlinedAt(); inlined_at;
       inlined_at = inlined_at->getInlinedAt()) {
    DILocalScope *scope = inlined_at->getScope();
    string filename = scope->getFilename();
    if (filename == caller_filename) {
      info.caller_line = to_string(inlined_at->getLine());
      info.callee_inlined_from_file = debugInfo->getFilename();
      info.callee_inlined_from_line = to_string(debugInfo->getLine());
      break;
    }
  }
  return info;
}

void CallGraphPass::printCallGraphHeader() {
  Ctx->csvout << ""
              << "\"caller_filename\","
              << "\"caller_function\","
              << "\"caller_def_line\","
              << "\"caller_line\","
              << "\"callee_filename\","
              << "\"callee_function\","
              << "\"callee_line\","
              << "\"callee_calltype\","
              << "\"callee_inlined_from_file\","
              << "\"callee_inlined_from_line\","
              << "\"indirect_found_with\""
              << "\n";
}

void CallGraphPass::printCallGraphRow(CallInst *caller_cinst,
                                      Function *callee_func, string callee_type,
                                      string indirect_found_with) {

  string callee_line = "";
  string callee_name = "";
  string callee_filename = "";

  if (callee_func) {
    callee_name = callee_func->getName();
    DISubprogram *callee_sp = callee_func->getSubprogram();
    if (callee_sp) {
      callee_line = to_string(callee_sp->getLine());
      callee_filename = callee_sp->getFilename().str();
      if (Ctx->demangle == demangle_debug_only)
        callee_name = callee_sp->getName().str();
    }
    if (Ctx->demangle == demangle_all)
      callee_name = demangle(callee_name);
  }

  string caller_line = "";
  string caller_name = "";
  string caller_filename = "";
  string caller_line_funcdef = "";

  Function *caller_func = caller_cinst->getCaller();
  if (caller_func) {
    caller_name = caller_func->getName();
    DISubprogram *caller_sp = caller_func->getSubprogram();
    if (caller_sp) {
      caller_line_funcdef = to_string(caller_sp->getLine());
      caller_filename = caller_sp->getFilename().str();
      if (Ctx->demangle == demangle_debug_only)
        caller_name = caller_sp->getName().str();
    } else if (Module *m = caller_func->getParent()) {
      caller_filename = m->getSourceFileName();
    }
    if (Ctx->demangle == demangle_all)
      caller_name = demangle(caller_name);
  }

  if (caller_name.empty() || callee_name.empty()) {
    return;
  }
  CallGraphDebugInfo info = readDebugInfo(caller_cinst, caller_filename);

  Ctx->csvout << ""
              << "\"" << caller_filename << "\","
              << "\"" << caller_name << "\","
              << "\"" << caller_line_funcdef << "\","
              << "\"" << info.caller_line << "\","
              << "\"" << callee_filename << "\","
              << "\"" << callee_name << "\","
              << "\"" << callee_line << "\","
              << "\"" << callee_type << "\","
              << "\"" << info.callee_inlined_from_file << "\","
              << "\"" << info.callee_inlined_from_line << "\","
              << "\"" << indirect_found_with << "\""
              << "\n";
}
CallGraphPass::CallGraphPass(GlobalContext *Ctx_)
    : IterativeModulePass(Ctx_, "CallGraph") {
  printCallGraphHeader();
}

// Find targets of indirect calls based on type analysis: as long as
// the number and type of parameters of a function matches with the
// ones of the callsite, we say the function is a possible target of
// this call.
void CallGraphPass::findCalleesWithType(CallInst *CI, FuncSet &S) {

  LOG_OBJ("CallInst: ", CI);
  if (CI->isInlineAsm())
    return;

  //
  // TODO: performance improvement: cache results for types
  //
  CallSite CS(CI);
  for (Function *F : Ctx->AddressTakenFuncs) {

    // VarArg
    if (F->getFunctionType()->isVarArg()) {
      // Compare only known args in VarArg.
    }
    // otherwise, the numbers of args should be equal.
    else if (F->arg_size() != CS.arg_size()) {
      continue;
    }

    if (F->isIntrinsic()) {
      continue;
    }

    // Skip if the function return types don't match
    Type *CSTy = CS->getType();
    Type *FRetTy = F->getReturnType();
    if (CSTy && FRetTy) {
      // LOG_OBJ("CallSite Type: ", CSTy);
      // LOG_OBJ("Function Return Type: ", FRetTy);
      // From Type.h:
      // The instances of the Type class are immutable: once they are created,
      // they are never changed.  Also note that only one instance of a
      // particular type is ever created.  Thus seeing if two types are equal is
      // a matter of doing a trivial pointer comparison.
      if (CSTy != FRetTy)
        continue;
    }

    // Type matching on args.
    bool Matched = true;
    CallSite::arg_iterator AI = CS.arg_begin();
    for (Function::arg_iterator FI = F->arg_begin(), FE = F->arg_end();
         FI != FE; ++FI, ++AI) {
      // Check type mis-matches.
      // Get defined type on callee side.
      Type *DefinedTy = FI->getType();
      // Get actual type on caller side.
      Type *ActualTy = (*AI)->getType();

      if (DefinedTy == ActualTy)
        continue;

      // FIXME: this is a tricky solution for disjoint
      // types in different modules. A more reliable
      // solution is required to evaluate the equality
      // of two types from two different modules.
      // Since each module has its own type table, same
      // types are duplicated in different modules. This
      // makes the equality evaluation of two types from
      // two modules very hard, which is actually done
      // at link time by the linker.
      while (DefinedTy->isPointerTy() && ActualTy->isPointerTy()) {
        DefinedTy = DefinedTy->getPointerElementType();
        ActualTy = ActualTy->getPointerElementType();
      }
      if (DefinedTy->isStructTy() && ActualTy->isStructTy() &&
          (DefinedTy->getStructName().equals(ActualTy->getStructName())))
        continue;
      if (DefinedTy->isIntegerTy() && ActualTy->isIntegerTy() &&
          DefinedTy->getIntegerBitWidth() == ActualTy->getIntegerBitWidth())
        continue;
      // TODO: more types to be supported.

      // Make the type analysis conservative: assume universal
      // pointers, i.e., "void *" and "char *", are equivalent to
      // any pointer type and integer type.
      if ((DefinedTy == Int8PtrTy &&
           (ActualTy->isPointerTy() || ActualTy == IntPtrTy)) ||
          (ActualTy == Int8PtrTy &&
           (DefinedTy->isPointerTy() || DefinedTy == IntPtrTy)))
        continue;
      else {
        Matched = false;
        break;
      }
    }

    if (Matched)
      S.insert(F);
  }
}

bool CallGraphPass::isCompositeType(Type *Ty) {
  if (Ty->isStructTy() || Ty->isArrayTy() || Ty->isVectorTy())
    return true;
  else
    return false;
}

bool CallGraphPass::typeConfineInInitializer(User *Ini) {

  list<User *> LU;
  LU.push_back(Ini);
  set<size_t> typeHashes;

  while (!LU.empty()) {
    User *U = LU.front();
    LU.pop_front();

    LOG_OBJ("Initializer: ", U);

    for (auto oi = U->op_begin(), oe = U->op_end(); oi != oe; ++oi) {
      // Strip possible bitcasts
      Value *O = (*oi)->stripPointerCasts();
      Type *OTy = O->getType();

      // Case 1: function address is assigned to a type
      if (Function *F = dyn_cast<Function>(O)) {
        Type *ITy = U->getType();
        // TODO: use offset?
        unsigned ONo = oi->getOperandNo();
        LOG_FMT("Adding to typeFuncsMap: Function [%s] assigned to field idx "
                "[%u]\n",
                F->getName().str().c_str(), ONo);
        typeFuncsMap[typeIdxHash(ITy, ONo)].insert(F);
        for (auto const &h : typeHashes) {
          LOG_FMT("Adding to typeFuncsMap from typeHashes: Function [%s] "
                  "assigned to field with hash [%lu]\n",
                  F->getName().str().c_str(), h);
          typeFuncsMap[h].insert(F);
        }
      }
      // Case 2: a composite-type object (value) is assigned to a
      // field of another composite-type object
      else if (isCompositeType(OTy)) {
        // confine composite types
        Type *ITy = U->getType();
        unsigned ONo = oi->getOperandNo();
        size_t h = typeIdxHash(ITy, ONo);
        LOG_FMT("Adding to typeHashes: %lu\n", h);
        typeHashes.insert(h);

        // recognize nested composite types
        User *OU = dyn_cast<User>(O);
        LU.push_back(OU);
      }
      // Case 3: a reference (i.e., pointer) of a composite-type
      // object is assigned to a field of another composite-type
      // object
      else if (PointerType *POTy = dyn_cast<PointerType>(OTy)) {
        if (isa<ConstantPointerNull>(O))
          continue;
        // if the pointer points a composite type, skip it as
        // there should be another initializer for it, which
        // will be captured
      }
    }
  }

  return true;
}

bool CallGraphPass::typeConfineInStore(Value *Dst, Value *Src) {

  LOG_OBJ("Destination: ", Dst);
  // Strip possible bitcasts
  Src = Src->stripPointerCasts();
  LOG_FMT("Source: %s\n", Src->getName().str().c_str());
  IndexVector NextLayer;
  int FieldIdx = -1;

  // Case 1: The value operand is a function
  if (Function *F = dyn_cast<Function>(Src)) {
    // Type *STyPrev = NULL;
    while (Type *STy = nextLayerBaseType(Dst, FieldIdx, &NextLayer)) {
      LOG_OBJ("Next layer type: ", STy);
      LOG_FMT("Adding to typeFuncsMap: Function [%s] assigned to field idx "
              "[%u]\n",
              F->getName().str().c_str(), FieldIdx);
      typeFuncsMap[typeIdxHash(STy, FieldIdx)].insert(F);
      if (NextLayer.empty()) {
        break;
      }
    }
    return true;
  }

  // Case 2: reference (i.e., pointer)-based store
  if (isa<ConstantPointerNull>(Src))
    return false;
  // FIXME: Get the correct types
  PointerType *PVTy = dyn_cast<PointerType>(Src->getType());
  if (!PVTy)
    return false;

  Type *EVTy = PVTy->getElementType();

  // Store something to a field of a composite-type object
  if (Type *STy = nextLayerBaseType(Dst, FieldIdx)) {
    LOG_OBJ("Next layer type: ", STy);
    // The value operand is a pointer to a composite-type object
    if (isCompositeType(EVTy)) {
      LOG_FMT("Adding to typeConfineMap: Type assigned to field idx [%i]\n",
              FieldIdx);
      LOG_OBJ("assigned to type: ", STy);
      LOG_OBJ("assigned type: ", EVTy);
      typeConfineMap[typeHash(STy)].insert(typeHash(EVTy));
      return true;
    } else {
      escapeType(STy, FieldIdx);
      return false;
    }
  }

  return false;
}

Type *getPointerType(Type *T) {
  if (PointerType *PT = dyn_cast<PointerType>(T)) {
    return getPointerType(PT->getElementType());
  } else {
    return T;
  }
}

bool CallGraphPass::typeConfineInCast(CastInst *CastI) {

  LOG_OBJ("CastInst: ", CastI);

  // If a function address is ever cast to another type and stored
  // to a composite type, the escaping analysis will capture the
  // composite type and discard it

  Value *ToV = CastI, *FromV = CastI->getOperand(0);
  Type *ToTy = ToV->getType(), *FromTy = FromV->getType();
  if (isCompositeType(FromTy)) {
    transitType(ToTy, FromTy);
    LOG("isCompositeType, done");
    return true;
  }

  if (!FromTy->isPointerTy() || !ToTy->isPointerTy())
    return false;

  Type *EToTy = getPointerType(ToTy);
  Type *EFromTy = getPointerType(FromTy);

  if (isCompositeType(EToTy) && isCompositeType(EFromTy)) {
    LOG("Adding to typeTransitTypeMap: ");
    LOG_OBJ("EToType: ", EToTy);
    LOG_OBJ("EFromType: ", EFromTy);
    typeTransitTypeMap[typeHash(EFromTy)].insert(EToTy);
  }

  if (isCompositeType(EToTy) && isCompositeType(EFromTy)) {
    transitType(EToTy, EFromTy);
    return true;
  }
  return false;
}

void CallGraphPass::escapeType(Type *Ty, int Idx) {
  LOG_OBJ("Type: ", Ty);
  if (Idx == -1)
    typeEscapeSet.insert(typeHash(Ty));
  else
    typeEscapeSet.insert(typeIdxHash(Ty, Idx));
}

void CallGraphPass::transitType(Type *ToTy, Type *FromTy, int ToIdx,
                                int FromIdx) {
  LOG_OBJ("ToType: ", ToTy);
  LOG_OBJ("FromType: ", FromTy);
  if (ToIdx != -1 && FromIdx != -1)
    typeTransitMap[typeIdxHash(ToTy, ToIdx)].insert(
        typeIdxHash(FromTy, FromIdx));
  else
    typeTransitMap[typeHash(ToTy)].insert(typeHash(FromTy));
}

void CallGraphPass::funcSetIntersection(FuncSet &FS1, FuncSet &FS2,
                                        FuncSet &FS) {
  FS.clear();
  for (auto F : FS1) {
    if (FS2.find(F) != FS2.end())
      FS.insert(F);
  }
}

// Get the composite type of the lower layer. Layers are split by
// memory loads
Type *CallGraphPass::nextLayerBaseType(Value *V, int &Idx,
                                       IndexVector *Indices) {
  LOG_OBJ("Value: ", V);

  // Case 1: GEPOperator
  if (GEPOperator *GEP = dyn_cast<GEPOperator>(V)) {
    LOG_OBJ("GEPOperator: ", GEP);

    if (GEP->getNumIndices() < 2) {
      LOG("Expecting at least two indices");
      return NULL;
    }
    if (!GEP->hasAllConstantIndices()) {
      LOG("Not all constant indices");
      return NULL;
    }
    IndexVector IntermediateIndices;
    if (!Indices) {
      LOG("Indices is NULL");
      Indices = &IntermediateIndices;
    }
    if (Indices->empty()) {
      LOG("Indices is empty");
      Indices->push_back(GEP->getOperand(1));
      for (unsigned i = 1, e = GEP->getNumIndices() - 1; i != e; ++i) {
        Indices->push_back(GEP->getOperand(i + 1));
      }
    }
    Type *Ty = GetElementPtrInst::getIndexedType(GEP->getSourceElementType(),
                                                 *Indices);
    // Check if bitcast impacts the type
    // TODO: use offsets instead of indexes to handle these cases proprely
    Type *TyBeforeBitcast = GEP->getPointerOperand()
                                ->stripPointerCasts()
                                ->getType()
                                ->getPointerElementType();
    Type *TyAfterBitcast =
        GEP->getPointerOperand()->getType()->getPointerElementType();
    if (TyBeforeBitcast != TyAfterBitcast && TyAfterBitcast == Ty) {
      LOG("Bitcast impacts types:");
      LOG_OBJ("Type before bitcast: ", TyBeforeBitcast);
      LOG_OBJ("Type after bitcast: ", TyAfterBitcast);
      int NumElemsBeforeBitcast = 0;
      int NumElemsAfterBitcast = 0;
      if (TyBeforeBitcast->isStructTy() && TyAfterBitcast->isStructTy()) {
        LOG("Both are struct types");
        NumElemsBeforeBitcast = TyBeforeBitcast->getStructNumElements();
        NumElemsAfterBitcast = TyAfterBitcast->getStructNumElements();
      } else {
        LOG("Not struct types");
        LOG_FMT("Type before: %i\n", TyBeforeBitcast->getTypeID());
        LOG_FMT("Type after: %i\n", TyAfterBitcast->getTypeID());
      }
      if (NumElemsBeforeBitcast != NumElemsAfterBitcast) {
        LOG("Bitcast impacts number of fields");
        return NULL;
      }
      Ty = TyBeforeBitcast;
    }

    LOG_OBJ("Final Type: ", Ty);
    if (!(Ty->isStructTy() || Ty->isArrayTy() || Ty->isVectorTy())) {
      LOG("Unsupported type");
      return NULL;
    }
    Value *idx = GEP->getOperand(Indices->size() + 1);
    Idx = dyn_cast<ConstantInt>(idx)->getSExtValue();
    LOG_FMT("Final index: %i\n", Idx);
    Indices->pop_back();
    return Ty;
  }
  // Case 2: LoadInst
  else if (LoadInst *LI = dyn_cast<LoadInst>(V)) {
    LOG("LoadInst");
    return nextLayerBaseType(LI->getOperand(0), Idx, Indices);
  } else if (AllocaInst *AI = dyn_cast<AllocaInst>(V)) {
    LOG_OBJ("AllocaInst: ", AI);
    Type *Ty = AI->getAllocatedType();
    LOG_OBJ("Allocated type: ", Ty);
    return Ty;
  }
  // Other instructions such as CastInst
  // FIXME: may introduce false positives
  else if (UnaryInstruction *UI = dyn_cast<UnaryInstruction>(V)) {
    LOG("UnaryInstruction");
    return nextLayerBaseType(UI->getOperand(0), Idx, Indices);
  } else {
    LOG("Unexpected type");
    return NULL;
  }
}

bool CallGraphPass::findCalleesWithMLTA(CallInst *CI, FuncSet &FS) {

  LOG_OBJ("CallInst: ", CI);

  // Initial set: first-layer results
  FuncSet FS1 = Ctx->sigFuncsMap[callHash(CI)];
  if (FS1.size() == 0) {
    // No need to go through MLTA if the first layer is empty
    LOG("Not in sigFuncsMap: MLTA failed");
    return false;
  }

  if (DEBUG) {
    for (Function *Callee : FS1)
      LOG_FMT("First-layer match: %s\n", Callee->getName().str().c_str());
  }

  FuncSet FS2, FST;

  int FieldIdx = -1;
  Value *CV = CI->getCalledValue();
  IndexVector NextLayer;
  int LayerNo = 1;
  int FirstIdx = -1;

  while (Type *LayerTy = nextLayerBaseType(CV, FieldIdx, &NextLayer)) {
    LOG_OBJ("Next layer LayerTy: ", LayerTy);
    LOG_FMT("Next layer FieldIdx: %d\n", FieldIdx);

    size_t TypeHash = typeHash(LayerTy);
    size_t TypeIdxHash = typeIdxHash(LayerTy, FieldIdx);

    // Step 1: ensure the type hasn't escaped
    if ((typeEscapeSet.find(TypeHash) != typeEscapeSet.end()) ||
        (typeEscapeSet.find(TypeIdxHash) != typeEscapeSet.end())) {
      LOG("Stopping, type escapes");
      break;
    }

    if (FirstIdx == -1)
      FirstIdx = FieldIdx;

    // Step 2: get the funcset and merge
    FS2 = typeFuncsMap[TypeIdxHash];
    funcSetIntersection(FS1, FS2, FST);
    for (Function *Callee : FST)
      LOG_FMT("Intersection after first merge: %s\n",
              Callee->getName().str().c_str());

    // Step 2b: get the funcset from typeConfineMap
    auto TCit = typeConfineMap.find(TypeHash);
    if (TCit != typeConfineMap.end()) {
      for (size_t hash : TCit->second) {
        LOG_FMT("typeConfineMap hash: %lu, with Idx: %i\n", hash, FirstIdx);
        FS2 = typeFuncsMap[hashIdxHash(hash, FirstIdx)];
        for (Function *Callee : FS2) {
          LOG_FMT("FS2 (from type confine): %s\n",
                  Callee->getName().str().c_str());
        }
        FST.insert(FS2.begin(), FS2.end());
      }
    }
    for (Function *Callee : FST)
      LOG_FMT("Intersection after typeconfine union: %s\n",
              Callee->getName().str().c_str());

      // Step 3: get transitted funcsets and merge
#if 1
    list<size_t> LT;
    LT.push_back(TypeHash);
    while (!LT.empty()) {
      size_t CT = LT.front();
      LT.pop_front();

      for (auto H : typeTransitMap[CT]) {
        LOG_FMT("typeTransitMap: from:%lu --> to:%lu\n", H, CT);
        FS2 = typeFuncsMap[hashIdxHash(H, FieldIdx)];
        funcSetIntersection(FS1, FS2, FST);
        FS1 = FST;
      }
    }
#endif
    FS1 = FST;
    if (DEBUG) {
      for (Function *Callee : FS1)
        LOG_FMT("Match after layer %i: %s\n", LayerNo,
                Callee->getName().str().c_str());
    }

    if (NextLayer.empty()) {
      LOG("Stopping, NextLayer is empty");
      break;
    }
    ++LayerNo;
  }

  FS = FS1;
  return true;
}

string getNamespace(DIScope *S) {
  if (!S) {
    return "";
  }
  string ns = getNamespace(S->getScope());
  if (!ns.empty())
    return ns + S->getName().str() + "::";
  else
    return S->getName().str() + "::";
}

void CallGraphPass::typeConfineInGlobalVarInit(Constant *Ini) {

  Type *FromTy = getPointerType(Ini->stripPointerCasts()->getType());
  Type *ToTy = getPointerType(Ini->getType());

  if (FromTy == ToTy) {
    return;
  }

  Use *OL = Ini->getOperandList();
  SmallVector<DIGlobalVariableExpression *, 1> GVs;
  for (unsigned I = 0; I < Ini->getNumOperands(); ++I) {
    LOG_OBJ("Operand: ", OL[I]);
    GlobalVariable *GV = dyn_cast<GlobalVariable>(OL[I]);
    if (!GV) {
      continue;
    }
    GV->getDebugInfo(GVs);
    for (auto *GVE : GVs) {
      DIType *DTy = GVE->getVariable()->getType();
      if (DTy == NULL) {
        continue;
      }
      LOG_OBJ("DIVariable type:", DTy);
      string TyName = DTy->getName().str();
      string NS = getNamespace(DTy->getScope());
      if (DTy->getTag() == dwarf::DW_TAG_class_type) {
        TyName = "class." + NS + TyName;
      } else {
        continue;
      }
      LOG_FMT("TyName: %s\n", TyName.c_str());
      auto TSI = structTypeMap.find(TyName);
      if (TSI == structTypeMap.end()) {
        continue;
      }
      for (Type *FromTy : TSI->second) {
        LOG("Adding to typeTransitTypeMap: ");
        LOG_OBJ("ToType: ", ToTy);
        LOG_OBJ("FromType: ", FromTy);
        typeTransitTypeMap[typeHash(FromTy)].insert(ToTy);
      }
    }
  }
}

void CallGraphPass::addStructTypeCallSignature(StructType *ST, Function *F) {
  static regex reg("([^,]+?\\([%@]?\"?)[^),*\"]+(.*)");
  string subst = "$1" + ST->getStructName().str() + "$2";
  LOG_FMT("Subst string: %s\n", subst.c_str());
  Ctx->sigFuncsMap[funcHash(F, false, &reg, &subst)].insert(F);
}

void CallGraphPass::addAddressTakenFunction(Function *F) {
  LOG_FMT("adding to AddressTakenFuncs: %s\n", F->getName().str().c_str());
  Ctx->AddressTakenFuncs.insert(F);
  LOG_FMT("adding to sigFuncsMap: %s\n", F->getName().str().c_str());
  Ctx->sigFuncsMap[funcHash(F, false)].insert(F);

  auto AI = F->arg_begin();
  if (AI == F->arg_end()) {
    return;
  }
  Type *ArgTy = getPointerType(AI->getType());
  LOG_OBJ("First argument type: ", ArgTy);

  if (!ArgTy->isStructTy()) {
    LOG("First argument type is not a struct, skipping");
    return;
  }

  auto TT = typeTransitTypeMap.find(typeHash(ArgTy));
  if (TT == typeTransitTypeMap.end()) {
    LOG("First argument type is not in typeTransitTypeMap, skipping");
    return;
  }
  for (Type *T : TT->second) {
    LOG_OBJ("Found from typeTransitTypeMap: ", T);
    if (T->isStructTy()) {
      addStructTypeCallSignature(dyn_cast<StructType>(T), F);
    }
  }
}

bool CallGraphPass::doInitialization(Module *M) {

  LOG_FMT("Module: %s\n", M->getName().str().c_str());

  DL = &(M->getDataLayout());
  Int8PtrTy = Type::getInt8PtrTy(M->getContext());
  IntPtrTy = DL->getIntPtrType(M->getContext());

  // Iterate struct types
  llvm::TypeFinder StructTypes;
  StructTypes.run(*M, true);
  for (StructType *STy : StructTypes) {
    structTypeMap[STy->getName().str()].insert(STy);
  }

  // Iterate and process globals
  for (Module::global_iterator gi = M->global_begin(); gi != M->global_end();
       ++gi) {
    GlobalVariable *GV = &*gi;
    if (!GV->hasInitializer())
      continue;
    Constant *Ini = GV->getInitializer();
    typeConfineInGlobalVarInit(Ini);
    if (!isa<ConstantAggregate>(Ini))
      continue;

    LOG_OBJ("Global variable init: ", Ini);
    typeConfineInInitializer(Ini);
  }

  // Iterate functions and instructions
  for (Function &F : *M) {

    if (F.isDeclaration())
      continue;

    LOG_FMT("Function: %s\n", F.getName().str().c_str());

    for (inst_iterator i = inst_begin(F), e = inst_end(F); i != e; ++i) {
      Instruction *I = &*i;

      if (StoreInst *SI = dyn_cast<StoreInst>(I)) {
        LOG_OBJ("Store inst: ", SI);
        typeConfineInStore(SI->getPointerOperand(), SI->getValueOperand());
      } else if (CastInst *CastI = dyn_cast<CastInst>(I)) {
        typeConfineInCast(CastI);
      }
    }

    // Collect address-taken functions.
    if (F.hasAddressTaken()) {
      addAddressTakenFunction(&F);
    }

    // Collect global function definitions.
    if (F.hasExternalLinkage() && !F.empty()) {
      // External linkage always ends up with the function name.
      StringRef FName = F.getName();
      // Map functions to their names.
      Ctx->GlobalFuncs[FName] = &F;
    }

    LOG("checking UnifiedFuncMap");
    // Keep a single copy for same functions (inline functions)
    size_t fh = funcHash(&F);
    if (Ctx->UnifiedFuncMap.find(fh) == Ctx->UnifiedFuncMap.end()) {
      Ctx->UnifiedFuncMap[fh] = &F;
    }
  }

  if (DEBUG) {
    ostringstream os;
    LOG("typeFuncsMap:");
    for (auto const &pair : typeFuncsMap) {
      os << "[Key:" << to_string(pair.first) << "]: ";
      for (Function *f : pair.second) {
        os << f->getName().str() << " ";
      }
      os << "\n";
    }
    LOG(os.str().c_str());
    os.str("");
    os.clear();
    LOG("typeConfineMap:");
    for (auto const &pair : typeConfineMap) {
      os << "[Key:" << to_string(pair.first) << "]: ";
      for (size_t second : pair.second) {
        os << to_string(second) << " ";
      }
      os << "\n";
    }
    LOG(os.str().c_str());
    os.str("");
    os.clear();
    LOG("typeTransitMap:");
    for (auto const &pair : typeTransitMap) {
      os << "[Key:" << to_string(pair.first) << "]: ";
      for (size_t second : pair.second) {
        os << to_string(second) << " ";
      }
      os << "\n";
    }
    LOG(os.str().c_str());
    string s;
    llvm::raw_string_ostream rso(s);
    LOG("typeTransitTypeMap:");
    for (auto const &pair : typeTransitTypeMap) {
      rso << "[Key:" << to_string(pair.first) << "]: ";
      for (Type *second : pair.second) {
        rso << "'";
        second->print(rso);
        rso << "' ";
      }
      rso << "\n";
    }
    LOG(rso.str().c_str());

    LOG("UnifiedFuncMap:");
    for (auto const &pair : Ctx->UnifiedFuncMap) {
      LOG(("[Key:" + to_string(pair.first) +
           "]: " + pair.second->getName().str())
              .c_str());
    }
    os.str("");
    os.clear();
    LOG("sigFuncsMap:");
    for (auto const &pair : Ctx->sigFuncsMap) {
      os << "[Key:" << to_string(pair.first) << "]: ";
      for (Function *f : pair.second) {
        os << f->getName().str() << " ";
      }
      os << "\n";
    }
    LOG(os.str().c_str());
    LOG("AddressTakenFuncs:");
    for (Function *f : Ctx->AddressTakenFuncs) {
      LOG_FMT("[%s]\n", f->getName().str().c_str());
    }
    LOG("typeEscapeSet:");
    for (size_t hash : typeEscapeSet) {
      LOG_FMT("[Key:%lu]\n", hash);
    }
  }

  return false;
}

bool CallGraphPass::doFinalization(Module *M) { return false; }

bool CallGraphPass::doModulePass(Module *M) {

  LOG_FMT("Module: %s\n", M->getName().str().c_str());

  // Use type-analysis to concervatively find possible targets of
  // indirect calls.
  for (Module::iterator f = M->begin(), fe = M->end(); f != fe; ++f) {

    Function *F = &*f;
    LOG_FMT("Function: %s\n", F->getName().str().c_str());

    size_t fh = funcHash(F);
    Function *UF = Ctx->UnifiedFuncMap[fh];
    if (!UF) {
      LOG("Not in UnifiedFuncMap, skipping");
      continue;
    }

    // Collect callers and callees
    for (inst_iterator i = inst_begin(F), e = inst_end(F); i != e; ++i) {
      // Map callsite to possible callees.
      if (CallInst *CI = dyn_cast<CallInst>(&*i)) {
        LOG_OBJ("CallInst: ", CI);
        if (IntrinsicInst *II = dyn_cast<IntrinsicInst>(CI)) {
          LOG("LLVM internal instruction");
          Value *Dst = NULL;
          Value *Src = NULL;
          // TODO: length, use offsets instead of indexes?
          if (MemCpyInst *M = dyn_cast<MemCpyInst>(II)) {
            LOG_OBJ("MemCpyInst ", M);
            Dst = M->getDest();
            Src = M->getSource();
          } else if (MemMoveInst *M = dyn_cast<MemMoveInst>(II)) {
            LOG_OBJ("MemMoveInst", M);
            Dst = M->getDest();
            Src = M->getSource();
          }
          if (Dst && Src) {
            typeConfineInStore(Dst, Src);
          }
          LOG("Skipping LLVM internal function");
          continue;
        }

        CallSite CS(CI);
        FuncSet FS;
        Function *CF = CI->getCalledFunction();
        Value *CV = CI->getCalledValue();
        if (!CF) {
          CF = dyn_cast<Function>(CV->stripPointerCasts());
        }
        string indirectFoundWith = "";
        // Indirect call
        if (CS.isIndirectCall()) {
          LOG("Inidirect call");
          if (Ctx->analysisType == ta_only) {
            findCalleesWithType(CI, FS);
            indirectFoundWith = "TA";
          } else {
            indirectFoundWith = "MLTA";
            bool ret = findCalleesWithMLTA(CI, FS);
            // To include in the output csv the cases where an indirect
            // function is called, but not assigned anywhere in the
            // target codebase, uncomment the following if statement:
            // if (!ret) {
            //   printCallGraphRow(CI, NULL, "indirect", "NOT_FOUND");
            // }
            if (!ret && Ctx->analysisType != mlta_only) {
              findCalleesWithType(CI, FS);
              indirectFoundWith = "TA";
            }
          }

          for (Function *Callee : FS) {
            printCallGraphRow(CI, Callee, "indirect", indirectFoundWith);
          }
        }
        // Direct call
        else {
          LOG("Direct call");
          // not InlineAsm
          if (CF) {
            // Call external functions
            if (CF->empty()) {
              LOG("Extrenal function call");
              StringRef FName = CF->getName();
              if (Function *GF = Ctx->GlobalFuncs[FName])
                CF = GF;
            }
            LOG_FMT("Called function: %s\n", CF->getName().str().c_str());
            // Use unified function
            size_t fh = funcHash(CF);
            Function *UF = Ctx->UnifiedFuncMap[fh];
            if (UF) {
              printCallGraphRow(CI, UF, "direct", "");
            } else {
              printCallGraphRow(CI, CF, "direct", "");
            }
          }
          // InlineAsm
          else {
            // LOG_OBJ("Inline assembly is not supported: ", CI);
          }
        }
      }
    }
  }
  return false;
}
