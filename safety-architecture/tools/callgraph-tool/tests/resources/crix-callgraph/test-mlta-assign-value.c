#include <stdio.h>

void say_hello1()
{
    printf("Hello1\n");
}
void say_hello2()
{
    printf("Hello2\n");
}
void say_hello3()
{
    printf("Hello3\n");
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

struct S s = {
    .fptr = say_hello1,
    .inner2 = { .inner_fptr = say_inner2 }
};

struct S s_array[3] = { 
    {
        .fptr = say_hello2, 
    }
};

struct S empty = {};

int main(void)
{
    struct S s_new = s;
    s_new.inner2.inner_fptr(); // say_inner2
    s_array[2] = s; // Type escapes here
    s_array[2].fptr(); // say_hello1, say_hello2
}
