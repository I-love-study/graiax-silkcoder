import asyncio
import struct
from io import BytesIO
from math import floor
from typing import Any, AsyncGenerator, Generator, overload, Coroutine
from ._silkv3 import ffi, lib  # type: ignore
from .utils import async_func
from .typing import Reader, Writer, AsyncReader, AsyncWriter, DataBuffer

try:
    import numpy as np
except ImportError:
    np = None


class SilkError(Exception):

    def __init__(self, code):
        self.code = code

    def __str__(self):
        if isinstance(self.code, int):
            if self.code == -1:
                return "ENC_INPUT_INVALID_NO_OF_SAMPLES"
            elif self.code == -2:
                return "ENC_FS_NOT_SUPPORTED"
            elif self.code == -3:
                return "ENC_PACKET_SIZE_NOT_SUPPORTED"
            elif self.code == -4:
                return "ENC_PAYLOAD_BUF_TOO_SHORT"
            elif self.code == -5:
                return "ENC_INVALID_LOSS_RATE"
            elif self.code == -6:
                return "ENC_INVALID_COMPLEXITY_SETTING"
            elif self.code == -7:
                return "ENC_INVALID_INBAND_FEC_SETTING"
            elif self.code == -8:
                return "ENC_INVALID_DTX_SETTING"
            elif self.code == -9:
                return "ENC_INTERNAL_ERROR"
            elif self.code == -10:
                return "DEC_INVALID_SAMPLING_FREQUENCY"
            elif self.code == -11:
                return "DEC_PAYLOAD_TOO_LARGE"
            elif self.code == -12:
                return "DEC_PAYLOAD_ERROR"
            else:
                return "Other error"
        else:
            return str(self.code)


def i16_to_bytes(data: int) -> bytes:
    return struct.pack("=h", data)


def bytes_to_i16(data: bytes) -> int:
    return struct.unpack("=h", data)[0]


def from_i16_le(data: int):
    if lib.SHOULD_SWAP():
        data = lib.swap_i16(data)
    return i16_to_bytes(data)


def to_i16_le(input: bytes) -> int:
    chunk = input[:2]
    data: int = bytes_to_i16(chunk)
    if lib.SHOULD_SWAP():
        data = lib.swap_i16(data)
    return data


