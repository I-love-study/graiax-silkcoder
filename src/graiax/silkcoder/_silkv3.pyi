from typing import Literal


def encode(pcm_data: bytes,
           input_samplerate: int,
           maximum_samplerate: int,
           bitrate: int,
           tencent: bool,
           complexity: Literal[0, 1, 2] = 2,
           packet_size: Literal[20, 40, 60, 80, 100] = 20,
           packet_loss: int = 0,
           use_in_band_fec: bool = False,
           use_dtx: bool = False):
    ...


def decode(silk_data: bytes,
           output_samplerate: int = 24000,
           packet_loss: int = 0):
    ...
