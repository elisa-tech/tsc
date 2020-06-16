// SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
//
// SPDX-License-Identifier: Apache-2.0

#include <stdio.h>

void say_hello()
{
    printf("Hello\n");
}

void call_function(int integer, void (*fun)())
{
    fun();
}

int main()
{
    int i_in_main = 1;
    call_function(i_in_main, say_hello);
}
