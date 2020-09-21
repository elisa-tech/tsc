// Test inline function call

void actual_call()
{
}

// 'inlined_func' will always be inlined.
static inline __attribute__((__always_inline__)) void
inlined_func()
{
    actual_call();
}

// 'another_inlined_func' will also always be inlined.
static inline __attribute__((__always_inline__)) void
another_inlined_func()
{
}

int main()
{
    // inlined_func() will be inlined here.
    // It calls actual_call(), so the output will include a call
    // from main.c:27 to actual_call() at main.c:3. 
    // Field 'callee_inlined_from_line' will be line 11, which is the
    // line number of the actual_call() call in the inlined_func()
    inlined_func();

    // antoher_inlined_func() will be inlined here.
    // Since there are no function calls from another_inlined_func(),
    // the inlined function call will not be recorded - i.e. this
    // call will not be visible in the output csv
    another_inlined_func();
}