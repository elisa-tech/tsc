// SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
//
// SPDX-License-Identifier: Apache-2.0

#include <stdio.h>

typedef void (*func_pointer)();

void say_hello()
{
    printf("Hello\n");
}

void say_hello2()
{
    printf("Hello\n");
}

func_pointer function_pointer = say_hello;

void test()
{
    function_pointer();
    function_pointer = say_hello2;
    function_pointer();
    function_pointer();
}

int main()
{
    test();
}
