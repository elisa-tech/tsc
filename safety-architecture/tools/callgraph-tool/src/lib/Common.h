#ifndef COMMON_H
#define COMMON_H

#include <llvm/IR/Module.h>
#include <llvm/Analysis/TargetLibraryInfo.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/Support/CommandLine.h>
#include <llvm/IR/DebugInfo.h>

#include <unistd.h>
#include <bitset>
#include <chrono>
#include <stdio.h>

using namespace llvm;
using namespace std;

#define OP llvm::errs()

#define DEBUG 0

#define DSTREAM stderr
#define LOG(str) LOG_FMT("%s\n", str)
#define LOG_OBJ(str, obj) \
    do { \
      if (DEBUG) {\
        LOG_FMT("%s ", str); \
        obj->print(OP); \
        OP << "\n"; \
      } \
    } while(0)
#define LOG_FMT(fmt, ...) \
    do { \
      if (DEBUG) \
        fprintf(DSTREAM, "[%s:%d]: " fmt, __func__, __LINE__, __VA_ARGS__);\
    } while (0)
#define DEBUG_SPAM 2

//
// Common functions
//

size_t funcHash(Function *F, bool withName = true);
size_t callHash(CallInst *CI);
size_t typeHash(Type *Ty);
size_t typeIdxHash(Type *Ty, int Idx = -1);
size_t hashIdxHash(size_t Hs, int Idx = -1);

#endif
