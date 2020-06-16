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
    void (*function_pointer)();
};

struct outer_struct {
    struct mystruct inner;
};

int main()
{
    struct outer_struct struct_test;
    struct_test.inner.function_pointer = say_hello;
    (&struct_test.inner)->function_pointer = say_hello2;
    struct_test.inner.function_pointer();
}
