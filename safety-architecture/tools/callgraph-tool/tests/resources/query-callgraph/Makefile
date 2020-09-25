CC      = clang
CFLAGS  = -O0 -g
INC     = -I./

SHELL := /bin/bash
CLANG_BIN_DIR := /usr/lib/llvm-10/bin
CG_BIN := ../../../build/lib/crix-callgraph
PATH := $(CLANG_BIN_DIR):$(PATH)

# List of target programs
PROGS = \
  test-chain\

progs: $(PROGS)

# Check clang is in PATH
.PHONY: clang-check
clang-check:
	@which clang >/dev/null

cg-bin:
	cd ../../../ && make crix-callgraph

# Build bitcode files from the targets in PROGS
# Run CG_BIN to generate the callgraph for each bitcode target
.PHONY: $(PROGS)
$(PROGS): %: %.c clang-check cg-bin
	$(CC) $(CFLAGS) $(INC) -emit-llvm -c -o $@.bc $<
# .bclist is just a list of .bc files that will be analyzed together
	echo $@.bc >$@.bclist
	$(CG_BIN) -o $@.csv @$@.bclist 2>/dev/null

clean:
	find . -type f -name "*.bc" -delete
	find . -type f -name "*.bclist" -delete
	find . -type f -name "*.png" -delete
	find . -type f -name "*.csv" -delete
