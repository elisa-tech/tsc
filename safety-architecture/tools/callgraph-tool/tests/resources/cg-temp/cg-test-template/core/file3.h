#ifndef FILE3_H
#define FILE3_H

//inspired by example from mm/shmem.c
struct page {
    int *data;
    int size;
};

struct file{
    void* file;
    int size;
};

struct as_operations {
    int (*writepage)(struct page *page, void *wbc);
    int (*readpage)(struct file *file, struct page *page);
    void (*freepage)(struct page *page);
};

#endif
