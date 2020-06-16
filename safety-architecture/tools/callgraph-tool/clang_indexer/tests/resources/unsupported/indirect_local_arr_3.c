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

typedef void (*func_pointer)();

void test()
{
    func_pointer function_arr[10] = { say_hello, say_hello2 };
    function_arr[1]();
}

int main()
{
    test();
}
