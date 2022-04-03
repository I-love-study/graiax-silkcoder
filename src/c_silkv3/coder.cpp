#include "SKP_Silk_typedef.h"
#include "codec.h"

static PyObject *encode_silk(PyObject *self, PyObject *args) {
  size_t counter;
  SKP_int16 nBytes;
  SKP_uint8 payload[ENCODE_MAX_BYTES_PER_FRAME * MAX_INPUT_FRAMES];
  SKP_int16 in[FRAME_LENGTH_MS * MAX_API_FS_KHZ * MAX_INPUT_FRAMES];
  SKP_int32 encSizeBytes, ret, pcmDataSize, tencent;
  void *psEnc = NULL;
  unsigned char *pcmData;
  std::vector<unsigned char> outputData;

#ifdef _SYSTEM_IS_BIG_ENDIAN
  SKP_int16 nBytes_LE;
#endif

  SKP_int32 targetRate_bps;

  /* Get input data */
  if (!PyArg_ParseTuple(args, "y#ii", &pcmData, &pcmDataSize, &targetRate_bps,
                        &tencent))
    return NULL;

  unsigned char *psRead = pcmData, *psReadEnd = pcmData + pcmDataSize;

  /* default settings */
  SKP_int32 API_fs_Hz = 24000;
  SKP_int32 max_internal_fs_Hz = 24000;
  SKP_int32 smplsSinceLastPacket, packetSize_ms = 20;
  SKP_int32 frameSizeReadFromFile_ms = 20;
  SKP_int32 packetLoss_perc = 0;
#if LOW_COMPLEXITY_ONLY
  SKP_int32 complexity_mode = 0;
#else
  SKP_int32 complexity_mode = 2;
#endif
  SKP_int32 DTX_enabled = 0, INBandFEC_enabled = 0;
  SKP_SILK_SDK_EncControlStruct encControl; // Struct for input to encoder
  SKP_SILK_SDK_EncControlStruct encStatus;  // Struct for status of encoder

  /* If no max internal is specified, set to minimum of API fs and 24 kHz */
  if (API_fs_Hz < max_internal_fs_Hz) {
    max_internal_fs_Hz = API_fs_Hz;
  }

  /* Add Silk header to stream */
  if (tencent)
    outputData.push_back('\x02');
  const char header[] = "#!SILK_V3";
  outputData.insert(outputData.end(), header, header + 9);

  /* Create Encoder */
  ret = SKP_Silk_SDK_Get_Encoder_Size(&encSizeBytes);
  if (ret)
    goto failed;

  psEnc = malloc(encSizeBytes);

  /* Reset Encoder */
  ret = SKP_Silk_SDK_InitEncoder(psEnc, &encStatus);
  if (ret)
    goto failed;

  /* Set Encoder parameters */
  encControl.API_sampleRate = API_fs_Hz;
  encControl.maxInternalSampleRate = max_internal_fs_Hz;
  encControl.packetSize = (packetSize_ms * API_fs_Hz) / 1000;
  encControl.packetLossPercentage = packetLoss_perc;
  encControl.useInBandFEC = INBandFEC_enabled;
  encControl.useDTX = DTX_enabled;
  encControl.complexity = complexity_mode;
  encControl.bitRate = (targetRate_bps > 0 ? targetRate_bps : 0);

  if (API_fs_Hz > MAX_API_FS_KHZ * 1000 || API_fs_Hz < 0)
    goto failed;
  smplsSinceLastPacket = 0;

  Py_BEGIN_ALLOW_THREADS;

  while (1) {
    /* Read input from file */
    if (psRead - pcmData >= pcmDataSize)
      break;

    counter = (frameSizeReadFromFile_ms * API_fs_Hz) / 1000;
    if ((int)counter > psReadEnd - psRead) {
      memset(in, 0x00, sizeof(in));

      size_t realrd = (psReadEnd - psRead);
      memcpy(in, psRead, realrd);
      psRead += realrd;
    } else {
      size_t realrd = counter * sizeof(SKP_int16);
      memcpy(in, psRead, realrd);
      psRead += realrd;
    }

#ifdef _SYSTEM_IS_BIG_ENDIAN
    swap_endian(in, counter);
#endif

    /* max payload size */
    nBytes = ENCODE_MAX_BYTES_PER_FRAME * MAX_INPUT_FRAMES;

    /* Silk Encoder */
    SKP_Silk_SDK_Encode(psEnc, &encControl, in, (SKP_int16)counter, payload,
                        &nBytes);

    /* Get packet size */
    packetSize_ms = (SKP_int)((1000 * (SKP_int32)encControl.packetSize) /
                              encControl.API_sampleRate);

    smplsSinceLastPacket += (SKP_int)counter;

    if (((1000 * smplsSinceLastPacket) / API_fs_Hz) == packetSize_ms) {

      /* Write payload size */
#ifdef _SYSTEM_IS_BIG_ENDIAN
      nBytes_LE = nBytes;
      swap_endian(&nBytes_LE, 1);
      unsigned char *p = (unsigned char *)&nBytes_LE;
      outputData.insert(outputData.end(), p, p + sizeof(SKP_int16));
#else
      unsigned char *p = (unsigned char *)&nBytes;
      outputData.insert(outputData.end(), p, p + sizeof(SKP_int16));
#endif

      /* Write payload */
      outputData.insert(outputData.end(), payload,
                        payload + sizeof(SKP_uint8) * nBytes);

      smplsSinceLastPacket = 0;
    }
  }

  /* Write dummy because it can not end with 0 bytes */
  nBytes = -1;

  /* Write payload size*/
  if (!tencent) {
    unsigned char *p = (unsigned char *)&nBytes;
    outputData.insert(outputData.end(), p, p + sizeof(SKP_int16));
  }

  /* Free Encoder */
  free(psEnc);

  Py_END_ALLOW_THREADS;
  return Py_BuildValue("y#", outputData.data(), outputData.size());

failed:
  if (psEnc)
    free(psEnc);
  PyErr_SetString(
      PyErr_NewException("graiax.silkcoder.codec.error", NULL, NULL),
      "encoder error");
  return 0;
}

