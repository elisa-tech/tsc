// SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
//
// SPDX-License-Identifier: Apache-2.0

#include <stdio.h>

int say_hello()
{
    printf("Hello\n");
    return 1;
}

struct mystruct {
    int val;
    int (*function_pointer)();
};

static struct mystruct struct_obj = { 0, say_hello };

int main(){
    struct_obj.function_pointer();
}
