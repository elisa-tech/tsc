// Test type escape
// Inspired by mm/mempool.c

typedef void (*mempool_alloc_t)(int i);

typedef struct mempool_s {
	mempool_alloc_t alloc;
} mempool_t;

int mempool_init_node(mempool_t *pool, mempool_alloc_t alloc_fn)
{
    pool->alloc = alloc_fn;
    pool->alloc(1);
    return 0;
}

void icall(int i) {
}

int test_main() {
    mempool_t pool;
    mempool_init_node(&pool, icall);
    return 0;
}