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

int main()
{
    struct mystruct struct_test;
    struct_test.function_pointer = say_hello;
    struct_test.function_pointer();
}
