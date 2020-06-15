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

void call_function(struct mystruct* struct_param)
{
    struct_param->function_pointer();
}

void nested_call(struct mystruct* struct_param)
{
    call_function(struct_param);
}

int main()
{
    struct mystruct struct_test;
    struct_test.function_pointer = say_hello;
    nested_call(&struct_test);
}
