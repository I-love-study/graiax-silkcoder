#include "encoder.h"
#include "SKP_Silk_typedef.h"

PyObject *encode_silk(PyObject *self, PyObject *args, PyObject *keyword_args) {
  size_t counter;
  SKP_int16 nBytes;
  SKP_uint8 payload[MAX_BYTES_PER_FRAME * MAX_INPUT_FRAMES];
  SKP_int16 in[FRAME_LENGTH_MS * MAX_API_FS_KHZ * MAX_INPUT_FRAMES];
  SKP_int32 encSizeBytes, ret, pcmDataSize, tencent;
  void *psEnc = NULL;
  unsigned char *pcmData;
  DataStream outputData;

  // temp
  int index;

#ifdef _SYSTEM_IS_BIG_ENDIAN
  SKP_int16 nBytes_LE;
#endif

  /* default settings */
  SKP_int32 smplsSinceLastPacket = 0, packetSize_ms = 20;
  SKP_int32 packetLoss_perc = 0;
  SKP_int32 complexity_mode = 2;
  SKP_int32 DTX_enabled = 0, INBandFEC_enabled = 0;
  SKP_SILK_SDK_EncControlStruct encControl; // Struct for input to encoder
  SKP_SILK_SDK_EncControlStruct encStatus;  // Struct for status of encoder

  SKP_int32 API_fs_Hz;
  SKP_int32 max_internal_fs_Hz;
  SKP_int32 targetRate_bps;

  static char *kwlist[] = {"pcm_data",
                           "input_samplerate",
                           "maximum_samplerate",
                           "bitrate",
                           "tencent",
                           "complexity",
                           "packet_size",
                           "packet_loss",
                           "use_in_band_fec",
                           "use_dtx",
                           NULL};

  /* Get input data */
  if (!PyArg_ParseTupleAndKeywords(
          args, keyword_args, "y#iiip|iiipp", kwlist, &pcmData, &pcmDataSize,
          &API_fs_Hz, &max_internal_fs_Hz, &targetRate_bps, &tencent,
          &complexity_mode, &packetSize_ms, &packetLoss_perc,
          &INBandFEC_enabled, &DTX_enabled))
    return NULL;
  unsigned char *psRead = pcmData, *psReadEnd = pcmData + pcmDataSize;

  if (API_fs_Hz > MAX_API_FS_KHZ * 1000 || API_fs_Hz < 0)
    goto failed;

  initializeDataStream(&outputData, ENCODE_MAX_BYTES_PER_FRAME *
                                        MAX_INPUT_FRAMES * 1000 /
                                        packetSize_ms);

  int input_samplerate_support[] = {8000,  12000, 16000, 24000,
                                    32000, 44100, 48000};
  int maximum_samplerate_support[] = {8000, 12000, 16000, 24000};
  int packet_size_support[] = {20, 40, 60, 80, 100};

  // Args checking
  if (targetRate_bps < 5000) {
    targetRate_bps = 5000;
  } else if (targetRate_bps > 100000) {
    targetRate_bps = 100000;
  }

  if (0 > complexity_mode || complexity_mode > 2) {
    PyErr_Format(PyExc_ValueError, "complexity should in [0, 1, 2]");
    return NULL;
  }

  if (0 > packetLoss_perc || packetLoss_perc > 100) {
    PyErr_Format(PyExc_ValueError, "packet_loss should in 0 ~ 100");
    return NULL;
  }

  if (findIndex(packetSize_ms, packet_size_support, 5) == -1) {
    PyErr_Format(PyExc_ValueError,
                 "packet_size should in [20, 40, 60, 80, 100]");
    return NULL;
  }

  if (findIndex(API_fs_Hz, input_samplerate_support, 7) == -1) {
    PyErr_Format(PyExc_ValueError, "input_samplerate should in [8000, 12000, "
                                   "16000, 24000, 32000, 44100, 48000]");
    return NULL;
  };

  index = findIndex(max_internal_fs_Hz, maximum_samplerate_support, 4);
  if (index == -1) {
    PyErr_Format(PyExc_ValueError,
                 "maximum_samplerate should in [8000, 12000, 16000, 24000]");
    return NULL;
  };
  if (tencent) {
    writeDataToStream(&outputData, (unsigned char *)&index, 1);
  }

  writeDataToStream(&outputData, (unsigned char *)"#!SILK_V3", 9);

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

  Py_BEGIN_ALLOW_THREADS;

  counter = (packetSize_ms * API_fs_Hz) / 1000;
  size_t realrd;
  while (1) {
    /* Read input from file */
    if (psRead - pcmData >= pcmDataSize)
      break;

    if (counter * sizeof(SKP_int16) > psReadEnd - psRead) {
      memset(in, 0x00, sizeof(in));
      realrd = (psReadEnd - psRead);
    } else {
      realrd = counter * sizeof(SKP_int16);
    }
    memcpy(in, psRead, realrd);
    psRead += realrd;

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
      writeDataToStream(&outputData, (unsigned char *)&nBytes_LE,
                        sizeof(SKP_int16));
#else
      writeDataToStream(&outputData, (unsigned char *)&nBytes,
                        sizeof(SKP_int16));
#endif

      /* Write payload */
      writeDataToStream(&outputData, payload, sizeof(SKP_uint8) * nBytes);

      smplsSinceLastPacket = 0;
    }
  }

  nBytes = -1;

  /* Write payload size*/
  if (!tencent) {
    writeDataToStream(&outputData, (void *)&nBytes, sizeof(SKP_int16));
  } else {
    /*https://github.com/I-love-study/graiax-silkcoder/issues/32 mention @lclichen*/
    removeDataFromStream(&outputData, 1L);
  }

  free(psEnc);

  Py_END_ALLOW_THREADS;
  return Py_BuildValue("y#", outputData.buffer, outputData.size);

failed:
  if (psEnc)
    free(psEnc);
  return 0;
}