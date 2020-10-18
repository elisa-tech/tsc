#include <stdio.h>
#include <string.h>

void say_hello(void)
{
    printf("Hello\n");
}

void say_inner1()
{
    printf("Inner1\n");
}

void say_inner2(void)
{
    printf("Inner2\n");
}

void say_int(int i) {
    printf("Int: %i\n", i);
}

typedef void (*fptr_t)();
typedef void (*fptr_t_int)(int);

struct I {
    int i;
    int j;
    char k;
    unsigned p;
    fptr_t i_fptr;
    fptr_t_int i_fptr_int;
    long long a;
};

struct S {
    int i;
    fptr_t s_fptr;
    fptr_t_int s_fptr_int;
    struct I s_i_inner1;
    struct I s_i_inner2;
};

struct O {
    struct S o_s_inner;
};

int main(void)
{
    struct O o;
    o.o_s_inner.s_i_inner1.i_fptr = NULL;
    o.o_s_inner.s_i_inner1.i_fptr();
}
