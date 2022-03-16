import audioop
import wave
from io import BytesIO


# 根据实验，audioop 在运行的时候还是占用GIL
# 所以 to_thread 没用，不如直接同步读取
def wav_encode(data: bytes, ss: int, t: int):

    with wave.open(BytesIO(data), 'rb') as wav:
        wav_rate = wav.getframerate()
        wav_width = wav.getsampwidth()
        wav_channel = wav.getnchannels()

        if t:
            wav_data = wav.readframes((ss + t) * wav_width * wav_rate)[ss * wav_width * wav_rate:]
        else:
            wav_data = wav.readframes(wav.getnframes())

        if wav_channel != 1: wav_data = audioop.tomono(wav_data, wav_channel, 0.5, 0.5)
        return audioop.ratecv(wav_data, wav_width, 1, wav_rate, 24000, None)[0]


def wav_decode(data: bytes):
    b = BytesIO()
    with wave.open(b, 'wb') as wav_out:
        wav_out.setnchannels(1)
        wav_out.setsampwidth(2)
        wav_out.setframerate(24000)
        wav_out.writeframes(data)
    return b.getvalue()

__all__ = ["wav_encode", "wav_decode"]