# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

CC      = gcc
CFLAGS  = -O0
INC     = -I./

#List of target programs
PROGS = \
  direct\
  indirect_local_var_1\
  indirect_local_var_2\
  indirect_local_var_3\
  indirect_local_var_4\
  indirect_global_var_1\
  indirect_struct_1\
  indirect_struct_2\
  indirect_struct_3\
  indirect_struct_list_init_1\
  indirect_struct_list_init_2\
  indirect_struct_list_init_3\
  indirect_struct_list_init_4\
  indirect_struct_list_init_5\
  indirect_struct_list_init_6\
  indirect_struct_list_init_7\
  indirect_struct_list_init_ex1\
  indirect_param_call_1\
  indirect_param_call_2\
  indirect_param_call_3\
  indirect_param_call_4\
  indirect_param_call_5\
  indirect_param_call_6\
  indirect_nested_call_1\
  indirect_nested_call_2\
  indirect_nested_call_3\

#PROGS = direct

all: $(PROGS)

# Make this target .PHONY to always run the recipe
.PHONY: $(PROGS)
$(PROGS): %: %.c
	$(CC) $(CFLAGS) $(INC) -o $@ $<

clean-progs:
	rm -f $(PROGS)

clean: clean-progs
	rm -f compile_commands.json

