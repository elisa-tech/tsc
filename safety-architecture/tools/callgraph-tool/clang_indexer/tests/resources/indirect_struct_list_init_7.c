// SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
//
// SPDX-License-Identifier: Apache-2.0

#include <stdio.h>

int say_hello()
{
    printf("Hello\n");
    return 1;
}

int say_hello2()
{
    printf("Hello\n");
    return 1;
}

struct mystruct {
    int val;
    int (*function_pointer1)();
    int (*function_pointer2)();
    int (*function_pointer3)();
};

// static struct mystruct struct_obj = { }

static struct mystruct struct_obj = { 
    0, 
    .function_pointer2 = say_hello,
    say_hello2 };

int main(){
    struct_obj.function_pointer2();
    struct_obj.function_pointer3();
}
