import asyncio
from io import BytesIO
from os import PathLike
from typing import Dict, AsyncGenerator, overload, Coroutine, Any, Generator

from .silkv3 import SilkDecoder, SilkEncoder
from .utils import AsyncReader, async_func, is_async_reader, is_async_writer
from .typing import Reader, Writer, AsyncWriter

try:
    import numpy as np
    import soundfile
    import soxr
except (ImportError, OSError):
    soundfile = None
    soxr = None

if soundfile is not None and soxr is not None:

    class SoundFileReadBytes(soundfile.SoundFile):

        def __init__(self, *args, resamplerate=24000, **kwargs):
            if soundfile is None or soxr is None:
                raise ModuleNotFoundError("Do not have soundfile and soxr")
            super().__init__(*args, **kwargs)
            if self.samplerate != resamplerate:
                self.resampler = soxr.ResampleStream(self.samplerate, resamplerate, 1)
            else:
                self.resampler = None

            self.resample_data = bytearray()
            self.resample_len = 0
            self.start = 0

        def add_resample(self, read_size: int | None = None):
            data = super().read(read_size if read_size is not None else self.samplerate,
                                'float32')
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


# 对于 soundfile，仅支持 read 是不够的，还需要包括 seek 等方法
# 为了防止代码里面全是 type hint 工程，这里用 Reader 简化
# 详细请看 Soundfile._has_virtual_io_attrs
SndSupportedFileR = Reader[bytes] | PathLike | str | bytes | int
SndSupportedFileW = Writer[bytes] | PathLike | str | bytes | int


class SndfileEncoder:

    def __init__(self,
                 output_samplerate: int = 24000,
                 bitrate: int = 100000,
                 ss: float = 0,
                 t: float | None = None,
                 **kwargs):

        self.silk_encoder = SilkEncoder(input_samplerate=output_samplerate,
                                        output_samplerate=output_samplerate,
                                        bitrate=bitrate,
                                        **kwargs)
        self.samplerate = output_samplerate
        self.ss = ss
        self.t = t

    def encode(self, input_bytes: bytes):
        input_stream = BytesIO(input_bytes)
        output_stream = BytesIO()
        self.encode_stream(input_stream)
        return output_stream.getvalue()

    @overload
    def encode_stream(self,
                      input_file: SndSupportedFileR) -> Generator[bytes, None, None]:
        ...

    @overload
    def encode_stream(self, input_file: SndSupportedFileR,
                      output_stream: Writer[bytes]) -> None:
        ...

    def encode_stream(self,
                      input_file: SndSupportedFileR,
                      output_stream: Writer[bytes] | None = None
                      ) -> Generator[bytes, None, None] | None:
        stream_iter = self.encode_stream_iter(input_file)
        if output_stream is None:
            return stream_iter
        for chunk in stream_iter:
            output_stream.write(chunk)

    def encode_stream_iter(
            self, input_file: SndSupportedFileR) -> Generator[bytes, None, None]:
        if soundfile is None or soxr is None:
            raise ImportError("Do not have soundfile")

        with SoundFileReadBytes(input_file, 'r') as f, self.silk_encoder as encoder:
            if self.ss != 0 or self.t is not None:
                f._prepare_read(int(self.ss * f.samplerate), int(self.t * f.samplerate),
                                -1)
            if self.silk_encoder.auto_bitrate and self.silk_encoder.bitrate is None:
                self.silk_encoder.set_calc_max_bitrate(f.frames / f.samplerate)
            yield from encoder.encode_stream(f)

    @overload
    async def async_encode_stream(
            self, input_file: SndSupportedFileR) -> AsyncGenerator[bytes, None]:
        ...

    @overload
    async def async_encode_stream(
            self, input_file: SndSupportedFileR,
            output_stream: Writer[bytes] | AsyncWriter[bytes]) -> None:
        ...

    def async_encode_stream(
        self,
        input_file: SndSupportedFileR,
        output_stream: Writer[bytes] | AsyncWriter[bytes] | None = None
    ) -> AsyncGenerator[bytes, None] | Coroutine[Any, Any, None]:

        if output_stream is None:
            return self.async_encode_stream_iter(input_file)
        elif not is_async_writer(output_stream):
            return asyncio.to_thread(self.encode_stream, input_file, output_stream)

        async def _coro():
            async for chunk in self.async_encode_stream_iter(input_file):
                await async_func(output_stream.write, chunk)

        return _coro()

    async def async_encode_stream_iter(self, input_file: SndSupportedFileR):
        if soundfile is None or soxr is None:
            raise ImportError("Do not have soundfile")

        with SoundFileReadBytes(input_file, 'r') as f, self.silk_encoder as encoder:
            if self.silk_encoder.auto_bitrate and self.silk_encoder.bitrate is None:
                self.silk_encoder.set_calc_max_bitrate(f.frames / f.samplerate)
            async for chunk in encoder.async_encode_stream(f):
                yield chunk


class SndfileDecode:

    def __init__(self,
                 audio_format: str | None = None,
                 output_samplerate: int = 24000,
                 subtype: str | None = None,
                 compression_level: float | None = None,
                 metadata: Dict[str, str] | None = None,
                 **kwargs: dict[str, Any]) -> None:

        self.soundfile_kwargs: dict[str,
                                    Any] = dict(samplerate=output_samplerate,
                                                format=audio_format,
                                                subtype=subtype,
                                                compression_level=compression_level,
                                                **kwargs)
        self.metadata = metadata
        self.silk_decoder = SilkDecoder(output_samplerate)
        pass

    def decode(self, input_bytes):
        input_stream = BytesIO(input_bytes)
        output_stream = BytesIO()
        self.decode_stream(input_stream, output_stream)
        return output_stream.getvalue()

    def decode_stream(self, input_stream: Reader[bytes],
                      output_file: SndSupportedFileW):
        if soundfile is None or soxr is None:
            raise ImportError("Do not have soundfile")

        with (soundfile.SoundFile(output_file, "w", channels=1, **self.soundfile_kwargs)
              as f, self.silk_decoder as decoder):

            if self.metadata is not None:
                for k, v in self.metadata.items():
                    setattr(f, k, v)

            for chunk in decoder.decode_stream_iter(input_stream):
                f.write(np.frombuffer(chunk, dtype=np.int16))

    async def async_decode(self, input_bytes: bytes):
        input_stream = BytesIO(input_bytes)
        output_stream = BytesIO()
        await asyncio.to_thread(self.decode_stream, input_stream, output_stream)
        return output_stream.getvalue()

    def async_decode_stream(self, input_stream: Reader[bytes] | AsyncReader[bytes],
                            output_file: SndSupportedFileW):
        if soundfile is None or soxr is None:
            raise ImportError("Do not have soundfile")

        if asyncio.iscoroutinefunction(getattr(output_file, "read", None)):
            raise TypeError("'output_file' is not support AsyncWriter, "
                            "Please use Writer instead.")
        elif not is_async_reader(input_stream):
            return asyncio.to_thread(self.decode_stream, input_stream, output_file)

        async def _coro():
            assert soundfile is not None
            with (soundfile.SoundFile(output_file,
                                      "w",
                                      channels=1,
                                      **self.soundfile_kwargs) as f, self.silk_decoder
                  as decoder):

                if self.metadata is not None:
                    for k, v in self.metadata.items():
                        setattr(f, k, v)

                async for chunk in decoder.async_decode_stream_iter(input_stream):
                    f.write(np.frombuffer(chunk, dtype=np.int16))

        return _coro
