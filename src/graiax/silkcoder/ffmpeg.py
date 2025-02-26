from __future__ import annotations

import asyncio
from contextlib import nullcontext
import os
import subprocess
import sys
from typing import TYPE_CHECKING, IO, Any, AsyncGenerator, Coroutine, Generator, overload

from .silkv3 import SilkDecoder, SilkEncoder
from .typing import AsyncReader, AsyncWriter, Reader, Writer
from .utils import CoderError, create_async_func, get_ffmpeg, has_fileno, is_writer, isStrOrBytesPath, soxr_available

if TYPE_CHECKING:
    from _typeshed import StrOrBytesPath

PIPE = subprocess.PIPE

ffmpeg_coder = get_ffmpeg()
if ffmpeg_coder is not None:
    soxr = soxr_available(ffmpeg_coder)
else:
    ffmpeg_coder, soxr = None, False


def set_ffmpeg_path(path: os.PathLike | str):
    global ffmpeg_coder
    if isinstance(path, os.PathLike):
        path = os.fspath(path)
    ffmpeg_coder = path


class FFMpegEncoder:

    def __init__(self,
                 output_samplerate: int = 24000,
                 ss: float = 0,
                 t: float = -1,
                 to: float | None = None,
                 audio_format: str | None = None,
                 ffmpeg_para: list[str] | None = None,
                 ffmpeg_path: StrOrBytesPath | None = None,
                 ffmpeg_soxr_support: bool | None = None,
                 **silkv3_kwargs) -> None:
        if ffmpeg_path is not None:
            self.ffmpeg_path = ffmpeg_path
            self.soxr = (ffmpeg_soxr_support if ffmpeg_soxr_support is not None else
                         soxr_available(ffmpeg_path))
        elif ffmpeg_coder is not None:
            self.ffmpeg_path = ffmpeg_coder
            self.soxr = soxr
        else:
            raise FileNotFoundError("Where's your ffmpeg? Read README.md again plz.")

        self.audio_format = audio_format
        self.ffmpeg_para = ffmpeg_para
        self.ss = ss
        self.t = t
        self.to = to
        self.output_samplerate = output_samplerate
        self.encoder = SilkEncoder(input_samplerate=output_samplerate,
                                   output_samplerate=output_samplerate,
                                   **silkv3_kwargs)

    def _create_cmd(self,
                    filename: StrOrBytesPath | None = None) -> list[StrOrBytesPath]:
        cmd: list[StrOrBytesPath] = [self.ffmpeg_path]
        if self.audio_format is not None:
            cmd += ['-f', self.audio_format]
        if self.to is not None and self.t > 0:
            raise ValueError("`to` and `t` cannot set in same")
        if self.ss:
            cmd += ['-ss', str(round(self.ss, 3))]
        if filename is None:
            cmd += ["-read_ahead_limit", "-1", "-i", "cache:pipe:0"]
        else:
            cmd += ["-i", filename]
        if self.t > 0:
            cmd += ['-t', str(round(self.t, 3))]
        if self.to is not None:
            cmd += ['-to', str(round(self.to, 3))]
        if self.ffmpeg_para:
            cmd += self.ffmpeg_para
        if self.soxr:
            cmd += ['-af', 'aresample=resampler=soxr']
        cmd += [
            '-ar',
            str(self.output_samplerate), '-ac', '1', '-y', '-vn', '-loglevel', 'error',
            '-f', 's16le', '-'
        ]
        return cmd

    def encode(self, input_bytes: bytes):
        command = self._create_cmd()
        shell = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = shell.communicate(input_bytes)
        if shell.returncode != 0:
            raise CoderError(f"ffmpeg error:\n{stderr.decode(errors='ignore')}")
        with self.encoder as encoder:
            return encoder.encode(stdout)

    def encode_stream(self, input_file: Reader[bytes] | StrOrBytesPath,
                      output_file: Writer[bytes] | StrOrBytesPath):

        if isStrOrBytesPath(input_file):
            command = self._create_cmd(input_file)
            input_stream = PIPE
        elif not has_fileno(input_file):
            raise ValueError("Reader without fileno is unsupport")
        else:
            command = self._create_cmd()
            input_stream = input_file.fileno()
        shell = subprocess.Popen(command, stdin=input_stream, stdout=PIPE, stderr=PIPE)
        assert shell.stdout is not None

        context = nullcontext(output_file) if is_writer(output_file) else open(
            output_file, "wb")
        with self.encoder as encoder, context as output_stream:
            return encoder.encode_stream(shell.stdout, output_stream)

    def encode_stream_iter(
            self, input_file: Reader[bytes] | StrOrBytesPath) -> Generator[bytes]:

        if isStrOrBytesPath(input_file):
            command = self._create_cmd(input_file)
            input_stream = PIPE
        elif not has_fileno(input_file):
            raise ValueError("Reader without fileno is unsupport")
        else:
            command = self._create_cmd()
            input_stream = input_file.fileno()
        shell = subprocess.Popen(command, stdin=input_stream, stdout=PIPE, stderr=PIPE)
        assert shell.stdout is not None

        with self.encoder as encoder:
            return encoder.encode_stream_iter(shell.stdout)

    async def async_encode(self, input_bytes: bytes) -> bytes:
        command = self._create_cmd()
        shell = await asyncio.create_subprocess_exec(*command,
                                                     stdin=PIPE,
                                                     stdout=PIPE,
                                                     stderr=PIPE)
        stdout, stderr = await shell.communicate(input_bytes)
        if shell.returncode != 0:
            raise CoderError(f"ffmpeg error:\n{stderr.decode(errors='ignore')}")
        with self.encoder as encoder:
            return await encoder.async_encode(stdout)

    @overload
    async def async_encode_stream(
        self, input_file: Reader[bytes] | AsyncReader[bytes]
        | StrOrBytesPath
    ) -> AsyncGenerator[bytes, None]:
        ...

    @overload
    async def async_encode_stream(
            self, input_file: Reader[bytes] | AsyncReader[bytes]
        | StrOrBytesPath, output_stream: Writer[bytes] | AsyncWriter[bytes]) -> None:
        ...

    def async_encode_stream(
        self,
        input_file: Reader[bytes] | AsyncReader[bytes]
        | StrOrBytesPath,
        output_stream: Writer[bytes] | AsyncWriter[bytes]
        | None = None
    ) -> AsyncGenerator[bytes, None] | Coroutine[Any, Any, None]:
        iter_task = self.async_encode_stream_iter(input_file)
        if output_stream is None:
            return iter_task

        async def _coro():
            write = create_async_func(output_stream.write)
            async for chunk in iter_task:
                await write(chunk)

        return _coro()

    async def async_encode_stream_iter(
        self, input_file: Reader[bytes] | AsyncReader[bytes]
        | StrOrBytesPath
    ) -> AsyncGenerator[bytes, None]:

        need_input = False
        if isStrOrBytesPath(input_file):
            command = self._create_cmd(input_file)
            input_stream = PIPE
        elif has_fileno(input_file):
            command = self._create_cmd()
            input_stream = input_file.fileno()
        else:
            command = self._create_cmd()
            input_stream = PIPE
            need_input = True

            async def write(stdin: asyncio.StreamWriter):
                read = create_async_func(input_file.read)
                while chunk := await read(16384):
                    stdin.write(chunk)
                    await stdin.drain()
                stdin.close()

        shell = await asyncio.create_subprocess_exec(*command,
                                                     stdin=input_stream,
                                                     stdout=PIPE,
                                                     stderr=PIPE)
        assert shell.stdout is not None

        async def check_retcode():
            await shell.wait()
            if shell.returncode != 0:
                assert shell.stderr is not None
                context = await shell.stderr.read()
                raise CoderError(context.decode(errors="ignore"))

        tasks = [check_retcode()]
        if need_input:
            assert shell.stdin is not None
            tasks.append(write(shell.stdin))

        async with self.encoder as encoder:
            async for chunk in encoder.async_encode_stream_iter(shell.stdout):
                yield chunk

            await asyncio.gather(*tasks)


