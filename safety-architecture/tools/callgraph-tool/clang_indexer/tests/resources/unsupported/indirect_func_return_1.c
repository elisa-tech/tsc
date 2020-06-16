// SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
//
// SPDX-License-Identifier: Apache-2.0

#include <stdio.h>

void say_hello()
{
    printf("Hello\n");
}

typedef void (*void_fptr);

void_fptr return_fptr()
{
    return say_hello;
}

void test()
{
    void (*function_pointer)();
    function_pointer = return_fptr();
    function_pointer();
}

int main()
{
    test();
}
