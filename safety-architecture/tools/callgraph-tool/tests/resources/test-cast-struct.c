// Test casting struct
struct struct_test {
    int i;
    void (*function_ptr)(int i);
};

static void icall(int i) {
}

static void caller(void* data) {
    struct struct_test* cast_result = (struct struct_test*)data;
    cast_result->function_ptr(2);
}

static struct struct_test self = 
{
    .i = 1,
    .function_ptr = icall
};

void test_main(void){
    caller(&self);
}
