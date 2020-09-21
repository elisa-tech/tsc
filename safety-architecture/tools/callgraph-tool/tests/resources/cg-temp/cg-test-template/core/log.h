#ifndef LOG_H
#define LOG_H

#ifndef NO_LOGGING
#include <stdio.h>

#define log(func) \
    printf("__FUNCTION__ = %s\n", func)

#else

#define log(func) \

#endif

#endif

