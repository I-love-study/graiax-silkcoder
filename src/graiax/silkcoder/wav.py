import audioop
import wave
from io import BytesIO
from typing import Union

Num = Union[int, float]


# 根据实验，audioop 在运行的时候还是占用GIL
# 所以 to_thread 没用，不如直接同步读取
def wav_encode(data: bytes, ss: Num = 0, t: Num = -1):

    with wave.open(BytesIO(data), 'rb') as wav:
        para = wav.getparams()

        rate_trans = lambda x: int(x * para.framerate)
        wav_data = (wav.readframes(rate_trans(ss + t))[rate_trans(ss):]
                    if t > 0 else wav.readframes(wav.getnframes()))

        if para.framerate != 24000:
            wav_data = audioop.ratecv(wav_data, para.sampwidth, para.nchannels, para.framerate,
                                      24000, None)[0]
        if para.nchannels != 1:
            wav_data = audioop.tomono(wav_data, para.sampwidth, 0.5, 0.5)
        if para.sampwidth != 2:
            wav_data = audioop.lin2lin(wav_data, para.sampwidth, 2)
        return wav_data


def wav_decode(data: bytes):
    with wave.open(b := BytesIO(), 'wb') as wav_out:
        wav_out.setnchannels(1)
        wav_out.setsampwidth(2)
        wav_out.setframerate(24000)
        wav_out.writeframes(data)
    return b.getvalue()


__all__ = ["wav_encode", "wav_decode"]
