import audioop
import wave
from io import BytesIO


# 根据实验，audioop 在运行的时候还是占用GIL
# 所以 to_thread 没用，不如直接同步读取
def wav_encode(data: bytes, ss: int = 0, t: int = 0):

    with wave.open(BytesIO(data), 'rb') as wav:
        wav_rate = wav.getframerate()
        wav_width = wav.getsampwidth()
        wav_channel = wav.getnchannels()

        if t:
            wav_data = wav.readframes((ss + t) * wav_rate)[ss * wav_rate:]
        else:
            wav_data = wav.readframes(wav.getnframes())

        if wav_rate != 24000:
            wav_data = audioop.ratecv(wav_data, wav_width, wav_channel, wav_rate, 24000, None)[0]
        if wav_channel != 1:
            wav_data = audioop.tomono(wav_data, wav_width, 0.5, 0.5)
        if wav_width != 2:
            wav_data = audioop.lin2lin(wav_data, wav_width, 2)
        return wav_data


def wav_decode(data: bytes):
    with wave.open(b := BytesIO(), 'wb') as wav_out:
        wav_out.setnchannels(1)
        wav_out.setsampwidth(2)
        wav_out.setframerate(24000)
        wav_out.writeframes(data)
    return b.getvalue()


__all__ = ["wav_encode", "wav_decode"]