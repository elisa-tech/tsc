#
# Makefile for the core
# 
#
MODULES := cg-test-template/core cg-test-template/init
#each submodule is also include path
CFLAGS += -Icg-test-template/include
CFLAGS += $(patsubst %,-I%,$(MODULES))
LIBS :=
# add here in submodule makefiles
SRC := 
INCL := $(patsubst %,%/module.mk,$(MODULES))

# include makefiles from submodules
include $(patsubst %,%/module.mk,$(MODULES))

GCC := gcc
LL_CC := clang
BC_CC := clang
CC := gcc

LL_FLAGS := -g -emit-llvm -S -Xclang -disable-O0-optnone
BC_FLAGS := -g -emit-llvm -c
DEPFLAGS := -MM -MG
CFLAGS += -g -O0
CXXFLAGS += $(CFLAGS)

OBJ := $(patsubst %.c,%.o,$(filter %.c,$(SRC)))
DEP := $(OBJ:.o=.d)
LLVM := $(OBJ:.o=.ll)
BC := $(OBJ:.o=.bc)

TARGET = cgtemplate

$(TARGET): $(OBJ)
	$(CC) -o $@ $(OBJ) $(LIBS)

depend: $(DEP)
llfiles: $(LLVM)
bcfiles: $(BC)
#include C dependencies
-include $(DEP)
#-include $(LLVM)

# determine include dependencies
%.d: %.c
	@$(GCC) $(DEPFLAGS) $< $(CFLAGS) | sed -e 's@^\(.*\)\.o:@\1.d \1.o:@' > $@

%.ll: %.c
	@$(LL_CC) $(LL_FLAGS) $(CFLAGS) -o $@ $<

%.bc: %.c
	@$(BC_CC) $(LL_FLAGS) $(CFLAGS) -o $@ $<


clean:
	@rm -rf $(DEP)
	@rm -rf $(OBJ)
	@rm -rf $(LLVM)
	@rm -rf $(BC)
	@rm -rf $(TARGET)
