// SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved
//
// SPDX-License-Identifier: LicenseRef-LLVM

#ifndef ANALYZER_GLOBAL_H
#define ANALYZER_GLOBAL_H

#include <fstream>
#include <sstream>
#include <unordered_map>

#include "Common.h"

enum AnalysisType { mlta_pref, mlta_only, ta_only };
enum Demangle { demangle_debug_only, demangle_all, demangle_none };

//
// typedefs
//
typedef vector<pair<llvm::Module *, llvm::StringRef>> ModuleList;
// The set of all functions.
typedef llvm::SmallPtrSet<llvm::Function *, 8> FuncSet;
// Mapping from function name to function.
typedef unordered_map<string, llvm::Function *> NameFuncMap;

struct GlobalContext {

  GlobalContext() {}

  // Map global function name to function.
  NameFuncMap GlobalFuncs;

  // Functions whose addresses are taken.
  FuncSet AddressTakenFuncs;

  // Unified functions -- no redundant inline functions
  DenseMap<size_t, Function *> UnifiedFuncMap;

  // Map function signature to functions
  DenseMap<size_t, FuncSet> sigFuncsMap;

  // Modules.
  ModuleList Modules;

  AnalysisType analysisType = mlta_pref;
  Demangle demangle = demangle_debug_only;
  bool nocpp = false;

  ofstream csvout;
};

class IterativeModulePass {
protected:
  GlobalContext *Ctx;
  const char *ID;

public:
  IterativeModulePass(GlobalContext *Ctx_, const char *ID_)
      : Ctx(Ctx_), ID(ID_) {}

  // Run on each module before iterative pass.
  virtual bool doInitialization(llvm::Module *M) { return true; }

  // Run on each module after iterative pass.
  virtual bool doFinalization(llvm::Module *M) { return true; }

  // Iterative pass.
  virtual bool doModulePass(llvm::Module *M) { return false; }

  virtual void run(ModuleList &modules);
};

#endif
