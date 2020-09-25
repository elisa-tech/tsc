#ifndef FILE2_H
#define FILE2_H

struct f2_ops{
    int i;
    char bits01 : 2;
    char bits23 : 2;
    char bits47 : 4;
    float (*expect)(int* array, int N);
};

struct f2_data{
    int N;
    int* array;
};

typedef struct f2_ops f2_ops_t;
#endif
