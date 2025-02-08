import asyncio
from io import BytesIO
from typing import Dict, Optional, Union
import importlib
from .utils import sync_to_async

try:
    import soundfile
    import soxr
except (ImportError, OSError):
    soundfile = None
    soxr = None

def sndfile_encode(data: bytes,
                   ss: float = 0,
                   t: float = -1,
                   output_samplerate: int = 24000,
                   audio_format: Optional[str] = None):
    if soundfile is None or soxr is None:
        raise ImportError("Do not have soundfile")
    with soundfile.SoundFile(BytesIO(data), 'r',
                             format=audio_format) as f:
        samplerate = f.samplerate
        frame = lambda x: int(x * samplerate)
        pcm = f.read(
            f._prepare_read(frame(ss), None,
                            frame(t) if t > 0 else -1))

    if f.channels != 1:
        pcm = pcm.mean(axis=1)
    if samplerate != output_samplerate:
        pcm = soxr.resample(pcm, samplerate, output_samplerate)
    soundfile.write(b := BytesIO(),
                    pcm,
                    output_samplerate,
                    "PCM_16",
                    format="RAW")
    return b.getvalue()


def sndfile_decode(data: bytes,
                   audio_format: str,
                   subtype: Optional[str] = None,
                   compress_level: Optional[float] = None,
                   metadata: Optional[Dict[str, str]] = None):
    if soundfile is None or soxr is None:
        raise ImportError("Do not have soundfile")
    pcm, samplerate = soundfile.read(BytesIO(data),
                                     samplerate=24000,
                                     channels=1,
                                     subtype="PCM_16",
                                     format="RAW")
    with soundfile.SoundFile(b := BytesIO(),
                             'w',
                             samplerate=samplerate,
                             channels=1,
                             format=audio_format,
                             subtype=subtype,
                             compression_level=compress_level) as f:
        if metadata:
            for k, v in metadata.items():
                setattr(f, k, v)
        f.write(pcm)
    return b.getvalue()


async_sndfile_encode = sync_to_async(sndfile_encode)
async_sndfile_decode = sync_to_async(sndfile_decode)


__all__ = [
    "sndfile_encode", "sndfile_decode", "async_sndfile_encode",
    "async_sndfile_decode"
]
