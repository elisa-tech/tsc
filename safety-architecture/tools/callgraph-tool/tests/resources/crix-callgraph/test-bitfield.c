// Bitfields can be problematic. In this case, the struct bitfield_ops type in
// the IR will be: { i8, void (i32)*, i8, i8, void (i32)* }. There are two i8
// fields due to the 10-bit mask variable in the struct.
// When MLTA finds the possible functions assigned to field 'up', it 
// finds that activate() is the only possible target since that's the only
// function assigned to bitfields_ops structure field number 2 (counting from
// 1). However, when finding possible functions assigned to field 'down', MLTA
// tries to find functions assigned to field number 4. Since the mask-bitfield
// was split to two i8 fields in the struct type, this search fails to find
// any matches and reverts back to matching only the function signatures.
// Therefore, 'down' is assigned two possible indirect call targets:
// activate() and deactivate().

struct bitfield_ops {
    char bit0 : 1;
    void (*up)(int bit_nr);
    short mask : 10;
    void (*down)(int bit_nr);
};


static void activate(int bit_nr)
{
}

static void deactivate(int bit_nr)
{
}


static struct bitfield_ops self = 
{
    .bit0 = 1,
    .up = activate,
    .down = deactivate,
};

void f4_main(void){
    self.up(0);
    self.down(0);
}
