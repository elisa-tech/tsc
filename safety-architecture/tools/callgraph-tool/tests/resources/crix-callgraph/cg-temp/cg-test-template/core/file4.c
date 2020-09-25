#include "file4.h"
#include "log.h"


static void activate(int bit_nr, void* ops)
{
    struct bitfield_ops* b = (struct bitfield_ops*)ops;
    if(bit_nr >= 10)
        return;

    b->mask |= 0x1 << bit_nr;
    if(bit_nr == 0){
        b->bit0 = 0x1;
    }else if(bit_nr == 1){
        b->bit1 = 0x1;
    }else{
        bit_nr -= 2;
        b->bits2_5 |= 0x1 << bit_nr;
    }
}

static void deactivate(int bit_nr, void* ops)
{
    struct bitfield_ops* b = (struct bitfield_ops*)ops;
    if(bit_nr >= 10)
        return;

    b->mask &= ~(0x1 << bit_nr);
    if(bit_nr == 0){
        b->bit0 = 0x0;
    }else if(bit_nr == 1){
        b->bit1 = 0x0;
    }else{
        bit_nr -= 2;
        b->bits2_5 &= ~(0x1 << bit_nr);
    }
}

static struct bitfield_ops self = 
{
    .bit0 = 1,
    .up = activate,
    .down = deactivate
};

void f4_main(void){
    self.up(2, &self);
    self.down(1, &self);
}
