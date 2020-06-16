// SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
//
// SPDX-License-Identifier: Apache-2.0

#include <stdio.h>

void say_hello(){
    printf("Hello\n");
}

struct mystruct {
    void (*function_pointer_1)();
};

void do_nothing(const struct mystruct* data){
}

static const struct mystruct struct_obj = {
    .function_pointer_1 = say_hello,
};

int main(){
    do_nothing(&struct_obj);
    struct_obj.function_pointer_1();
    do_nothing(&struct_obj);
    struct_obj.function_pointer_1();
}