class FFMpegDecoder:

    def __init__(self,
                 audio_format: str | None = None,
                 output_samplerate: int = 24000,
                 subtype: str | None = None,
                 rate: int | str | None = None,
                 metadata: dict[str, str] | None = None,
                 ffmpeg_para: list[str] | None = None,
                 ffmpeg_path: StrOrBytesPath | None = None,
                 ffmpeg_soxr_support: bool | None = None,
                 **kwargs: dict[str, Any]):
        if ffmpeg_path is not None:
            self.ffmpeg_path = ffmpeg_path
            self.soxr = (ffmpeg_soxr_support if ffmpeg_soxr_support is not None else
                         soxr_available(ffmpeg_path))
        elif ffmpeg_coder is not None:
            self.ffmpeg_path = ffmpeg_coder
            self.soxr = soxr
        else:
            raise FileNotFoundError("Where's your ffmpeg? Read README.md again plz.")

        self.decoder = SilkDecoder(output_samplerate)
        self.output_samplerate = output_samplerate
        self.audio_format = audio_format
        self.rate = rate
        self.metadata = metadata
        self.ffmpeg_para = ffmpeg_para

    def _create_cmd(
        self,
        filename: StrOrBytesPath | None = None,
    ) -> list[StrOrBytesPath]:
        cmd = [
            self.ffmpeg_path, '-f', 's16le', '-ar',
            str(self.output_samplerate), '-ac', '1', '-i', 'pipe:'
        ]
        if self.audio_format is not None:
            cmd += ['-f', self.audio_format]
        if self.rate is not None:
            cmd += ['-b:a', str(self.rate)]
        if self.metadata is not None:
            for k, v in self.metadata.items():
                cmd += ["-metadata", f"{k}={v}"]
        if self.ffmpeg_para is not None:
            cmd += [str(a) for a in self.ffmpeg_para]
        if sys.platform == 'darwin' and self.audio_format == 'mp3':
            cmd += ["-write_xing", "0"]
        cmd += ['-y', '-loglevel', 'error']
        if filename is None:
            cmd += ['pipe:']
        else:
            cmd += [filename]
        return cmd

    def decode(self, input_bytes: bytes) -> bytes:
        command = self._create_cmd()
        shell = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        with self.decoder as decoder:
            pcm = decoder.decode(input_bytes)
        stdout, stderr = shell.communicate(pcm)
        if shell.returncode != 0:
            raise CoderError(f"ffmpeg error:\n{stderr.decode(errors='ignore')}")
        return stdout

    def decode_stream(self,
                      input_file: Reader[bytes] | StrOrBytesPath,
                      output_file: StrOrBytesPath | IO | None = None) -> None:
        if has_fileno(output_file):
            command = self._create_cmd()
            output_stream = output_file.fileno()
        elif isStrOrBytesPath(output_file):
            command = self._create_cmd(output_file)
            output_stream = PIPE
        else:
            raise ValueError("Do not support Writer without `fileno` in sync method")

        shell = subprocess.Popen(command, stdin=PIPE, stdout=output_stream)
        assert shell.stdin is not None
        context = open(
            input_file,
            "rb") if isStrOrBytesPath(input_file) else nullcontext(input_file)
        with self.decoder as decoder, context as input_stream:
            for chunk in decoder.decode_stream(input_stream):
                shell.stdin.write(chunk)
        stdout, stderr = shell.communicate()
        if shell.returncode != 0:
            raise CoderError(f"ffmpeg error:\n{stderr.decode(errors='ignore')}")

    async def async_decode(self, input_bytes: bytes) -> bytes:
        command = self._create_cmd()
        shell = await asyncio.create_subprocess_exec(*command,
                                                     stdin=PIPE,
                                                     stdout=PIPE,
                                                     stderr=PIPE)

        with self.decoder as decoder:
            pcm = await decoder.async_decode(input_bytes)
        stdout, stderr = await shell.communicate(pcm)
        if shell.returncode != 0:
            raise CoderError(f"ffmpeg error:\n{stderr.decode(errors='ignore')}")
        return stdout

    async def async_decode_stream(
        self,
        input_stream: Reader[bytes] | AsyncReader[bytes],
        output_file: StrOrBytesPath | Writer[bytes] | AsyncWriter[bytes] | None = None
    ) -> None:

        tasks = []
        need_task = False
        if isStrOrBytesPath(output_file):
            command = self._create_cmd(output_file)
            output_stream = PIPE
        elif has_fileno(output_file):
            command = self._create_cmd()
            output_stream = output_file.fileno()
        else:

            async def stream_iter(stdout: asyncio.StreamReader):
                while True:
                    try:
                        chunk = await stdout.readexactly(8192)
                    except asyncio.IncompleteReadError as e:
                        chunk = e.partial
                    if not chunk:
                        break
                    yield chunk

            async def stream_write(stdout: asyncio.StreamReader):
                assert output_file is not None
                write = create_async_func(output_file.write)
                async for chunk in stream_iter(stdout):
                    await write(chunk)

            command = self._create_cmd()
            output_stream = PIPE
            need_task = True

        shell = await asyncio.create_subprocess_exec(*command,
                                                     stdin=PIPE,
                                                     stdout=output_stream)

        if need_task:
            assert shell.stdout is not None
            tasks.append(stream_write(shell.stdout))

        async def put_input():
            assert shell.stdin is not None
            async with self.decoder as decoder:
                async for chunk in decoder.async_decode_stream(input_stream):
                    shell.stdin.write(chunk)
                shell.stdin.close()

        async def check_retcode():
            await shell.wait()
            if shell.returncode != 0:
                assert shell.stderr is not None
                context = await shell.stderr.read()
                raise CoderError(context.decode(errors="ignore"))

        tasks += (put_input(), check_retcode())

        await asyncio.gather(*tasks)

    async def async_decode_stream_iter(
        self, input_stream: Reader[bytes] | AsyncReader[bytes]
    ) -> AsyncGenerator[bytes, None]:

        command = self._create_cmd()
        output_stream = PIPE
        tasks = []

        shell = await asyncio.create_subprocess_exec(*command,
                                                     stdin=PIPE,
                                                     stdout=output_stream)

        async def put_input():
            assert shell.stdin is not None
            async with self.decoder as decoder:
                async for chunk in decoder.async_decode_stream(input_stream):
                    shell.stdin.write(chunk)
                shell.stdin.close()

        async def check_retcode():
            await shell.wait()
            if shell.returncode != 0:
                assert shell.stderr is not None
                context = await shell.stderr.read()
                raise CoderError(context.decode(errors="ignore"))

        tasks += (put_input(), check_retcode())

        func = asyncio.gather(*tasks)

        assert shell.stdout is not None
        while True:
            try:
                chunk = await shell.stdout.readexactly(8192)
            except asyncio.IncompleteReadError as e:
                chunk = e.partial
            if not chunk:
                break
            yield chunk

        await func
