// SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
//
// SPDX-License-Identifier: Apache-2.0

#include <stdio.h>

void say_hello()
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

static const struct mystruct struct_obj = {
    .not_called_function_pointer = say_hello,
    .function_pointer = say_hello
};

int main(){
    function(&struct_obj);
}
