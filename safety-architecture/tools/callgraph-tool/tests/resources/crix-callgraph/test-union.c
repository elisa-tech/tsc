#include <stdio.h>

void say_hello()
{
    printf("Hello\n");
}

void say_int(int i)
{
    printf("Int: %i\n", i);
}

struct S
{
    union
    {
        void (*fnptr1)(void);
        void (*fnptr2)(int);
    } fptr;
};

int main(void)
{
    struct S s;
    s.fptr.fnptr1 = say_hello;
    s.fptr.fnptr1();
    s.fptr.fnptr2 = say_int;
    s.fptr.fnptr2(0);
    return 0;
}
