import asyncio
from io import BytesIO

try:
    import soundfile
    import soxr
    libsndfile_available = True
except ImportError:
    libsndfile_available = False


def sndfile_encode(data: bytes, audio_format: str = None, ss: int = 0, t: int = -1):
    with soundfile.SoundFile(BytesIO(data), 'r', format=audio_format) as f:
        samplerate = f.samplerate
        data = f.read(f._prepare_read(ss * samplerate, None, t * samplerate))
    if samplerate != 24000:
        pcm = soxr.resample(pcm, samplerate, 24000)
    if pcm.shape[1] > 1:
        pcm = pcm.mean(axis=1)
    b = BytesIO()
    soundfile.write(b, pcm, 24000, "PCM_16", format="RAW")
    return b.getvalue()

def sndfile_decode(data: bytes, audio_format: str = None):
    pcm, samplerate = soundfile.read(BytesIO(data),
                                     samplerate=24000,
                                     channels=1,
                                     subtype="PCM_16",
                                     format="RAW")
    b = BytesIO()
    soundfile.write(b, pcm, samplerate, format=audio_format)
    return b.getvalue()


async def async_sndfile_encode(data: bytes, audio_format: str = None, ss: int = 0, t: int = -1):
    await asyncio.to_thread(sndfile_encode, data, audio_format, ss, t)


async def async_sndfile_decode(data: bytes, audio_format: str = None):
    await asyncio.to_thread(sndfile_decode, data, audio_format)


__all__ = [
    "libsndfile_available", "sndfile_encode", "sndfile_decode", "async_sndfile_encode",
    "async_sndfile_decode"
]
