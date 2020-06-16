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
    void (*not_called_function_pointer)();
    void (*function_pointer)();
};

void function(const struct mystruct* impl)
{
    impl->function_pointer();
}

static struct mystruct struct_obj = {
    .not_called_function_pointer = say_hello,
    .function_pointer = say_hello
};

int main(){
    struct_obj.function_pointer = say_hello2;
    function(&struct_obj);
}
