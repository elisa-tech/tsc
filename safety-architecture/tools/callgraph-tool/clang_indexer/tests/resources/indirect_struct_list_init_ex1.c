// SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
//
// SPDX-License-Identifier: Apache-2.0

#include <stdio.h>

struct ops_struct {
     int* (*alloc)(size_t);
     void (*free)(int*);
};

static int* impl_alloc(size_t bytes){
    return NULL;
}

static void impl_free(int* resource){
}

static const struct ops_struct impl_ops = {
    .alloc = impl_alloc,
    .free = impl_free,
};

void function(const struct ops_struct * impl)
{
    size_t bytes = 1024;
    int* resource = impl->alloc(bytes);
    impl->free(resource);
}

int main(){
    function(&impl_ops);
}
