#include "decoder.h"
#include "SKP_Silk_typedef.h"

PyObject *decode_silk(PyObject *self, PyObject *args, PyObject *keyword_args) {
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
  SKP_int32 remainPackets = 0;
  SKP_int32 decSizeBytes, result;
  SKP_uint8 *silkData;
  SKP_int32 silkDataSize;
  SKP_int32 API_sampleRate = 24000;
  SKP_int32 frames, lost;
  void *psDec;
  SKP_SILK_SDK_DecControlStruct DecControl;
  DataStream outputData;

  SKP_float loss_prob = 0.0f;

  static char *kwlist[] = {"silk_data", "output_samplerate", "packet_loss",
                           NULL};

  if (!PyArg_ParseTupleAndKeywords(args, keyword_args, "y#|if", kwlist,
                                   &silkData, &silkDataSize, &API_sampleRate,
                                   &loss_prob)) {
    return NULL;
  }

  SKP_uint8 *psRead = silkData;

  /* Check Silk header */
  if (strncmp((char *)psRead, "#!SILK_V3", 9) == 0)
    psRead += 9;
  else if ((psRead[0] == '\x00' || psRead[0] == '\x01' || psRead[0] == '\x02' ||
            psRead[0] == '\x03') &&
           strncmp((char *)psRead + 1, "#!SILK_V3", 9) == 0)
    psRead += 10;
  else {
    PyErr_Format(PyExc_ValueError, "input isn't silkv3");
    return NULL;
  }

  /* Set the samplingrate that is requested for the output */
  DecControl.API_sampleRate = API_sampleRate;
  /* Initialize to one frame per packet, for proper concealment before first
   * packet arrives */
  DecControl.framesPerPacket = 1;

  initializeDataStream(&outputData,
                       ((FRAME_LENGTH_MS * API_sampleRate) << 1) * 1000 / 20);

  Py_BEGIN_ALLOW_THREADS;

  /* Create decoder */
  ret = SKP_Silk_SDK_Get_Decoder_Size(&decSizeBytes);
  psDec = malloc(decSizeBytes);

  /* Reset decoder */
  ret = SKP_Silk_SDK_InitDecoder(psDec);

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

    if (silkDataSize - (psRead - silkData) < (int)nBytes)
      break;
    memcpy(payloadEnd, psRead, nBytes);
    psRead += nBytes;

    nBytesPerPacket[i] = nBytes;
    payloadEnd += nBytes;
  }

  while (1) {
    /* Read payload size */
    if (psRead - silkData >= silkDataSize)
      break;
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
          PyErr_Format(PyExc_RuntimeError, "Decode failed");
          return NULL;
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
          PyErr_Format(PyExc_RuntimeError, "Decode failed");
          return NULL;
        }
        outPtr += len;
        tot_len += len;
      }
    }

    /* Write output to file */
#ifdef _SYSTEM_IS_BIG_ENDIAN
    swap_endian(out, tot_len);
#endif
    writeDataToStream(&outputData, (unsigned char *)out, sizeof(SKP_int16) * tot_len);

    /* Update buffer */
    totBytes = 0;
    for (i = 0; i < MAX_LBRR_DELAY; i++) {
      totBytes += nBytesPerPacket[i + 1];
    }
    /* Check if the received totBytes is valid */
    if (totBytes < 0 || totBytes > sizeof(payload)) {
      PyErr_Format(PyExc_RuntimeError, "Decode failed");
      return NULL;
    }
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
          PyErr_Format(PyExc_RuntimeError, "Decode failed");
          return NULL;
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
        if (ret) {
          PyErr_Format(PyExc_RuntimeError, "Decode failed");
          return NULL;
        }
        outPtr += len;
        tot_len += len;
      }
    }

    /* Write output to file */
#ifdef _SYSTEM_IS_BIG_ENDIAN
    swap_endian(out, tot_len);
#endif
    writeDataToStream(&outputData, (unsigned char *)out, sizeof(SKP_int16) * tot_len);

    /* Update Buffer */
    totBytes = 0;
    for (i = 0; i < MAX_LBRR_DELAY; i++) {
      totBytes += nBytesPerPacket[i + 1];
    }

    /* Check if the received totBytes is valid */
    if (totBytes < 0 || totBytes > sizeof(payload)) {
      PyErr_Format(PyExc_RuntimeError, "Decode failed");
      return NULL;
    }

    SKP_memmove(payload, &payload[nBytesPerPacket[0]],
                totBytes * sizeof(SKP_uint8));
    payloadEnd -= nBytesPerPacket[0];
    SKP_memmove(nBytesPerPacket, &nBytesPerPacket[1],
                MAX_LBRR_DELAY * sizeof(SKP_int16));
  }

  /* Free decoder */
  free(psDec);
  Py_END_ALLOW_THREADS;
  return Py_BuildValue("y#", outputData.buffer, outputData.size);
};