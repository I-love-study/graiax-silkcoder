#ifndef _CODEC_H_
#define _CODEC_H_

#include "SKP_Silk_SDK_API.h"
#include "src/SKP_Silk_SigProc_FIX.h"

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#ifdef _WIN32
#define _CRT_SECURE_NO_DEPRECATE 1
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vector>

/* Define codec specific settings should be moved to h file */
#define ENCODE_MAX_BYTES_PER_FRAME 250 // Equals peak bitrate of 100 kbps
#define MAX_BYTES_PER_FRAME 1024
#define MAX_INPUT_FRAMES 5
#define MAX_FRAME_LENGTH 480
#define FRAME_LENGTH_MS 20
#define MAX_API_FS_KHZ 48
#define MAX_LBRR_DELAY 2

#ifdef _SYSTEM_IS_BIG_ENDIAN
/* Function to convert a little endian int16 to a */
/* big endian int16 or vica verca                 */
void swap_endian(SKP_int16 vec[], SKP_int len) {
  SKP_int i;
  SKP_int16 tmp;
  SKP_uint8 *p1, *p2;

  for (i = 0; i < len; i++) {
    tmp = vec[i];
    p1 = (SKP_uint8 *)&vec[i];
    p2 = (SKP_uint8 *)&tmp;
    p1[0] = p2[1];
    p1[1] = p2[0];
  }
}
#endif

#if (defined(_WIN32) || defined(_WINCE))
#include <windows.h> /* timer */
#else                // Linux or Mac
#include <sys/time.h>
#endif

/* Seed for the random number generator, which is used for simulating packet
 * loss */
static SKP_int32 rand_seed = 1;

#endif /* _CODEC_H_ */