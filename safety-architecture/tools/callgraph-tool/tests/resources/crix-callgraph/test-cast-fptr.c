// Test casting function pointer

typedef void (*func_pointer)(int);

static void icall(int i) {
}

static void caller(void* fptr) {
    func_pointer f = (func_pointer)fptr;
    f(0);
}

void test_main(void){
    caller(icall);
}
