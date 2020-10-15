#include <stdio.h>

void say_hello()
{
    printf("Hello\n");
}

void say_inner1()
{
    printf("Inner1\n");
}

void say_inner2()
{
    printf("Inner2\n");
}

typedef void (*fptr_t)(void);

struct I {
    int i;
    int j;
    char k;
    unsigned p;
    fptr_t inner_fptr;
    long long a;
};

struct S {
    int i;
    fptr_t fptr;
    struct I inner1;
    struct I inner2;
};

struct O {
    struct S o_inner;
};

struct S s1 = { 
    .i = 1,
    .fptr = say_hello, 
    .inner1 = { .inner_fptr = say_inner1 },
    .inner2 = { .inner_fptr = say_inner2 } 
};

struct O o1 = {
    .o_inner = {
        .inner1 = { .inner_fptr = say_inner1 }
    }
};

int main(void)
{
    struct S s2;
    s2.fptr = say_hello;
    s2.inner2.inner_fptr = say_inner2;
    s1.fptr();
    s1.inner2.inner_fptr();
    struct O o2;
    o2.o_inner = s2;
    o2.o_inner.inner2.inner_fptr();
    o1.o_inner.inner1.inner_fptr();
}
