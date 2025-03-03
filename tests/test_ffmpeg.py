from io import BytesIO
from pathlib import Path

import pytest

from graiax.silkcoder.ffmpeg import FFMpegDecoder, FFMpegEncoder

from .utils import get_similarity, original_audio, original_audio_long

class TestFFMpeg:

    @pytest.mark.fast
    def test_ffmpeg_fast(self, tmp_path):
        silk = BytesIO()
        FFMpegEncoder(ios_adaptive=False, t=16).encode_stream(original_audio, silk)
        silk.seek(0)
        wav = tmp_path / "test_ffmpeg_encode_decode.wav"
        FFMpegDecoder("wav").decode_stream(silk, wav)
        similarity = get_similarity(original_audio, wav, a1_duration=16)
        assert similarity > 0.97
        
    def test_ffmpeg_encode_decode(self, tmp_path):
        silk = BytesIO()
        FFMpegEncoder(ios_adaptive=False).encode_stream(original_audio_long, silk)
        silk.seek(0)
        wav = tmp_path / "test_ffmpeg_encode_decode.wav"
        FFMpegDecoder("wav").decode_stream(silk, wav)
        similarity = get_similarity(original_audio_long, wav)
        assert similarity > 0.97

    def test_ffmpeg_ios_adaptive(self, tmp_path):
        silk = BytesIO()
        FFMpegEncoder(ios_adaptive=True).encode_stream(original_audio_long, silk)
        silk.seek(0)
        wav = tmp_path / "test_ffmpeg_ios_adaptive.wav"
        FFMpegDecoder("wav").decode_stream(silk, wav)
        similarity = get_similarity(original_audio_long, wav)
        assert similarity > 0.86

    def test_ffmpeg_input_file(self, tmp_path):
        FFMpegEncoder().encode_stream(original_audio_long,
                                      tmp_path / "test_ffmpeg_input_file.silk")
        FFMpegDecoder().decode_stream(tmp_path / "test_ffmpeg_input_file.silk",
                                      tmp_path / "test_ffmpeg_input_file.flac")
        similarity = get_similarity(original_audio_long,
                                    tmp_path / "test_ffmpeg_input_file.flac")
        assert similarity > 0.86
