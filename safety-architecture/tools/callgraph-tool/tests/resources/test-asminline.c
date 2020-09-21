// Verify function calls in inline assembly are *not* detected
void callee(void) 
{
}

void inline_asm_caller(void)
{
    asm("call callee\n");
}

int main()
{
    inline_asm_caller();
}