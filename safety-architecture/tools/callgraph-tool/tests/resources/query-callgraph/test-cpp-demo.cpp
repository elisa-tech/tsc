// Demonstrate C++ callgraph with a simple example

#include <iostream>

using namespace std;

////////////////////////////////////////////////////////////////////////////////

class Worker 
{
public:
    virtual void do_init() = 0;
    virtual void do_work() = 0;
    virtual void run();
};


void Worker::run()
{
    cout << __PRETTY_FUNCTION__ << "\n";

    // Call implementation from the derived class:
    this->do_init();
    this->do_work();
}

////////////////////////////////////////////////////////////////////////////////

class DummyWorker: public Worker
{
public:
    void do_init();
    void do_work();
};

void DummyWorker::do_init()
{
    cout << __PRETTY_FUNCTION__ << "\n";
}
void DummyWorker::do_work()
{
    cout << __PRETTY_FUNCTION__ << "\n";
}

////////////////////////////////////////////////////////////////////////////////

int main()
{
    DummyWorker w;
    w.run();
    return 0;
}

////////////////////////////////////////////////////////////////////////////////
