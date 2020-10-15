// Bitfields can be problematic. In this case, the struct bitfield_ops type in
// the IR will be: { i8, void (i32)*, i8, i8, void (i32)* }. There are two i8
// fields due to the 10-bit mask variable in the struct.
// After bitcast operation, the type will be converted to:
// { i8, void (i32)*, i16, void (i32)* }, merging the two i8 fields into one
// i16 field. This has an impact on the struct field indexes.
// crix-callgraph identifies when a bitcast operation impacts the number
// fields in the structure, and reverts back to matching only the function
// signatures in such cases. Therefore, both 'up' and 'down' are assigned
// two possible indirect call targets: activate() and deactivate() in this
// example. Notice: if the bitfield size is less than or equal to 8 bits,
// the revert does not occur.

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
