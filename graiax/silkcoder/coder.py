'''这玩意没个⑨年脑淤血都设计不出来，能用就行'''
import os
import wave
import shlex
import asyncio
import audioop
import tempfile
import mimetypes
from typing import Union
from pathlib import Path
from functools import partial
from collections import namedtuple

from . import _silkv3
from .utils import (
	fsdecode, iswave, issilk, 
	makesureinput, makesureoutput, to_thread)

class CoderError(Exception):
	"""所有编码/解码的错误"""
	pass

WavSubChunk = namedtuple('WavSubChunk', ['id', 'position', 'size'])
AudioData = namedtuple('AudioData', ['audio_format', 'content', 'sample_rate', 'bits_per_sample', 'raw_data'])

async def to_thread(func, *args, **kwargs):
	loop = asyncio.get_event_loop()
	method = partial(func, *args, **kwargs)
	return await loop.run_in_executor(method)

class SilkCoder:

	def __init__(self, pcm_data=None):
		"""注:pcm为24kHz 16bit mono"""
		self.pcm = tempfile.NamedTemporaryFile(mode="w+b", delete=False, suffix='.pcm')
		if pcm_data: self.pcm.write(pcm_data)

	def __del__(self):
		pcm.close()
		os.unlink(pcm)

	@classmethod
	async def from_wav(cls, file, ss, t):
		"""从wav导入音频数据
		注:wav只允许1-48000kHz 8-16bit音频
		file是文件本身，也可以是bytesIOBytesIO实例"""
		with makesureinput(file, BytesIO_allowed=True) as f, wave.open(f, 'rb')as wav:
			wav_rate = wav_in.getframerate()
			wav_channel = wav.getnchannels()
			if ss or t:
				wav_data = wav_in.readframes((ss+t)*wav_rate)[ss*wav_rate:]
			else:
				wav_data = wav_in.readframes(wav_in.getnframes())
			converted = audioop.ratecv(wav_data, wav.getsampwidth(), wav_channel, wav_in_rate, 24000, None)[0]
			if wav_channel != 1: converted = audioop.tomono(converted, wav_channel, 0.5, 0.5)
			return cls(converted)

	@classmethod
	async def from_file(cls, file, audio_format, ss, t):
		c = cls()
		with makesureinput(file) as f:
			cmd = ['ffmpeg']
			if audio_format is not None: cmd.extend(['-f', audio_format])
			cmd.extend(['-ss', ss, '-i', f, '-t', str(t)] if t else ['-i', f])
			cmd.extend(['-af', 'aresample=resampler=soxr', '-ar', '24000', '-ac', '1', '-y' ,
				'-loglevel', 'error', '-f', 's16le', c.pcm.name])
			shell = await asyncio.create_subprocess_exec(cmd)
			p_out, p_err = await shell.communicate()
			if p.returncode != 0 or len(p_out) == 0:
				raise CoderError(
					"Decoding failed. ffmpeg returned error code: {0}\n\nOutput from ffmpeg/avlib:\n\n{1}".format(
						p.returncode, p_err.decode(errors='ignore')))
		return c

	@classmethod
	async def from_silk(cls, file):
		with makesureinput(file) as f:
			if not issilk(file):
				raise CoderError("File is not the silkv3 format")
			c = cls()
			await to_thread(_silkv3.decode, file, c.pcm.name)
		return c

	async def to_wav(self, file=None):
		with makesurefile(file, BytesIO_allowed=True) as f:
			with wave.open(f, 'wb') as wav_out:
				self.pcm.seek(0)
				wav_out.setnchannels(1)
				wav_out.setframerate(24000)
				wav_out.setsampwidth(2)
				wav_out.writeframes(self.pcm.read())
			if file is None:
				return Path(file).read_bytes()

	async def to_file(self, file=None, audio_format=None, ffmpeg_para=None):
		with makesureoutput(file) as f:
			cmd = ['ffmpeg', '-f', 's16le', '-ar', '24000', '-ac', '1', '-i', self.pcm.name]
			if audio_format is not None: cmd.extend(['-f', audio_format])
			if ffmpeg_para is not None: cmd.extend([str(a) for a in ffmpeg_para])
			cmd.extend(['-y' ,'-loglevel', 'error', f])
			shell = await asyncio.create_subprocess_exec(cmd)
			p_out, p_err = await shell.communicate()
			if p.returncode != 0 or len(p_out) == 0:
				raise CoderError(
					"Encoding failed. ffmpeg returned error code: {0}\n\nOutput from ffmpeg/avlib:\n\n{1}".format(
						p.returncode, p_err.decode(errors='ignore')))
			if file is None:
				return Path(f).read_bytes()

	async def to_silk(self, rate, file=None):
		with makesurefile(file) as f:
			await to_thread(_silkv3.decode, self.pcm.name, file)
			if file is None:
				return Path(f).read_bytes()

async def encode(
	input_voice: Union[os.PathLike, str, BytesIO, bytes], 
	output_voice: Union[os.PathLike, str, BytesIO, None]=None,
	audio_format: str=None, ensure_ffmpeg: bool=False, rate: int=65000, ss: int=0, t: int=0
	) -> Union[bool, tuple]:
	"""将音频文件转化为silk文件
	如果传入的文件为wav且ensure_ffmpeg为False,那么将会使用Python标准库的wave和audioop对数据进行转换
	(注:wave只支持1~48000Hz 16bit的wav,如不是这个范围的wav将使用ffmpeg)
	如果是其他格式的文件，将会用ffmpeg对文件进行转换(请确保安装了ffmpeg)
	audio_format请填写ffmpeg中的format格式，如果为None则由ffmpeg自动判断
	rate是码率(单位bps)，因为silk编码器本身限制,所以码率最高可能也就70kbps
	ss和t分别对应ffmpeg参数中的ss和t,方便做音频裁切
	若ss和t都为0则不做裁切"""
	if not ensure_ffmpeg and iswave(input_voice):
		pcm = SilkCoder.from_wav(input_voice, ss, t)
	else:
		pcm = SilkCoder.from_file(input_voice, audio_format, ss, t)
	return pcm.to_silk(output_voice)

async def decode(
	input_voice: Union[os.PathLike, str, BytesIO, bytes],
	output_voice: Union[os.PathLike, str, BytesIO, None]=None,
	audio_format: str=None, ensure_ffmpeg: bool=False, rate: int=None, ffmpeg_para: list=None) -> Union[bool, tuple]:
	"""将silkv3音频转换为其他音频格式
	如果输出ensure_ffmpeg为False,output_voice结尾为.wav,没有指定rate,ffmpeg_para,将使用python标准库wave储存音频
	如果没有类型为os.PathLike/str的output_voice,则audio_format为必填项
	其余情况将会使用ffmpeg进行转码"""
	pcm = SilkCoder.from_silk(input_voice)
	if isinstance(output_voice, (os.PathLike, str)):
		audio_format = fsdecode(output_voice).split('.')[-1]
	if ffmpeg_para is None and rate is None and audio_format == 'wav':
		return pcm.to_wav(output_voice)
	else:
		return pcm.to_file(output_voice, audio_format, ffmpeg_para)