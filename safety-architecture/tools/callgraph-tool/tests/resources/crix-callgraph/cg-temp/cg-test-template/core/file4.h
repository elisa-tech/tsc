#ifndef FILE4_H
#define FILE4_H

struct bitfield_ops {
    char bit0 : 1;
    char bit1 : 1;
    char bits2_5 : 4;
    char bits6_9 : 4;
    void (*up)(int bit_nr, void* ops);
    void (*down)(int bit_nr, void* ops);
    short mask : 10;
};

#endif
