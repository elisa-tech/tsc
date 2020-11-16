// SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved
//
// SPDX-License-Identifier: LicenseRef-LLVM

//===-- Analyzer.cc - the kernel-analysis framework--------------===//
//
// This file implements the analysis framework. It calls the pass for
// building call-graph and the pass for finding security checks.
//
// ===-----------------------------------------------------------===//

#include "llvm/Bitcode/BitcodeReader.h"
#include "llvm/IRReader/IRReader.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/PrettyStackTrace.h"
#include "llvm/Support/Signals.h"

#include "CallGraph.h"
#include "Common.h"
#include "VirtualCallTargets.h"

using namespace llvm;
using namespace std;
using namespace virtcall;

// Command line parameters.
cl::list<string> InputFilenames(cl::Positional, cl::OneOrMore,
                                cl::desc("<input bitcode files>"));

cl::OptionCategory CallgraphCategory("Callgraph Options");

cl::opt<string> optOutFilename(
    "o", cl::desc("Specify output CSV filename (default='callgraph.csv)"),
    cl::value_desc("filename"), cl::init("callgraph.csv"),
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

cl::opt<Demangle> optDemangle(
    cl::desc("Demangle C++ function names:"),
    cl::values(clEnumVal(demangle_debug_only,
                         "Demangle function names that are "
                         "associated with debug info (default)"),
               clEnumVal(demangle_all, "Demangle all function names"),
               clEnumVal(demangle_none, "Don't demangle function names")),
    cl::cat(CallgraphCategory));

cl::opt<string> optCppLinkedBitcode(
    "cpp_linked_bitcode",
    cl::desc(
        "Specify whole-program bitcode file for C++ virtual call resolution"),
    cl::value_desc("filename"), cl::init(""), cl::cat(CallgraphCategory));

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
  cl::ParseCommandLineOptions(
      argc, argv,
      "\n\n"
      "  Generate precise global callgraph given input bitcode files\n\n"
      "EXAMPLES:\n\n"
      "  - Generate callgraph given input file '/path/to/foo.bc', write output "
      "to default output file 'callgraph.csv':\n"
      "    crix-callgraph /path/to/foo.bc"
      "\n\n"
      "  - Generate callgraph given two input files '/path/to/foo.bc' and "
      "'/path/to/bar.bc', write output "
      "to 'foobar.csv':\n"
      "    crix-callgraph /path/to/foo.bc /path/to/bar.bc -o foobar.csv"
      "\n\n"
      "  - Generate callgraph given a text file with a list of input files "
      "'/path/to/foobar.txt' containing one bitcode input file per line, write "
      "output "
      "to 'foobar.csv':\n"
      "    crix-callgraph @/path/to/foobar.txt -o foobar.csv"
      "\n\n"

  );

  const string yellow("\033[1;33m");
  const string reset("\033[0m");
  GlobalCtx.analysisType = optAnalysisType;
  GlobalCtx.demangle = optDemangle;
  GlobalCtx.csvout.open(optOutFilename);
  SMDiagnostic Err;

  // Loading modules
  OP << "Total " << InputFilenames.size() << " file(s)\n";

  for (unsigned i = 0; i < InputFilenames.size(); ++i) {

    LLVMContext *LLVMCtx = new LLVMContext();
    unique_ptr<Module> M = parseIRFile(InputFilenames[i], Err, *LLVMCtx);

    if (M == NULL) {
      WARN_FMT("Error loading file: '%s'\n", InputFilenames[i].c_str());
      continue;
    } else if (M->getNamedMetadata("llvm.dbg.cu") == NULL) {
      WARN_FMT("Debug info missing: '%s'\n", M->getName().str().c_str());
    }

    Module *Module = M.release();
    StringRef MName = StringRef(strdup(InputFilenames[i].data()));
    GlobalCtx.Modules.push_back(make_pair(Module, MName));
  }

  // Build global callgraph
  CallGraphPass CGPass(&GlobalCtx);
  CGPass.run(GlobalCtx.Modules);
  if (!optCppLinkedBitcode.empty()) {
#if __clang_major__ <= 10
    CGPass.resolveVirtualCallTargets(optCppLinkedBitcode);
#else
    WARN_FMT("Resolving virtual call targets is currently not supported on "
             "llvm-11 or later%s",
             "\n");
#endif
  }
  OP << "[Wrote: " << optOutFilename << "]\n";

  return 0;
}
