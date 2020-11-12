#ifndef TEST_MODULES_BASE_H 
#define TEST_MODULES_BASE_H 

class Base
{
private:
  const char *ID;

public:
    Base(const char *name) : ID(name) {}
    // Base's definition in header file
    virtual void do_init(){ return; }
    virtual void do_work(){ return; }
    virtual void do_final(){ return; }

    // Base's definition in cpp-file
    virtual void run();
};

#endif