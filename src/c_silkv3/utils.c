#include "utils.h"

void initializeDataStream(DataStream *stream, size_t initialCapacity) {
  stream->buffer = malloc(initialCapacity);
  if (stream->buffer == NULL) {
    perror("Error allocating memory");
    exit(EXIT_FAILURE);
  }

  stream->size = 0;
  stream->capacity = initialCapacity;
  stream->init_capacity = initialCapacity;
}

void writeDataToStream(DataStream *stream, unsigned char *data,
                       size_t dataSize) {
  if (stream->size + dataSize > stream->capacity) {
    while (stream->size + dataSize > stream->capacity) {
      stream->capacity += stream->init_capacity;
    }
    stream->buffer = realloc(stream->buffer, stream->capacity);
    if (stream->buffer == NULL) {
      perror("Error reallocating memory");
    }
  }

  memcpy(stream->buffer + stream->size, data, dataSize);
  stream->size += dataSize;
}

void removeDataFromStream(DataStream *stream, size_t dataSize) {
  stream->size -= dataSize;
  memset(stream->buffer + stream->size, '\0', dataSize);
}

void freeDataStream(DataStream *stream) {
  free(stream->buffer);
  stream->buffer = NULL;
  stream->size = 0;
  stream->capacity = 0;
}

int findIndex(int targetNumber, int array[], int size) {
  for (int i = 0; i < size; ++i) {
    if (array[i] == targetNumber) {
      return i;
    }
  }
  return -1;
}