class SilkEncoder:

    def __init__(self,
                 input_samplerate: int,
                 output_samplerate: int,
                 bitrate: int | None = None,
                 packet_loss_percentage: int = 0,
                 complexity: int = 2,
                 use_inband_fec: bool = False,
                 use_dtx: bool = False,
                 tencent: bool = True,
                 ios_adaptive: bool = True,
                 auto_bitrate: bool = True):

        self.ios_adaptve = ios_adaptive
        self.auto_bitrate = auto_bitrate
        self.bitrate = bitrate
        self.enc_control = ffi.new("SKP_SILK_SDK_EncControlStruct *")
        self.enc_control.API_sampleRate = input_samplerate
        self.enc_control.maxInternalSampleRate = output_samplerate
        self.enc_control.packetSize = (20 * input_samplerate) // 1000
        self.enc_control.packetLossPercentage = packet_loss_percentage
        self.enc_control.complexity = complexity
        self.enc_control.useInBandFEC = use_inband_fec
        self.enc_control.useDTX = use_dtx
        if bitrate is None:
            self.enc_control.bitRate = 24000 if self.ios_adaptve else 100000
        else:
            self.enc_control.bitRate = bitrate

        self.enc_status = ffi.new("SKP_SILK_SDK_EncControlStruct *")
        self.enc_status.API_sampleRate = 0
        self.enc_status.maxInternalSampleRate = 0
        self.enc_status.packetSize = 0
        self.enc_status.bitRate = 0
        self.enc_status.packetLossPercentage = 0
        self.enc_status.complexity = 0
        self.enc_status.useInBandFEC = 0
        self.enc_status.useDTX = 0

        self.tencent = tencent
        self.frame_size = input_samplerate // 1000 * 40

    def __enter__(self):
        enc_size_bytes = ffi.new("int32_t *", 0)
        code = lib.SKP_Silk_SDK_Get_Encoder_Size(enc_size_bytes)
        if code != 0:
            raise SilkError(code)
        self.enc = lib.PyMem_Malloc(enc_size_bytes[0])
        if self.enc == ffi.NULL:
            raise MemoryError
        code = lib.SKP_Silk_SDK_InitEncoder(self.enc, self.enc_status)
        if code != 0:
            raise SilkError(code)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if getattr(self, "enc", None) is not None:
            lib.PyMem_Free(self.enc)

    async def __aenter__(self):
        await asyncio.to_thread(self.__enter__)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.to_thread(self.__exit__, exc_type, exc_val, exc_tb)

    def set_calc_max_bitrate(self, seconds: float):
        maximum_bps = 24000 if self.ios_adaptve else 100000
        self.enc_control.bitRate = min(floor(980 * 1024 / seconds / 8), maximum_bps)

    def set_calc_max_bitrate_from_bytes(self, input_bytes: bytes):
        return self.set_calc_max_bitrate(len(input_bytes) / 24000 / 2)

    def encode(self, input_bytes: bytes):
        if self.auto_bitrate and self.bitrate is None:
            self.set_calc_max_bitrate_from_bytes(input_bytes)
        input_stream = BytesIO(input_bytes)
        output_stream = BytesIO()
        self.encode_stream(input_stream, output_stream)
        return output_stream.getvalue()

    async def async_encode(self, input_bytes: bytes):
        input_stream = BytesIO(input_bytes)
        output_stream = BytesIO()
        await asyncio.to_thread(self.encode_stream, input_stream, output_stream)
        return output_stream.getvalue()

    @overload
    def encode_stream(self,
                      input_stream: Reader[DataBuffer]) -> Generator[bytes, None, None]:
        ...

    @overload
    def encode_stream(self, input_stream: Reader[DataBuffer],
                      output_stream: Writer[bytes]) -> None:
        ...

    def encode_stream(
        self,
        input_stream: Reader[DataBuffer],
        output_stream: Writer[bytes] | None = None
    ) -> Generator[bytes, None, None] | None:
        if output_stream is None:
            return self.encode_stream_iter(input_stream)

        for chunk in self.encode_stream_iter(input_stream):
            output_stream.write(chunk)

    def encode_stream_iter(
            self, input_stream: Reader[DataBuffer]) -> Generator[bytes, None, None]:
        # Header
        if self.tencent:
            yield b"\x02"

        yield b"#!SILK_V3"

        n_bytes = ffi.new("int16_t *", 1250)
        payload = ffi.new("uint8_t[1250]")
        while True:
            chunk = input_stream.read(self.frame_size)
            if np is not None and isinstance(chunk, np.ndarray):
                chunk = chunk.tobytes()
            if not isinstance(chunk, bytes):
                raise TypeError(
                    f"input must be a file-like rb object, got {type(input).__name__}")

            n_bytes[0] = 1250
            if len(chunk) < self.frame_size:
                break
            c_chunk = ffi.from_buffer("int16_t[]", chunk)
            encoded_bytes, payload_ = self._encode(c_chunk, chunk, payload, n_bytes)

            yield encoded_bytes
            yield payload_

    @overload
    async def async_encode_stream(
        self, input_stream: AsyncReader[DataBuffer] | Reader[DataBuffer]
    ) -> AsyncGenerator[bytes, None]:
        ...

    @overload
    async def async_encode_stream(
            self, input_stream: AsyncReader[DataBuffer] | Reader[DataBuffer],
            output_stream: AsyncWriter[bytes] | Writer[bytes]) -> None:
        ...

    def async_encode_stream(
        self,
        input_stream: AsyncReader[DataBuffer] | Reader[DataBuffer],
        output_stream: AsyncWriter[bytes] | Writer[bytes] | None = None
    ) -> AsyncGenerator[bytes, None] | Coroutine[Any, Any, None]:
        if output_stream is None:
            return self.async_encode_stream_iter(input_stream)
        else:
            if (not asyncio.iscoroutinefunction(input_stream.read)
                    and not asyncio.iscoroutinefunction(output_stream.write)):
                return asyncio.to_thread(self.encode_stream, input_stream,
                                         output_stream)

            async def _coro():
                async for chunk in self.async_encode_stream_iter(input_stream):
                    await async_func(output_stream.write, chunk)

            return _coro()

    async def async_encode_stream_iter(
        self, input_stream: AsyncReader[DataBuffer] | Reader[DataBuffer]
    ) -> AsyncGenerator[bytes, None]:
        """因为线程切换问题导致他效率非常低"""
        # Header
        if self.tencent:
            yield b"\x02"
        yield b"#!SILK_V3"

        n_bytes = ffi.new("int16_t *", 1250)
        payload = ffi.new("uint8_t[1250]")
        while True:
            chunk = await async_func(input_stream.read, self.frame_size)

            if np is not None and isinstance(chunk, np.ndarray):
                chunk = chunk.tobytes()
            if not isinstance(chunk, bytes):
                raise TypeError(
                    f"input must be a file-like rb object, got {type(input).__name__}")

            n_bytes[0] = 1250
            if len(chunk) < self.frame_size:
                break
            c_chunk = ffi.from_buffer("int16_t[]", chunk)
            encoded_bytes, payload_ = await asyncio.to_thread(
                self._encode, c_chunk, chunk, payload, n_bytes)
            yield encoded_bytes
            yield payload_

    def _encode(self, c_chunk, chunk, payload, n_bytes):
        code = lib.SKP_Silk_SDK_Encode(self.enc, self.enc_control, c_chunk,
                                       len(chunk) // 2, payload, n_bytes)
        if code != 0:
            raise SilkError(code)

        return from_i16_le(n_bytes[0]), ffi.unpack(ffi.cast("char *", payload),
                                                   n_bytes[0])


class SilkDecoder:

    def __init__(
        self,
        output_samplerate: int,
        frame_size: int = 0,
        frames_per_packet: int = 1,
        more_internal_decoder_frames: bool = False,
        in_band_fec_offset: int = 0,
        loss: bool = False,
    ):

        self.dec_control = ffi.new("SKP_SILK_SDK_DecControlStruct *")
        self.dec_control.API_sampleRate = output_samplerate
        self.dec_control.frameSize = frame_size
        self.dec_control.framesPerPacket = frames_per_packet
        self.dec_control.moreInternalDecoderFrames = more_internal_decoder_frames
        self.dec_control.inBandFECOffset = in_band_fec_offset

        self.loss = loss
        self.frame_size = output_samplerate // 1000 * 40

    def __enter__(self):
        dec_size = ffi.new("int32_t *", 0)
        code: int = lib.SKP_Silk_SDK_Get_Decoder_Size(dec_size)
        if code != 0:
            raise SilkError(code)
        self.dec = lib.PyMem_Malloc(dec_size[0])
        if self.dec == ffi.NULL:
            raise MemoryError
        code = lib.SKP_Silk_SDK_InitDecoder(self.dec)
        if code != 0:
            raise SilkError(code)
        self.buf = lib.PyMem_Malloc(self.frame_size)
        if self.buf == ffi.NULL:
            raise MemoryError
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if getattr(self, "dec", None) is not None:
            lib.PyMem_Free(self.dec)
        if getattr(self, "buf", None) is not None:
            lib.PyMem_Free(self.buf)

    async def __aenter__(self):
        await asyncio.to_thread(self.__enter__)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.to_thread(self.__exit__, exc_type, exc_val, exc_tb)

    def decode(self, input_bytes: bytes):
        input_stream = BytesIO(input_bytes)
        output_stream = BytesIO()
        self.decode_stream(input_stream, output_stream)
        return output_stream.getvalue()

    async def async_decode(self, input_bytes: bytes):
        input_stream = BytesIO(input_bytes)
        output_stream = BytesIO()
        await asyncio.to_thread(self.decode_stream, input_stream, output_stream)
        return output_stream.getvalue()

    @overload
    def decode_stream(self,
                      input_stream: Reader[bytes]) -> Generator[bytes, None, None]:
        ...

    @overload
    def decode_stream(self, input_stream: Reader[bytes],
                      output_stream: Writer[bytes]) -> None:
        ...

    def decode_stream(self,
                      input_stream: Reader[bytes],
                      output_stream: Writer[bytes] | None = None
                      ) -> Generator[bytes, None, None] | None:
        if output_stream is None:
            return self.decode_stream_iter(input_stream)

        for i in self.decode_stream_iter(input_stream):
            output_stream.write(i)

    def decode_stream_iter(self,
                           input_stream: Reader[bytes]) -> Generator[bytes, None, None]:
        chunk = input_stream.read(9)
        if np is not None and isinstance(chunk, np.ndarray):
            chunk = chunk.tobytes()
        if not isinstance(chunk, bytes):
            raise TypeError(
                f"input must be a file-like rb object, got {type(input_stream).__name__}"
            )
        if chunk != b"#!SILK_V3" and chunk != b"\x02#!SILK_V":
            raise SilkError("INVALID")
        elif chunk == b"\x02#!SILK_V":
            chunk = input_stream.read(1)
            if chunk != b"3":
                raise SilkError("INVALID")

        n_bytes = ffi.new("int16_t *")
        while True:
            chunk = input_stream.read(2)
            if np is not None and isinstance(chunk, np.ndarray):
                chunk = chunk.tobytes()
            if len(chunk) < 2:
                break
            n_bytes[0] = bytes_to_i16(chunk)
            if lib.SHOULD_SWAP():
                n_bytes[0] = lib.swap_i16(n_bytes[0])
            if n_bytes[0] > self.frame_size:
                raise SilkError("INVALID")
            chunk = input_stream.read(n_bytes[0])  # type: bytes
            if len(chunk) < n_bytes[0]:  # not enough data
                raise SilkError("INVALID")
            c_chunk = ffi.from_buffer("uint8_t[]", chunk)
            unpack_bytes = self._decode(c_chunk, n_bytes)
            yield unpack_bytes

    @overload
    async def async_decode_stream(
            self, input_stream: AsyncReader[bytes]) -> AsyncGenerator[bytes, None]:
        ...

    @overload
    async def async_decode_stream(self, input_stream: AsyncReader[bytes],
                                  output_stream) -> None:
        ...

    def async_decode_stream(
            self,
            input_stream: AsyncReader[bytes],
            output_stream=None
    ) -> AsyncGenerator[bytes, None] | Coroutine[Any, Any, None]:
        if output_stream is None:
            return self.async_decode_stream_iter(input_stream)
        else:
            if (not asyncio.iscoroutinefunction(input_stream.read)
                    and not asyncio.iscoroutinefunction(output_stream.write)):
                return asyncio.to_thread(self.decode_stream, input_stream,
                                         output_stream)

            async def _coro():
                async for chunk in self.async_decode_stream_iter(input_stream):
                    await async_func(output_stream.write, chunk)

            return _coro()

    async def async_decode_stream_iter(
            self, input_stream: AsyncReader[bytes]) -> AsyncGenerator[bytes, None]:
        """因为线程切换问题导致他效率非常低"""
        chunk = await async_func(input_stream.read, 9)
        if np is not None and isinstance(chunk, np.ndarray):
            chunk = chunk.tobytes()
        if not isinstance(chunk, bytes):
            raise TypeError(
                f"input must be a file-like rb object, got {type(input_stream).__name__}"
            )
        if chunk != b"#!SILK_V3" and chunk != b"\x02#!SILK_V":
            raise SilkError("INVALID")
        elif chunk == b"\x02#!SILK_V":
            chunk = await async_func(input_stream.read, 1)
            if chunk != b"3":
                raise SilkError("INVALID")

        n_bytes = ffi.new("int16_t *")
        while True:
            chunk = await async_func(input_stream.read, 2)
            if np is not None and isinstance(chunk, np.ndarray):
                chunk = chunk.tobytes()
            if len(chunk) < 2:
                break
            n_bytes[0] = bytes_to_i16(chunk)
            if lib.SHOULD_SWAP():
                n_bytes[0] = lib.swap_i16(n_bytes[0])
            if n_bytes[0] > self.frame_size:
                raise SilkError("INVALID")
            chunk = await async_func(input_stream.read, n_bytes[0])
            if len(chunk) < n_bytes[0]:  # not enough data
                raise SilkError("INVALID")
            c_chunk = ffi.from_buffer("uint8_t[]", chunk)
            unpack_bytes = await asyncio.to_thread(self._decode, c_chunk, n_bytes)
            yield unpack_bytes

    def _decode(self, c_chunk, n_bytes):
        code = lib.SKP_Silk_SDK_Decode(
            self.dec,
            self.dec_control,
            self.loss,
            c_chunk,
            n_bytes[0],
            ffi.cast("int16_t *", self.buf),
            n_bytes,
        )
        if code != 0:
            raise SilkError(code)
        return ffi.unpack(ffi.cast("char*", self.buf), n_bytes[0] * 2)
