import unittest
import wave
from io import BytesIO
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from graiax.silkcoder import Codec, decode, encode

folder = Path(__file__).parent / "data"


class Test(unittest.TestCase):

    def assertAudioAlmostSame(self,
                              a1,
                              a2,
                              places=2,
                              delta=None,
                              msg=None):
        audio1, sr1 = librosa.load(a1)
        audio2, sr2 = librosa.load(a2)

        size = max(len(audio1), len(audio2))
        mfcc1 = librosa.feature.mfcc(y=audio1, sr=sr1)
        mfcc2 = librosa.feature.mfcc(y=audio2, sr=sr2)
        mfcc1 = np.mean(mfcc1, axis=1)
        mfcc2 = np.mean(mfcc2, axis=1)
        mfcc1 = np.reshape(mfcc1, (1, -1))
        mfcc2 = np.reshape(mfcc2, (1, -1))

        similarity = (np.inner(mfcc1, mfcc2) /
                      (np.linalg.norm(mfcc1) *
                       np.linalg.norm(mfcc2)))[0][0]  # type: ignore
        diff = 1 - similarity

        if delta is not None:
            if diff <= delta:
                return

            standardMsg = f'Diff bigger than expect delta {delta}'
        else:
            if round(diff, places) == 0:
                return
            standardMsg = f'Diff bigger than expect places {places}'
        standardMsg += f"({similarity=}, {diff=})"
        msg = self._formatMessage(msg, standardMsg)
        raise self.failureException(msg)

    def test_8bit_wave(self):
        file = folder / "test_24khz_8bit.wav"
        silk = encode(file, codec=Codec.wave)
        assert silk is not None
        wav = decode(silk, audio_format="wav")
        assert wav is not None
        with wave.open(str(file), "rb") as a:
            a_secs = a.getnframes() / a.getframerate()
        with wave.open(BytesIO(wav), "rb") as b:
            b_secs = b.getnframes() / b.getframerate()

        # packet = 20ms = 0.02s
        self.assertAlmostEqual(a_secs, b_secs, delta=0.02)
        self.assertAudioAlmostSame(file, BytesIO(wav))

    def test_flac_libsndfile(self):
        file = folder / "test_48khz_24bit.flac"
        silk = encode(file, codec=Codec.libsndfile)
        assert silk is not None
        output = decode(silk, audio_format="flac", quality=1)
        assert output is not None
        self.assertAudioAlmostSame(file, BytesIO(output))

    def test_flac_libsndfile_meta(self):
        file = folder / "test_48khz_24bit.flac"
        silk = encode(file, codec=Codec.libsndfile)
        assert silk is not None
        output = decode(silk,
                        audio_format="flac",
                        quality=1,
                        metadata={"title": "测试音频"})
        assert output is not None
        with sf.SoundFile(BytesIO(output)) as s:
            self.assertEqual(s.copy_metadata()["title"], "测试音频")

    def test_flac_ffmpeg(self):
        file = folder / "test_48khz_24bit.flac"
        silk = encode(file, codec=Codec.ffmpeg)
        assert silk is not None
        output = decode(silk, audio_format="flac", quality=1)

if __name__ == "__main__":
    unittest.main(warnings="ignore")
