import audioop
import wave
from io import BytesIO
from typing import Union


def wav_encode(data: bytes, ss: float = 0, t: float = -1, output_samplerate: int = 24000):

    with wave.open(BytesIO(data), 'rb') as wav:
        para = wav.getparams()

        rate_trans = lambda x: int(x * para.framerate)
        wav_data = (wav.readframes(rate_trans(ss +
                                              t))[rate_trans(ss):]
                    if t > 0 else wav.readframes(wav.getnframes()))

        if para.nchannels != 1:
            wav_data = audioop.tomono(wav_data, para.sampwidth, 0.5,
                                      0.5)
        if para.framerate != output_samplerate:
            wav_data = audioop.ratecv(wav_data, para.sampwidth,
                                      para.nchannels, para.framerate,
                                      output_samplerate, None)[0]
        if para.sampwidth != 2:
            wav_data = audioop.lin2lin(wav_data, para.sampwidth, 2)
            if para.sampwidth == 1:
                wav_data = audioop.bias(wav_data, 2, -32768)

        return wav_data


def wav_decode(data: bytes):
    with wave.open(b := BytesIO(), 'wb') as wav_out:
        wav_out.setnchannels(1)
        wav_out.setsampwidth(2)
        wav_out.setframerate(24000)
        wav_out.writeframes(data)
    return b.getvalue()


__all__ = ["wav_encode", "wav_decode"]
