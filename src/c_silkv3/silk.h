#ifndef SILK_H
#define SILK_H

#include <stdint.h>
#include <Python.h>

#ifdef _WIN32
    #ifdef SILK_EXPORTS
        #define SILK_API __declspec(dllexport)
    #else
        #define SILK_API __declspec(dllimport)
    #endif
#else
    #define SILK_API
#endif

SILK_API uint8_t is_le(void);
SILK_API void* PyMem_Malloc_EnsureGIL(size_t size);
SILK_API void PyMem_Free_EnsureGIL(void* p);
SILK_API int16_t swap_i16(int16_t data);
SILK_API int SHOULD_SWAP(void);

#endif