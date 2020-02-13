<!--
SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: Apache-2.0
-->

# Configuration file

The name of the input configuration file can be specified using the command line
option _config_. Configuration file uses YAML format.
There are three main groups of options (keys):
* Direct
* Indirect
* TriggerMapIgnore

## Key Direct

_Trigger_, in the terminology of this tool, is defined as a named point in a particular
code which causes other part of the code of interest to be executed. The name of the
trigger may be same as the name of a function in the code but this is not the prerequisite. 
It can also relate to the context of execution of a certain function, like timer or interrupt context.
In order to track which triggers cause a certain part of the code to be executed we create
a trigger map/database. Under the 'Direct' key we provide a list of triggers that we want to 
store in the database for later recall. Each trigger is anchored using the name of the triggering function. I.e. for trigger _getcpu_ with caller function ___x86_sys_getcpu_ we define the following entry:
```
Direct:
    getcpu:
      __x64_sys_getcpu
```
Multiple calling functions can be assigned to the same trigger. For example, the
interrupt trigger _lineevent_irq_ has two functions _lineevent_irq_handler_ and
_lineevent_irq_thread_. Continuing the previous configuration setup, configuration file has
the following entries:

```
Direct:
    getcpu:
      __x64_sys_getcpu
    lineevent_irq:
    - lineevent_irq_handler
    - lineevent_irq_thread
```
For every function in the call graph database that can be called from any of the triggers in the list there is an entry in the trigger map database where key is the called function and value is the trigger.
The path from the trigger to the called function can be either directl or indirect. Once the map is build, user can easily get an answer which triggers might have caused the execution of the code under study.

_Sidenote:_ This configuration option is also utilized when processing _multipath_ command line option.
Here, the information on the trigger related functions is used to highlight (colorize) the nodes
in the graph that are in the trigger list.


## Key Indirect

The common pattern in the C code is utilization of the _structs_ to define an interface
for a particular functionality. This way the implementation is abstracted away and the
user code can call all the submodules implementing the aforementioned interface in an
unified manner. However, the consequence is that it becomes harder to track the function 
call paths in the code. A simple strategy, inspecting _caller_ body to find _callees_ (i.e
new routes in the path) does not work here, which leaves many code paths in the callgraph
unfinished/hanging.


### Structure API example

On of the functionalities in Linux that uses this API mechanism is high-resolution
timer(_struct hrtimer_). The full interface for high-resolution timer support can 
be found in <linux/hrtimer.h>. In this case, the following member represents the
indirect call interface:
```
enum hrtimer_restart (*function)(struct hrtimer *);
```
As expected, _function()_ will be called when timer expires. Linux uses _hrtimers_
for scheduling, e.g. in <kernel/sched/fair.c>:
```
void init_cfs_bandwidth(struct cfs_bandwidth *cfs_b)
{
    ...
     
    INIT_LIST_HEAD(&cfs_b->throttled_cfs_rq);
    hrtimer_init(&cfs_b->period_timer, CLOCK_MONOTONIC, HRTIMER_MODE_ABS_PINNED);
    cfs_b->period_timer.function = sched_cfs_period_timer;
    hrtimer_init(&cfs_b->slack_timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
     
    ...
}
```
The callback follow-up is implemented in <kernel/time/hrtimer.c>:
```
static void __run_hrtimer(struct hrtimer_cpu_base *cpu_base,
                          struct hrtimer_clock_base *base,
                          struct hrtimer *timer, ktime_t *now,
                          unsigned long flags)
{
        enum hrtimer_restart (*fn)(struct hrtimer *);
       ...
        fn = timer->function;
        ....
        /*
         * The timer is marked as running in the CPU base, so it is
         * protected against migration to a different CPU even if the lock
         * is dropped.
         */
        raw_spin_unlock_irqrestore(&cpu_base->lock, flags);
        trace_hrtimer_expire_entry(timer, now);
        restart = fn(timer);
        trace_hrtimer_expire_exit(timer);
        raw_spin_lock_irq(&cpu_base->lock);
        ...
}
```
It is obvious in the example that, by the time the callback function is called, we have lost the track of the name of the actual function being called. There is also an additional level of indirection in form of the local callback function declaration - fn. The callgraph build tool is capable of handling these, too.

### Defining new indirect calls
In order to track indirect paths in the code user needs to explicitly define relevant 'inflection' points in the code under
the key option 'Indirect'. The entries in this configuration block follow the same logic as in the Direct block, but this time the definition is a bit more involved.

To define a caller, the corresponding structure type name and member (function callback definition) are specified in the name\_of\_the\_structure\_type.callback\_member\_name format. For example, in the above mentioned type _struct timer_ which has function callback member _enum hrtimer\_restart (*function)(struct hrtimer *)_, configuration entry for caller is specified as _hrtimer.function_. This caller is "virtual" in the sense that it doesn't exist anywhere in the code; it represents the function pointer in the _hrtimer_ structure. The actual callers of this function pointer are enumerated automatically by the script and they don't have to be configured manually.

Also, the concrete function which should be tracked through the indirect call interface - analog to the function name in the direct configuration block - needs to be defined. Following the example with _hrtimer_, to track the callback function we can specify the callee as the name of the function that was assigned to the function member of the _hrtimer_ structure during the initialization of a particular instance of this object. In example of init\_cfs\_bandwidth the callee is sched\_cfs\_period\_timer.

```
Indirect:
    hrtimer.function:
    - sched_cfs_period_timer
```
This allows us to bridge this indirection in a call graph. With this functionality implemented, it is possible to track the path from system call / interrupt / timer to the end callee (which is usually the part of the bug-fix commit code that we are interested in).

In following example, the top-level functionality that calls this part of the code is hrtimer software interrupt registration and this information needs to be included into the configuration file (Note: hrtimer\_run\_softirq is a called from open\_softirq, but this is only matter of the granularity at which the analysis is being performed, i.e. configuration with which the callgraph database was generated.).

## Key TriggerMapIgnore
By default, there are not entries in the trigger map database that contain 
trigger functions as keys. We can extend this list by defining the additional
names under key 'TriggerMapIgnore' in configuration file. E.g. to prevent building the trigger information for functions _do_current_softirqs_ and _notifier_call_chain_ following entry needs to be added to the file:
```
TriggerMapIgnore:
- do_current_softirqs
- notifier_call_chain
```