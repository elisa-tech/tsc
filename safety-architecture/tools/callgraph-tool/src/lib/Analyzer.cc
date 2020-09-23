//===-- Analyzer.cc - the kernel-analysis framework--------------===//
//
// This file implements the analysis framework. It calls the pass for
// building call-graph and the pass for finding security checks.
//
// ===-----------------------------------------------------------===//

#include "llvm/Bitcode/BitcodeReader.h"
#include "llvm/Bitcode/BitcodeWriter.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/PassManager.h"
#include "llvm/IR/Verifier.h"
#include "llvm/IRReader/IRReader.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/ManagedStatic.h"
#include "llvm/Support/Path.h"
#include "llvm/Support/PrettyStackTrace.h"
#include "llvm/Support/Signals.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/Support/SystemUtils.h"
#include "llvm/Support/ToolOutputFile.h"

#include <memory>
#include <sstream>
#include <sys/resource.h>
#include <vector>

#include "Analyzer.h"
#include "CallGraph.h"
#include "Common.h"

using namespace llvm;

// Command line parameters.
cl::list<string> InputFilenames(cl::Positional, cl::OneOrMore,
                                cl::desc("<input bitcode files>"));

cl::OptionCategory CallgraphCategory("Callgraph Options");

cl::opt<string> optOutFilename("o", cl::desc("Specify output CSV filename"),
                               cl::value_desc("filename"),
                               cl::init("callgraph.csv"),
                               cl::cat(CallgraphCategory));

cl::opt<AnalysisType> optAnalysisType(
    cl::desc("Resolve indirect call targets with:"),
    cl::values(
        clEnumVal(mlta_pref,
                  "Prefer MLTA, fallback to TA if MLTA failed (default)"),
        clEnumVal(mlta_only, "Find targets of indirect calls based on MLTA"),
        clEnumVal(
            ta_only,
            "Find targets of indirect calls based on type analysis (TA)")),
    cl::cat(CallgraphCategory));

GlobalContext GlobalCtx;

void IterativeModulePass::run(ModuleList &modules) {

  ModuleList::iterator i, e;
  OP << "[" << ID << "] Initializing " << modules.size() << " modules ";
  bool again = true;
  while (again) {
    again = false;
    for (i = modules.begin(), e = modules.end(); i != e; ++i) {
      if (DEBUG)
        OP << "\n";
      again |= doInitialization(i->first);
      OP << ".";
    }
  }
  OP << "\n";

  unsigned iter = 0, changed = 1;
  while (changed) {
    ++iter;
    changed = 0;
    unsigned counter_modules = 0;
    unsigned total_modules = modules.size();
    for (i = modules.begin(), e = modules.end(); i != e; ++i) {
      OP << "[" << ID << " / " << iter << "] ";
      OP << "[" << ++counter_modules << " / " << total_modules << "] ";
      OP << "[" << i->second << "]";
      if (DEBUG)
        OP << "\n";

      bool ret = doModulePass(i->first);
      if (ret) {
        ++changed;
        OP << "\t [CHANGED]\n";
      } else
        OP << "\n";
    }
    OP << "[" << ID << "] Updated in " << changed << " modules.\n";
  }

  OP << "[" << ID << "] Postprocessing ...\n";
  again = true;
  while (again) {
    again = false;
    for (i = modules.begin(), e = modules.end(); i != e; ++i) {
      // TODO: Dump the results.
      again |= doFinalization(i->first);
    }
  }

  OP << "[" << ID << "] Done!\n\n";
}

int main(int argc, char **argv) {

  // Print a stack trace if we signal out.
  sys::PrintStackTraceOnErrorSignal(argv[0]);
  PrettyStackTraceProgram X(argc, argv);

  llvm_shutdown_obj Y; // Call llvm_shutdown() on exit.

  cl::HideUnrelatedOptions(CallgraphCategory);
  cl::ParseCommandLineOptions(argc, argv, "Crix Callgraph\n");
  GlobalCtx.analysisType = optAnalysisType;
  GlobalCtx.csvout.open(optOutFilename);
  SMDiagnostic Err;

  // Loading modules
  OP << "Total " << InputFilenames.size() << " file(s)\n";

  for (unsigned i = 0; i < InputFilenames.size(); ++i) {

    LLVMContext *LLVMCtx = new LLVMContext();
    unique_ptr<Module> M = parseIRFile(InputFilenames[i], Err, *LLVMCtx);

    if (M == NULL) {
      OP << argv[0] << ": error loading file '" << InputFilenames[i] << "'\n";
      continue;
    }

    Module *Module = M.release();
    StringRef MName = StringRef(strdup(InputFilenames[i].data()));
    GlobalCtx.Modules.push_back(make_pair(Module, MName));
  }

  // Build global callgraph.
  CallGraphPass CGPass(&GlobalCtx);
  CGPass.run(GlobalCtx.Modules);
  OP << "[Wrote: " << optOutFilename << "]\n";

  return 0;
}
