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

void call_function(struct mystruct* struct_param, void (*fun))
{
    struct_param->function_pointer = fun;
    struct_param->function_pointer();
}

int main()
{
    struct mystruct struct_test;
    struct_test.function_pointer = say_hello;
    call_function(&struct_test, say_hello2);
}
