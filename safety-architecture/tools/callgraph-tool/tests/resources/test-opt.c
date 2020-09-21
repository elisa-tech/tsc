// When compiled with -O0, empty functions should stay
// in the generated callgraph.
// When compiled with -O1, empty functions are optimized away,
// which should also be visible in the generated callgraph.
// The test in this file is to compile it with both -O0 and -O1
// and verify that the empty function is included only into the 
// -O0 build.

void do_nothing()
{
}

int main()
{
    do_nothing();
}