static PyObject *decode_silk1(PyObject *self, PyObject *args) {
  SKP_uint8
      payload[MAX_BYTES_PER_FRAME * MAX_INPUT_FRAMES * (MAX_LBRR_DELAY + 1)];
  SKP_uint8 *payloadEnd = NULL, *payloadToDec = NULL;
  SKP_int16 nBytesPerPacket[MAX_LBRR_DELAY + 1];
  SKP_int16 out[((FRAME_LENGTH_MS * MAX_API_FS_KHZ) << 1) * MAX_INPUT_FRAMES],
      *outPtr;
  SKP_int32 remainPackets = 0;
  SKP_int16 len, nBytes, totalLen = 0;
  SKP_int32 decSizeBytes, result, silkDataSize;
  unsigned char *silkData;
  std::vector<unsigned char> outputData;

  if (!PyArg_ParseTuple(args, "s#", &silkData, &silkDataSize))
    return NULL;

  unsigned char *psRead = silkData;
  void *psDec = NULL;

  SKP_SILK_SDK_DecControlStruct DecControl;

  /* Check Silk header */
  if (strncmp((char *)psRead, "#!SILK_V3", 9) == 0)
    psRead += 9;
  else if (strncmp((char *)psRead, "\x02#!SILK_V3", 10) == 0)
    psRead += 10;
  else
    goto failed;

  /* Create decoder */
  result = SKP_Silk_SDK_Get_Decoder_Size(&decSizeBytes);
  if (result)
    goto failed;

  /* Reset decoder */
  psDec = malloc(decSizeBytes);
  result = SKP_Silk_SDK_InitDecoder(psDec);
  if (result)
    goto failed;

  payloadEnd = payload;
  DecControl.framesPerPacket = 1;
  DecControl.API_sampleRate = 24000;

  /* Simulate the jitter buffer holding MAX_FEC_DELAY packets */
  for (int i = 0; i < MAX_LBRR_DELAY; i++) {

    /* Read payload size */
    nBytes = *(SKP_int16 *)psRead;
    psRead += sizeof(SKP_int16);

#ifdef _SYSTEM_IS_BIG_ENDIAN
    swap_endian(&nBytes, 1);
#endif

    /* Read payload */
    memcpy(payloadEnd, (SKP_uint8 *)psRead, nBytes);
    psRead += sizeof(SKP_uint8) * nBytes;

    nBytesPerPacket[i] = nBytes;
    payloadEnd += nBytes;
  }

  nBytesPerPacket[MAX_LBRR_DELAY] = 0;

  Py_BEGIN_ALLOW_THREADS;

  while (1) {

    if (remainPackets == 0) {

      /* Read payload size */
      nBytes = *(SKP_int16 *)psRead;
      psRead += sizeof(SKP_int16);

#ifdef _SYSTEM_IS_BIG_ENDIAN
      swap_endian(&nBytes, 1);
#endif

      if (nBytes < 0 || psRead - silkData >= silkDataSize) {
        remainPackets = MAX_LBRR_DELAY;
        goto decode;
      }

      /* Read payload */
      memcpy(payloadEnd, (SKP_uint8 *)psRead, nBytes);
      psRead += sizeof(SKP_uint8) * nBytes;

    } else if (--remainPackets <= 0)
      break;

  decode:
    if (nBytesPerPacket[0] != 0) {
      nBytes = nBytesPerPacket[0];
      payloadToDec = payload;
    }

    outPtr = out;
    totalLen = 0;
    int frames = 0;

    /* Decode all frames in the packet */
    do {
      /* Decode 20 ms */
      SKP_Silk_SDK_Decode(psDec, &DecControl, 0, payloadToDec, nBytes, outPtr,
                          &len);

      frames++;
      outPtr += len;
      totalLen += len;

      if (frames > MAX_INPUT_FRAMES) {
        /* Hack for corrupt stream that could generate too many frames */
        outPtr = out;
        totalLen = 0;
        frames = 0;
      }

      /* Until last 20 ms frame of packet has been decoded */
    } while (DecControl.moreInternalDecoderFrames);

    /* Write output to file */
#ifdef _SYSTEM_IS_BIG_ENDIAN
    swap_endian(out, totalLen);
#endif

    outputData.insert(outputData.end(), (unsigned char *)out,
                      (unsigned char *)out + sizeof(SKP_int16) * totalLen);

    /* Update buffer */
    SKP_int16 totBytes = 0;
    for (int i = 0; i < MAX_LBRR_DELAY; i++) {
      totBytes += nBytesPerPacket[i + 1];
    }

    /* Check if the received totBytes is valid */
    if (totBytes < 0 || totBytes > sizeof(payload))
      goto failed;

    SKP_memmove(payload, &payload[nBytesPerPacket[0]],
                totBytes * sizeof(SKP_uint8));
    payloadEnd -= nBytesPerPacket[0];
    SKP_memmove(nBytesPerPacket, &nBytesPerPacket[1],
                MAX_LBRR_DELAY * sizeof(SKP_int16));
  }

  free(psDec);

  Py_END_ALLOW_THREADS;

  return Py_BuildValue("y#", (char *)outputData.data(), outputData.size());

failed:
  if (psDec)
    free(psDec);
  PyErr_SetString(
      PyErr_NewException("graiax.silkcoder.codec.error", NULL, NULL),
      "decoder error");
  return 0;
}

