from io import BytesIO
from typing import Dict, Optional, BinaryIO
from os import PathLike
from .utils import sync_to_async
from .silkv3 import SilkEncoder, SilkDecoder

try:
    import soundfile
    import soxr
    import numpy as np
except (ImportError, OSError):
    soundfile = None
    soxr = None

if soundfile is not None and soxr is not None:

    class SoundFileReadBytes(soundfile.SoundFile):

        def __init__(self, *args, resamplerate=24000, **kwargs):
            super().__init__(*args, **kwargs)
            if self.samplerate != resamplerate:
                self.resampler = soxr.ResampleStream(self.samplerate, resamplerate, 1)
            else:
                self.resampler = None

            self.resample_data = bytearray()
            self.resample_len = 0
            self.start = 0

        def add_resample(self):
            data = super().read(self.samplerate, 'float32')
            if self.channels != 1:
                data = data.mean(axis=1)
            if len(data) == 0:
                return False
            if self.resampler is not None:
                is_last = (self.tell() == self.frames)
                data = self.resampler.resample_chunk(data, last=is_last)

            data_int16 = (data * 32767).clip(-32767, 32767).astype('<i2')
            chunk_bytes = data_int16.tobytes()

            self.resample_data.extend(chunk_bytes)
            self.resample_len += len(chunk_bytes)

            return True

        def read(self, frames: int = -1):
            if frames == -1:

                while self.add_resample():
                    pass
                data = bytes(self.resample_data[self.start:])
                self.start = len(self.resample_data)
                self.resample_len = 0
                return data

            while frames > self.resample_len:
                if not self.add_resample():
                    break

            available = min(frames, self.resample_len)
            data = bytes(self.resample_data[self.start:self.start + available])
            self.start += available
            self.resample_len -= available

            # 定期清理已读数据（例如超过4KB时压缩）
            if self.start > 4096:
                del self.resample_data[:self.start]
                self.start = 0

            return data


def sndfile_encode(input_bytes: bytes,
                   output_samplerate: int = 24000,
                   tencent: bool = True,
                   ios_adaptive: bool = True):
    input_stream = BytesIO(input_bytes)
    output_stream = BytesIO()
    sndfile_encode_stream(input_stream, output_stream, output_samplerate, tencent,
                          ios_adaptive)
    return output_stream.getvalue()


def sndfile_encode_stream(input_file,
                          output_stream=None,
                          output_samplerate: int = 24000,
                          tencent: bool = True,
                          ios_adaptive: bool = True):
    if soundfile is None or soxr is None:
        raise ImportError("Do not have soundfile")
    stream_iter = sndfile_encode_stream_iter(input_file, output_samplerate, tencent,
                                             ios_adaptive)
    if output_stream is None:
        return stream_iter
    else:
        for chunk in stream_iter:
            output_stream.write(chunk)


def sndfile_encode_stream_iter(input_file,
                               output_samplerate: int = 24000,
                               tencent: bool = True,
                               ios_adaptive: bool = True):
    if soundfile is None or soxr is None:
        raise ImportError("Do not have soundfile")

    with (SoundFileReadBytes(input_file, 'r') as f,
          SilkEncoder(output_samplerate,
                      output_samplerate,
                      100000,
                      tencent=tencent,
                      ios_adaptive=ios_adaptive) as encoder):

        yield from encoder.encode_stream(f)


def sndfile_decode(input_bytes: bytes,
                   audio_format: str,
                   subtype: Optional[str] = None,
                   compression_level: Optional[float] = None,
                   metadata: Optional[Dict[str, str]] = None,
                   **kwargs):
    input_stream = BytesIO(input_bytes)
    output_stream = BytesIO()
    sndfile_decode_stream(input_stream,
                          audio_format=audio_format,
                          subtype=subtype,
                          metadata=metadata,
                          compression_level=compression_level,
                          **kwargs)
    return output_stream.getvalue()


def sndfile_decode_stream(input_stream,
                          audio_format: str,
                          output_stream: BinaryIO | PathLike | None = None,
                          output_samplerate: int = 24000,
                          subtype: Optional[str] = None,
                          compression_level: Optional[float] = None,
                          metadata: Optional[Dict[str, str]] = None,
                          **kwargs):
    if soundfile is None or soxr is None:
        raise ImportError("Do not have soundfile")
    if output_stream is None:
        output_stream = BytesIO()
    with (soundfile.SoundFile(output_stream,
                              "w",
                              samplerate=output_samplerate,
                              channels=1,
                              format=audio_format,
                              subtype=subtype,
                              compression_level=compression_level,
                              **kwargs) as f, SilkDecoder(24000) as decoder):
        if metadata:
            for k, v in metadata.items():
                setattr(f, k, v)
        for chunk in decoder.decode_stream_iter(input_stream):
            chunk = np.frombuffer(chunk, np.int16)
            f.write(chunk)


async_sndfile_encode = sync_to_async(sndfile_encode)
async_sndfile_decode = sync_to_async(sndfile_decode)
async_sndfile_encode_stream = sync_to_async(sndfile_encode_stream)
async_sndfile_decode_stream = sync_to_async(sndfile_decode_stream)
