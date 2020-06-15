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

void call_function(struct mystruct* struct_param)
{
    struct_param->function_pointer();
}

int main()
{
    struct mystruct struct_test;
    // Resolve needs to be fixed to include all possible assignments, not
    // only the latest one before the call. For instance, the below example
    // incorrectly assigns only 'say_hello2' as call target to 
    // struct_test.function_pointer():
    if(1) {
        struct_test.function_pointer = say_hello;
    }
    if(0) {
        struct_test.function_pointer = say_hello2;
    }
    call_function(&struct_test);
}
