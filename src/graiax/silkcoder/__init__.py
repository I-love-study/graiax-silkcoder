from typing import Union
import wave
import asyncio
import audioop
import tempfile

from . import _silkv3

def wave_cv(wav_in_name, wav_out_name):
	with wave.open(wav_in_name, 'rb')as wav_in, wave.open(wav_out_name, 'wb') as wav_out:
		wav_in_data = wav_in.readframes(wav_in.getnframes())
		wav_in_rate = wav_in.getframerate()
		converted = audioop.ratecv(wav_in_data, 2, 2, wav_in_rate, 24000, None)
		wav_out_data = audioop.tomono(converted[0], 2, 0.5, 0.5)
		wav_out.setnchannels(1)
		wav_out.setframerate(24000)
		wav_out.setsampwidth(2)
		wav_out.writeframes(wav_out_data)

def check_wave(wav_in_name):
	with wave.open(wav_in_name, 'rb')as wav:
		label = wav.getparams()
		return label.nchannels == 1 and label.framerate == 24000

async def encode(input_file: Union[Path, str], output_file: Union[Path, str]) -> str:
	"""将音频文件转化为silk文件
	如果传入的文件为wav,那么将会使用Python标准库自带的wave和audioop对数据进行转换
	如果是其他格式的文件，将会用ffmpeg对文件进行转换(请确保安装了ffmpeg并在Path目录中)"""
	if input_file not in [Path, str] or input_file not in [Path, str]:
		raise ValueError('Uncorrect Path')
	if mimetypes.guess_type(input_file) != 'audio/x-wav':
		input_file = str(input_file)
		wav = tempfile.NamedTemporaryFile()
		await asyncio.create_subprocess_shell(
			f'ffmpeg -i "{input_file}" -af aresample=resampler=soxr '
            f'-ar 24000 -ac 1 -y -loglevel error "{wav.name}"')
		_silkv3.encode(wav.name, str(output_file))
	else:
		if check_wave(input_file):
			_silkv3.encode(str(input_file), str(output_file))
		else:
			wav = tempfile.NamedTemporaryFile()
			wave_cv(input_file, wav.name)
			if not _silkv3.encode(wav.name, str(output_file)):
				raise Exception('Cannot encode it to silk file')

async def encodebytes(input_bytes: bytes) -> bytes:
	"""将音频数据转化为silk数据
	将会创建临时文件储存数据，剩下的与encode无异"""
	input_file = tempfile.NamedTemporaryFile()
	input_file.write(input_bytes)
	output_file = tempfile.NamedTemporaryFile()
	await encode(input_file.name output_file.name)
	return output_file.read()

async def decode(input_file: Union[Path, str], output_file: Union[Path, str]) -> str:
	"""将silkv3音频转换为wav
	(注：并不会对input_file是否为silk进行判断)"""
	if input_file not in [Path, str] or input_file not in [Path, str]:
		raise ValueError('Uncorrect Path')
	if not _silkv3.decode(str(input_file), str(output_file)):
		raise Exception('Cannot decode it to wave')

async def decodebytes(input_bytes: bytes) -> bytes:
	"""将silk数据转化为音频数据
	将会创建临时文件储存数据，剩下的与decode无异"""
	input_file = tempfile.NamedTemporaryFile()
	input_file.write(input_bytes)
	output_file = tempfile.NamedTemporaryFile()
	await decode(input_file.name output_file.name)
	return output_file.read()