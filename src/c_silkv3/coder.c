#define PY_SSIZE_T_CLEAN

#include <Python.h>

#include "decoder.h"
#include "encoder.h"

static PyMethodDef SilkMethods[] = {
    {"decode", (PyCFunction)(void (*)(void))decode_silk,
     METH_VARARGS | METH_KEYWORDS, "Decode a silk file to pcm file."},
    {"encode", (PyCFunction)(void (*)(void))encode_silk,
     METH_VARARGS | METH_KEYWORDS, "Encode a pcm file to silk file."},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

static PyModuleDef silk_module = {
    PyModuleDef_HEAD_INIT,
    "Silkv3",
    "Lib for converting silk v3 format audio file",
    -1,
    SilkMethods,
    NULL, /* inquiry m_reload */
    NULL, /* traverseproc m_traverse */
    NULL, /* inquiry m_clear */
    NULL, /* freefunc m_free */
};

PyMODINIT_FUNC PyInit__silkv3(void) { return PyModule_Create(&silk_module); }
