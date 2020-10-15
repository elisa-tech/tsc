#include "llvm/IR/DebugInfoMetadata.h"
#include <regex>

#include "Common.h"

static string fixHash(string hash) {
  // Dirty fix for issue discussed in: TODO
  static const regex reg("void\\(\\.\\.\\.\\)");
  return regex_replace(hash, reg, "void()");
}

size_t funcHash(Function *F, bool withName) {

  hash<string> str_hash;
  string output;

  string sig;
  raw_string_ostream rso(sig);
  Type *FTy = F->getFunctionType();
  FTy->print(rso);
  output = rso.str();

  if (withName) {
    output += F->getName();

#if 1
    if (!F->hasExternalLinkage()) {
      // For file local (static) functions, include the filename into the
      // hash, so that it will not collide with possible global function
      // with the same name
      DISubprogram *SP = F->getSubprogram();
      if (SP) {
        output = SP->getFilename().str() + ":" + output;
      }
    }
#endif
  }

  string::iterator end_pos = remove(output.begin(), output.end(), ' ');
  output.erase(end_pos, output.end());
  output = fixHash(output);
  LOG_FMT("hash [%lu] based on string: %s\n", str_hash(output), output.c_str());

  return str_hash(output);
}

size_t callHash(CallInst *CI) {

  CallSite CS(CI);
  Function *CF = CI->getCalledFunction();

  if (CF)
    return funcHash(CF);
  else {
    hash<string> str_hash;
    string sig;
    raw_string_ostream rso(sig);
    Type *FTy = CS.getFunctionType();
    FTy->print(rso);

    string strip_str = rso.str();
    string::iterator end_pos = remove(strip_str.begin(), strip_str.end(), ' ');
    strip_str.erase(end_pos, strip_str.end());
    strip_str = fixHash(strip_str);
    LOG_FMT("hash [%lu] based on string: %s\n", str_hash(strip_str),
            strip_str.c_str());
    return str_hash(strip_str);
  }
}

size_t typeHash(Type *Ty) {
  hash<string> str_hash;
  string sig;

  raw_string_ostream rso(sig);
  Ty->print(rso);
  string ty_str = rso.str();
  string::iterator end_pos = remove(ty_str.begin(), ty_str.end(), ' ');
  ty_str.erase(end_pos, ty_str.end());

  LOG_FMT("hash [%lu] based on string: %s\n", str_hash(ty_str), ty_str.c_str());
  return str_hash(ty_str);
}

size_t hashIdxHash(size_t Hs, int Idx) {
  hash<string> str_hash;
  LOG_FMT("hash Idx: %d\n", Idx);
  LOG_FMT("hash idx hash: %lu\n", (Hs + str_hash(to_string(Idx))));
  return Hs + str_hash(to_string(Idx));
}

size_t typeIdxHash(Type *Ty, int Idx) { return hashIdxHash(typeHash(Ty), Idx); }
