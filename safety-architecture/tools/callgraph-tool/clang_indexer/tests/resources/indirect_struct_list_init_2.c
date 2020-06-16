// SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
//
// SPDX-License-Identifier: Apache-2.0

#include <stdio.h>

void say_hello()
{
    printf("Hello\n");
}

void say_hello2()
{
    printf("Hello\n");
}

struct mystruct {
    void (*not_called_pointer)();
    void (*function_pointer)();
};

static const struct mystruct struct_init_assignment = {
    .not_called_pointer = say_hello2,
    .function_pointer = say_hello,
};

static const struct mystruct struct_init_assignment2 = {
    .not_called_pointer = say_hello,
    .function_pointer = say_hello2,
};

int main()
{
    struct_init_assignment2.function_pointer();
}
