// Demonstrate callgraph with a clumsy example

#include <stdio.h>
#include <string.h>

#define MAX_INPUT_LEN 10

typedef void (*fptr_t)(char *);

struct reader_a
{
    fptr_t read;
    int other_data;
};

struct reader_b
{
    fptr_t read;
    char *other_data;
};

void flush()
{
    char c;
    while ((c = getchar()) != '\n' && c != EOF)
        ;
}

char *gets(char *);
void read_no_check(char *buffer)
{
    printf("Input to %s: ", __func__);
    gets(buffer);
}

void read_with_check(char *buffer)
{
    printf("Input to %s: ", __func__);
    if (fgets(buffer, MAX_INPUT_LEN, stdin))
        if (!strchr(buffer, '\n'))
            flush();
}

int main()
{
    char input[MAX_INPUT_LEN];
    struct reader_a safe = {.read = read_with_check};
    struct reader_b unsafe = {.read = read_no_check};
    safe.read(input);
    unsafe.read(input);
    return 0;
}
