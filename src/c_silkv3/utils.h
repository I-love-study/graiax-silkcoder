#ifndef _UTILS_H_
#define _UTILS_H_

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  unsigned char *buffer;
  size_t size;
  size_t capacity;
  size_t init_capacity;
} DataStream;

void initializeDataStream(DataStream *stream, size_t initialCapacity);
void writeDataToStream(DataStream *stream, unsigned char *data, size_t dataSize);
void freeDataStream(DataStream *stream);
void removeDataFromStream(DataStream *stream, size_t dataSize);
int findIndex(int targetNumber, int array[], int size);

#endif /* _STREAM_H_ */