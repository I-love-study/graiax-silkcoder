import librosa
import numpy as np
import wave
from io import BytesIO
from typing import BinaryIO


def package_pcm(audio: bytes,
                output_stream: BinaryIO | None = None,
                nchannels: int = 1,
                sampwidth: int = 2,
                framerate: int = 24000):

    if output_stream is None:
        output_stream_ = BytesIO()
    else:
        output_stream_ = output_stream

    with wave.open(output_stream_, "w") as wav:
        wav.setnchannels(nchannels)
        wav.setsampwidth(sampwidth)
        wav.setframerate(framerate)
        wav.writeframes(audio)

    if output_stream is None:
        return output_stream_.getvalue() # type: ignore


def get_similarity(a1, a2):
    audio1, sr1 = librosa.load(a1)
    audio2, sr2 = librosa.load(a2)

    #size = max(len(audio1), len(audio2))
    mfcc1 = librosa.feature.mfcc(y=audio1, sr=sr1)
    mfcc2 = librosa.feature.mfcc(y=audio2, sr=sr2)
    mfcc1 = np.mean(mfcc1, axis=1)
    mfcc2 = np.mean(mfcc2, axis=1)
    mfcc1 = np.reshape(mfcc1, (1, -1))
    mfcc2 = np.reshape(mfcc2, (1, -1))

    similarity = (np.inner(mfcc1, mfcc2) /
                  (np.linalg.norm(mfcc1) * np.linalg.norm(mfcc2)))[0][0]  # type: ignore
    return similarity
