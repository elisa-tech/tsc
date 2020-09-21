// Example from paper:
// https://www-users.cs.umn.edu/~kjlu/papers/mlta.pdf

#include <stdio.h>
#include <string.h>

typedef void (*fptr_t)(char *, char *);

struct A { fptr_t handler; };
struct B { struct A a; }; // B is an outer layer of A
struct C { struct A a; }; // C is an outer layer of A

#define MAX_LEN 10

void copy_with_check(char *dst, char *src) {
    if (strlen(src) < MAX_LEN) strcpy(dst, src);
}

void copy_no_check(char *dst, char *src) {
    strcpy(dst, src);
}

// Store functions with initializers
struct B b = { .a = { .handler = &copy_with_check } };

// Store function with store instruction
struct C c;

int main()
{
    c.a.handler = &copy_no_check;
    char buf[MAX_LEN];
    char user_input[2*MAX_LEN];
    (*b.a.handler)(buf, user_input); // safe
    (*c.a.handler)(buf, user_input); // buffer overflow !!
}
