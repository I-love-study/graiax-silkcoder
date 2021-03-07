'''这玩意没个十年脑淤血都设计不出来，能用就行'''
import os
import wave
import shlex
import asyncio
import audioop
import tempfile
import mimetypes
import contextvars
from typing import Union
from pathlib import Path
from functools import partial

from . import _silkv3

class _TempControl:

	def __init__(self):
		self.temp = []

	def maketemp(self, b: bytes=b'', suffix=None):
		file = tempfile.NamedTemporaryFile(mode="w+b", delete=False, suffix=suffix)
		self.temp.append(file)
		if b:
			file.write(b)
			file.seek(0)
		return file

	def readtemp(self, name: str, size: int=-1):
		t = next(f for f in self.temp if f.name == name)
		t.seek(0)
		return t.read(size)

	def delete(self):
		for temp in self.temp:
			temp.close()
			os.unlink(temp.name)

def wave_cv(wav_in_name, wav_out_name, ss, t):
	with wave.open(wav_in_name, 'rb')as wav_in:
		wav_in_rate = wav_in.getframerate()
		if ss or t:#数据切片
			sl = slice(*tuple(map(lambda x:int(x*wav_in_rate), (ss, ss+t))))
			wav_in_data = wav_in.readframes(wav_in.getnframes())[sl]
		else:
			wav_in_data = wav_in.readframes(wav_in.getnframes())
		converted = audioop.ratecv(wav_in_data, 2, 2, wav_in_rate, 24000, None)
		wav_out_data = audioop.tomono(converted[0], 2, 0.5, 0.5)
		return wav_out_data

def check_wave(wav_in_name):
	with wave.open(wav_in_name, 'rb')as wav:
		label = wav.getparams()
		return label.nchannels == 1 and  label.framerate == 24000


async def to_thread(func, /, *args, **kwargs):
    """Same as asyncio.to_thread in python 3.9+"""
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)

async def encode_silkv3(input_file, output_file, rate):
	return await to_thread(_silkv3.encode, input_file, output_file, rate)

async def decode_silkv3(input_file, output_file):
	return await to_thread(_silkv3.decode, input_file, output_file)

async def encode(input_voice: Union[bytes, os.PathLike], output_voice: Union[None, os.PathLike]=None,
	ensure_ffmpeg: bool=False, rate: int=65000, ss: int=0, t: int=0) -> Union[bool, tuple]:
	"""将音频文件转化为silk文件
	如果传入的文件为wav且ensure_ffmpeg为False,那么将会使用Python标准库的wave和audioop对数据进行转换
	(注:wave只支持1~48000Hz 16bit的wav,如不是这个范围的wav请ensure_ffmpeg)
	如果是其他格式的文件，将会用ffmpeg对文件进行转换(请确保安装了ffmpeg)
	rate是码率(单位bps)，因为silk编码器本身限制,所以码率最高可能也就70kbps
	ss和t分别对应ffmpeg参数中的ss和t,方便做音频裁切"""
	temp = _TempControl()
	input_file = temp.maketemp(input_voice).name if isinstance(input_voice, bytes) else os.fspath(input_voice)
	output_file = temp.maketemp().name if output_voice is None else os.fspath(output_voice)
	if not ensure_ffmpeg and mimetypes.guess_type(input_file)[0] == 'audio/x-wav':
		if check_wave and not (ss or t):
			status = await encode_silkv3(input_file, output_file, rate)
		else:
			pcm = temp.maketemp(suffix='.pcm')
			pcm.write(wave_cv(input_file, ss, t))
			status = await encode_silkv3(pcm.name, output_file, rate)
	else:
		pcm = temp.maketemp(suffix='.pcm').name
		cmd = ['ffmpeg']
		cmd.extend(['-ss', str(ss), '-i', f'"{input_file}"', '-t', str(t)] if t else ['-i', f'"{input_file}"'])
		cmd.extend(['-af', 'aresample=resampler=soxr', '-ar', '24000', '-ac', '1', '-y' ,
			'-loglevel', 'error', '-f', 's16le', f'"{pcm}"'])
		shell = await asyncio.create_subprocess_shell(' '.join(cmd))
		await shell.wait()
		status = await encode_silkv3(pcm, output_file, rate)

	if output_voice is None:
		if status:
			ret = temp.readtemp(output_file)
		else:
			raise Exception
	else:
		ret = status

	temp.delete()
	return ret

async def decode(input_voice: Union[bytes, os.PathLike], output_voice: Union[None, os.PathLike]=None,
	ensure_ffmpeg: bool=False, rate: int=None, ffmpeg_para: list=None) -> Union[bool, tuple]:
	"""将silkv3音频转换为其他音频格式
	如果输出ensure_ffmpeg为False,output_voice结尾为.wav,没有指定rate,ffmpeg_para,将使用python标准库wave储存音频
	其余情况将会使用ffmpeg进行转码"""
	temp = _TempControl()
	if isinstance(input_voice, bytes):
		input_file = temp.maketemp(input_voice).name
		if temp.readtemp(input_file, 10) != b'\x02#!SILK_V3':
			raise ValueError('This is not a silkv3_file')
	else:
		with open(input_voice, 'rb') as f:
			if f.read(10) != b'\x02#!SILK_V3':
				raise ValueError('This is not a silkv3_file')
		input_file = os.fspath(input_voice)
	output_file = temp.maketemp().name if output_voice is None else os.fspath(output_voice)

	pcm = temp.maketemp(suffix='.pcm').name
	if not await decode_silkv3(input_file, pcm):
		raise Exception('Cannot decode it to pcm')

	if all((not ensure_ffmpeg, not output_voice or output_voice.endswith('.wav'), not rate, not ffmpeg_para)):
		with wave.open(output_file, 'wb') as wav_out:
			wav_out.setnchannels(1)
			wav_out.setframerate(24000)
			wav_out.setsampwidth(2)
			wav_out.writeframes(temp.readtemp(pcm))
	else:
		cmd = ['ffmpeg']
		cmd.extend(['-f', 's16le', '-ar', '24000', '-ac', '1', '-i', f'"{input_file}"'])
		if ffmpeg_para: cmd.extend([str(a) for a in ffmpeg_para])
		cmd.extend(['-y' ,'-loglevel', 'error', f'"{output_file}"'])
		shell = await asyncio.create_subprocess_shell(' '.join(cmd))
		await shell.wait()

	if output_voice is None:
		ret = temp.readtemp(output_file)
	else:
		ret = True

	temp.delete()
	return ret