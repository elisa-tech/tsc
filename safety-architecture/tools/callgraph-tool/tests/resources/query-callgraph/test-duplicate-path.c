#include <stdio.h>

void say_hello()
{
    printf("Hello\n");
}

void duplicte_s4(){
    say_hello();
}

void duplicate_s3()
{
    say_hello();
    duplicte_s4();
}

void duplicate_s1()
{
    duplicate_s3();
    duplicate_s3();
}

void duplicate_s2()
{
    duplicate_s3();
}

int main()
{
    duplicate_s1();
    duplicate_s2();
    return 0;
}
