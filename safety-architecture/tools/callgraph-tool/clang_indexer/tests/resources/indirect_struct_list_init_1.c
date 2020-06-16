// SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
//
// SPDX-License-Identifier: Apache-2.0

#include <stdio.h>

void say_hello()
{
    printf("Hello\n");
}

struct mystruct {
    void (*function_pointer)();
};

static const struct mystruct struct_init_assignment = {
    .function_pointer = say_hello,
};

int main()
{
    struct_init_assignment.function_pointer();
}
