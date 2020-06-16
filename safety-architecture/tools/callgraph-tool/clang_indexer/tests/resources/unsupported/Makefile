# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

CC      = gcc
CFLAGS  = -O0
INC     = -I./

#List of target programs
PROGS = \
  indirect_func_return_1\
  indirect_func_return_2\
  indirect_incorrect_1\
  indirect_incorrect_2\
  indirect_local_arr_1\
  indirect_local_arr_2\
  indirect_local_arr_3\
  indirect_struct_list_init_8\

all: $(PROGS)

# Make this target .PHONY to always run the recipe
.PHONY: $(PROGS)
$(PROGS): %: %.c
	$(CC) $(CFLAGS) $(INC) -o $@ $<

clean-progs:
	rm -f $(PROGS)

clean: clean-progs
	rm -f compile_commands.json

