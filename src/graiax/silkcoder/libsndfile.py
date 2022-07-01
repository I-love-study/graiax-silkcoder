import asyncio
from email.mime import audio
from io import BytesIO
from typing import Union

try:
    import soundfile
    import soxr
    libsndfile_available = True
except ImportError:
    libsndfile_available = False

Num = Union[int, float]


def sndfile_encode(data: bytes, audio_format: str = None, ss: Num = 0, t: Num = -1):
    with soundfile.SoundFile(BytesIO(data), 'r', format=audio_format) as f:
        samplerate = f.samplerate
        pcm = f.read(
            f._prepare_read(int(ss * samplerate), None,
                            int(t * samplerate) if t > 0 else -1))
    if samplerate != 24000:
        pcm = soxr.resample(pcm, samplerate, 24000)
    if pcm.shape[1] > 1:
        pcm = pcm.mean(axis=1)
    soundfile.write(b := BytesIO(), pcm, 24000, "PCM_16", format="RAW")
    return b.getvalue()


def sndfile_decode(data: bytes, audio_format: str = None, quality: float = None, metadata: dict = None):
    if quality is not None and 0 <= quality <= 1:
        raise ValueError("vbr should between 0 and 1")
    pcm, samplerate = soundfile.read(BytesIO(data),
                                     samplerate=24000,
                                     channels=1,
                                     subtype="PCM_16",
                                     format="RAW")
    with soundfile.SoundFile(b := BytesIO(),
                             'w',
                             samplerate=samplerate,
                             channels=1,
                             format=audio_format) as f:
        for k, v in metadata.items():
            f[k] = v
        if quality is not None:
            q = soundfile._ffi.new("double*", quality)
            if audio_format == "flac":
                ret = soundfile._snd.sf_command(f._file, soundfile._snd.SFC_SET_COMPRESSION_LEVEL,
                                                q, soundfile._ffi.sizeof(q))
            else:
                ret = soundfile._snd.sf_command(f._file,
                                                soundfile._snd.SFC_SET_VBR_ENCODING_QUALITY, q,
                                                soundfile._ffi.sizeof(q))
            if ret == soundfile._snd.SF_FALSE:
                err = soundfile._snd.sf_error(f._file)
                raise soundfile.LibsndfileError(err, "Error setting quality for the file")
        f.write(pcm)
    return b.getvalue()


async def async_sndfile_encode(data: bytes, audio_format: str = None, ss: Num = 0, t: Num = 0):
    await asyncio.to_thread(sndfile_encode, data, audio_format, ss, t)


async def async_sndfile_decode(data: bytes,
                               audio_format: str = None,
                               quality: float = None,
                               metadata: dict = None):
    await asyncio.to_thread(sndfile_decode, data, audio_format, quality, metadata)


__all__ = [
    "libsndfile_available", "sndfile_encode", "sndfile_decode", "async_sndfile_encode",
    "async_sndfile_decode"
]