static PyObject *decode_silk(PyObject *self, PyObject *args)
// int main( int argc, char* argv[] )
{
  size_t counter;
  SKP_int32 i, k;
  SKP_int16 ret, len, tot_len;
  SKP_int16 nBytes;
  SKP_uint8
      payload[MAX_BYTES_PER_FRAME * MAX_INPUT_FRAMES * (MAX_LBRR_DELAY + 1)];
  SKP_uint8 *payloadEnd = NULL, *payloadToDec = NULL;
  SKP_uint8 FECpayload[MAX_BYTES_PER_FRAME * MAX_INPUT_FRAMES], *payloadPtr;
  SKP_int16 nBytesFEC;
  SKP_int16 nBytesPerPacket[MAX_LBRR_DELAY + 1], totBytes;
  SKP_int16 out[((FRAME_LENGTH_MS * MAX_API_FS_KHZ) << 1) * MAX_INPUT_FRAMES],
      *outPtr;
  SKP_int32 packetSize_ms = 0, API_Fs_Hz = 0;
  SKP_int32 decSizeBytes;
  void *psDec;
  SKP_float loss_prob;
  SKP_int32 frames, lost;
  SKP_SILK_SDK_DecControlStruct DecControl;

  /* default settings */
  loss_prob = 0.0f;

  /* get arguments */
  unsigned char *silkData;
  SKP_int32 silkDataSize;
  std::vector<unsigned char> outputData;
  if (!PyArg_ParseTuple(args, "y#", &silkData, &silkDataSize))
    return NULL;

  unsigned char *psRead = silkData;

  Py_BEGIN_ALLOW_THREADS;

  /* Check Silk header */
  if (strncmp((char *)psRead, "#!SILK_V3", 9) == 0)
    psRead += 9;
  else if (strncmp((char *)psRead, "\x02#!SILK_V3", 10) == 0)
    psRead += 10;
  else
    goto failed;

  /* Set the samplingrate that is requested for the output */
  if (API_Fs_Hz == 0) {
    DecControl.API_sampleRate = 24000;
  } else {
    DecControl.API_sampleRate = API_Fs_Hz;
  }

  /* Initialize to one frame per packet, for proper concealment before first
   * packet arrives */
  DecControl.framesPerPacket = 1;

  /* Create decoder */
  ret = SKP_Silk_SDK_Get_Decoder_Size(&decSizeBytes);
  if (ret)
    goto failed;
  psDec = malloc(decSizeBytes);

  /* Reset decoder */
  ret = SKP_Silk_SDK_InitDecoder(psDec);
  if (ret)
    goto failed;

  payloadEnd = payload;

  /* Simulate the jitter buffer holding MAX_FEC_DELAY packets */
  for (i = 0; i < MAX_LBRR_DELAY; i++) {
    /* Read payload size */
    nBytes = *(SKP_int16 *)psRead;
    psRead += sizeof(SKP_int16);

#ifdef _SYSTEM_IS_BIG_ENDIAN
    swap_endian(&nBytes, 1);
#endif
    /* Read payload */
    memcpy(payloadEnd, (SKP_uint8 *)psRead, nBytes);
    psRead += sizeof(SKP_uint8) * nBytes;

    if ((SKP_int16)counter < nBytes)
      break;

    nBytesPerPacket[i] = nBytes;
    payloadEnd += nBytes;
  }

  while (1) {
    if (psRead - silkData >= silkDataSize)
      break;

    /* Read payload size */
    nBytes = *(SKP_int16 *)psRead;
    psRead += sizeof(SKP_int16);
#ifdef _SYSTEM_IS_BIG_ENDIAN
    swap_endian(&nBytes, 1);
#endif
    if (nBytes < 0)
      break;

    /* Read payload */
    if (silkDataSize - (psRead - silkData) < (int)nBytes)
      break;
    memcpy(payloadEnd, (SKP_uint8 *)psRead, nBytes);
    psRead += sizeof(SKP_uint8) * nBytes;

    /* Simulate losses */
    rand_seed = SKP_RAND(rand_seed);
    if ((((float)((rand_seed >> 16) + (1 << 15))) / 65535.0f >=
         (loss_prob / 100.0f)) &&
        (counter > 0)) {
      nBytesPerPacket[MAX_LBRR_DELAY] = nBytes;
      payloadEnd += nBytes;
    } else {
      nBytesPerPacket[MAX_LBRR_DELAY] = 0;
    }

    if (nBytesPerPacket[0] == 0) {
      /* Indicate lost packet */
      lost = 1;

      /* Packet loss. Search after FEC in next packets. Should be done in the
       * jitter buffer */
      payloadPtr = payload;
      for (i = 0; i < MAX_LBRR_DELAY; i++) {
        if (nBytesPerPacket[i + 1] > 0) {
          SKP_Silk_SDK_search_for_LBRR(payloadPtr, nBytesPerPacket[i + 1],
                                       (i + 1), FECpayload, &nBytesFEC);
          if (nBytesFEC > 0) {
            payloadToDec = FECpayload;
            nBytes = nBytesFEC;
            lost = 0;
            break;
          }
        }
        payloadPtr += nBytesPerPacket[i + 1];
      }
    } else {
      lost = 0;
      nBytes = nBytesPerPacket[0];
      payloadToDec = payload;
    }

    /* Silk decoder */
    outPtr = out;
    tot_len = 0;

    if (lost == 0) {
      /* No Loss: Decode all frames in the packet */
      frames = 0;
      do {
        /* Decode 20 ms */
        ret = SKP_Silk_SDK_Decode(psDec, &DecControl, 0, payloadToDec, nBytes,
                                  outPtr, &len);
        if (ret) {
          printf("\nSKP_Silk_SDK_Decode returned %d", ret);
        }

        frames++;
        outPtr += len;
        tot_len += len;
        if (frames > MAX_INPUT_FRAMES) {
          /* Hack for corrupt stream that could generate too many frames */
          outPtr = out;
          tot_len = 0;
          frames = 0;
        }
        /* Until last 20 ms frame of packet has been decoded */
      } while (DecControl.moreInternalDecoderFrames);
    } else {
      /* Loss: Decode enough frames to cover one packet duration */
      for (i = 0; i < DecControl.framesPerPacket; i++) {
        /* Generate 20 ms */
        ret = SKP_Silk_SDK_Decode(psDec, &DecControl, 1, payloadToDec, nBytes,
                                  outPtr, &len);
        if (ret) {
          printf("\nSKP_Silk_Decode returned %d", ret);
        }
        outPtr += len;
        tot_len += len;
      }
    }

    packetSize_ms = tot_len / (DecControl.API_sampleRate / 1000);

    /* Write output to file */
#ifdef _SYSTEM_IS_BIG_ENDIAN
    swap_endian(out, tot_len);
#endif

    unsigned char *p = (unsigned char *)out;
    outputData.insert(outputData.end(), p, p + sizeof(SKP_int16) * tot_len);

    /* Update buffer */
    totBytes = 0;
    for (i = 0; i < MAX_LBRR_DELAY; i++) {
      totBytes += nBytesPerPacket[i + 1];
    }
    /* Check if the received totBytes is valid */
    if (totBytes < 0 || totBytes > sizeof(payload))
      goto failed;
    SKP_memmove(payload, &payload[nBytesPerPacket[0]],
                totBytes * sizeof(SKP_uint8));
    payloadEnd -= nBytesPerPacket[0];
    SKP_memmove(nBytesPerPacket, &nBytesPerPacket[1],
                MAX_LBRR_DELAY * sizeof(SKP_int16));
  }

  /* Empty the recieve buffer */
  for (k = 0; k < MAX_LBRR_DELAY; k++) {
    if (nBytesPerPacket[0] == 0) {
      /* Indicate lost packet */
      lost = 1;

      /* Packet loss. Search after FEC in next packets. Should be done in the
       * jitter buffer */
      payloadPtr = payload;
      for (i = 0; i < MAX_LBRR_DELAY; i++) {
        if (nBytesPerPacket[i + 1] > 0) {
          SKP_Silk_SDK_search_for_LBRR(payloadPtr, nBytesPerPacket[i + 1],
                                       (i + 1), FECpayload, &nBytesFEC);
          if (nBytesFEC > 0) {
            payloadToDec = FECpayload;
            nBytes = nBytesFEC;
            lost = 0;
            break;
          }
        }
        payloadPtr += nBytesPerPacket[i + 1];
      }
    } else {
      lost = 0;
      nBytes = nBytesPerPacket[0];
      payloadToDec = payload;
    }

    /* Silk decoder */
    outPtr = out;
    tot_len = 0;

    if (lost == 0) {
      /* No loss: Decode all frames in the packet */
      frames = 0;
      do {
        /* Decode 20 ms */
        ret = SKP_Silk_SDK_Decode(psDec, &DecControl, 0, payloadToDec, nBytes,
                                  outPtr, &len);
        if (ret) {
          printf("\nSKP_Silk_SDK_Decode returned %d", ret);
        }

        frames++;
        outPtr += len;
        tot_len += len;
        if (frames > MAX_INPUT_FRAMES) {
          /* Hack for corrupt stream that could generate too many frames */
          outPtr = out;
          tot_len = 0;
          frames = 0;
        }
        /* Until last 20 ms frame of packet has been decoded */
      } while (DecControl.moreInternalDecoderFrames);
    } else {
      /* Loss: Decode enough frames to cover one packet duration */

      /* Generate 20 ms */
      for (i = 0; i < DecControl.framesPerPacket; i++) {
        ret = SKP_Silk_SDK_Decode(psDec, &DecControl, 1, payloadToDec, nBytes,
                                  outPtr, &len);
        if (ret)
          goto failed;
        outPtr += len;
        tot_len += len;
      }
    }

    packetSize_ms = tot_len / (DecControl.API_sampleRate / 1000);

    /* Write output to file */
#ifdef _SYSTEM_IS_BIG_ENDIAN
    swap_endian(out, tot_len);
#endif
    unsigned char *p = (unsigned char *)out;
    outputData.insert(outputData.end(), p, p + sizeof(SKP_int16) * tot_len);

    /* Update Buffer */
    totBytes = 0;
    for (i = 0; i < MAX_LBRR_DELAY; i++) {
      totBytes += nBytesPerPacket[i + 1];
    }

    /* Check if the received totBytes is valid */
    if (totBytes < 0 || totBytes > sizeof(payload))
      goto failed;

    SKP_memmove(payload, &payload[nBytesPerPacket[0]],
                totBytes * sizeof(SKP_uint8));
    payloadEnd -= nBytesPerPacket[0];
    SKP_memmove(nBytesPerPacket, &nBytesPerPacket[1],
                MAX_LBRR_DELAY * sizeof(SKP_int16));
  }

  /* Free decoder */
  free(psDec);

  Py_END_ALLOW_THREADS;
  return Py_BuildValue("y#", outputData.data(), outputData.size());

failed:
  if (psDec)
    free(psDec);
  PyErr_SetString(
      PyErr_NewException("graiax.silkcoder.codec.error", NULL, NULL),
      "decoder error");
  return 0;
}

static PyMethodDef SilkMethods[] = {
    {"decode", decode_silk, METH_VARARGS, "Decode a silk file to pcm file."},
    {"encode", encode_silk, METH_VARARGS, "Encode a pcm file to silk file."},
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

/***********************************************************************
Copyright (c) 2006-2012, Skype Limited. All rights reserved.
Redistribution and use in source and binary forms, with or without
modification, (subject to the limitations in the disclaimer below)
are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.
- Neither the name of Skype Limited, nor the names of specific
contributors, may be used to endorse or promote products derived from
this software without specific prior written permission.
NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED
BY THIS LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS ''AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTI_SYSTEM_IS_BIG_ENDIANES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
***********************************************************************/