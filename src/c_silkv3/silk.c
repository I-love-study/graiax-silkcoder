#include "silk.h"

uint8_t is_le()
{
    uint16_t data=1;
    return *(uint8_t*)&data;
}

void* PyMem_Malloc_EnsureGIL(size_t size) {
    PyGILState_STATE state = PyGILState_Ensure();
    void* ptr = PyMem_Malloc(size);
    PyGILState_Release(state);
    return ptr;
}

void PyMem_Free_EnsureGIL(void* p) {
    PyGILState_STATE state = PyGILState_Ensure();
    PyMem_Free(p);
    PyGILState_Release(state);
};

#ifdef _WIN32
    #define swap_i16 _byteswap_ushort
#else
    #define swap_i16 __builtin_bswap16
#endif /* _WIN32 */

#ifdef _SYSTEM_IS_BIG_ENDIAN
    #define SHOULD_SWAP() 1
#else
    #define SHOULD_SWAP() 0
#endif