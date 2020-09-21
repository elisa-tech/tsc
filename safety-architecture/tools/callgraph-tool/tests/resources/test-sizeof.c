// Test sizeof: sizeof is evaluated at compile time 
#include <stdio.h>

static inline int func() { 
    printf("func()\n");
    return 0;
} 

int main()
{
    printf("main, before sizeof()\n");
    // func is an argument to sizeof, which is a compile time operator: 
    // therefore, the below line doesn't call func() at run time
    (void) sizeof( (func()) );
    printf("main, after sizeof()\n");
    func();
    printf("main, after func()\n");
}

/*
# Prints:
main, before sizeof()
main, after sizeof()
func()
main, after func()
*/