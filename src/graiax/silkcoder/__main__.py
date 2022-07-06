from . import decode, encode
from .utils import Method, play_audio, issilk, iswave
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(prog="silkcoder", description="silkv3的编解码器（超简单ver.）")

subparsers = parser.add_subparsers()
encode_parser = subparsers.add_parser("encode", help="编码")
encode_parser.add_argument('-i', help="输入文件", required=True)
encode_parser.add_argument('--audio_format', help="音频格式，默认为None")
encode_parser.add_argument('--codec', type=Method, choices=list(Method), help="编码器(如果需要) 默认为None")
encode_parser.add_argument('--rate', help="silk码率 默认为None 编码情况下此时编码器将会尝试将码率限制在980kb(若时常在10min内，将严守1Mb线)")
encode_parser.add_argument('-ia', '--ios-adaptive', action='store_true', help="ios适配（控制最高码率在24kbps），默认关闭")
encode_parser.add_argument('output', help="输出文件名")
encode_parser.add_argument('-ss', type=int, help="开始读取时间,对应ffmpeg/avconc中的ss(只能精确到秒) 默认为0(如t为0则忽略)")
encode_parser.add_argument('-t', type=int, help="持续读取时间,对应ffmpeg/avconc中的t(只能精确到秒) 默认为0(不剪切)")
encode_parser.set_defaults(func=encode)

decode_parser = subparsers.add_parser("decode", help="解码")
decode_parser.add_argument('-i', help="输入文件", required=True)
decode_parser.add_argument('--audio-format', help="音频格式，默认为None")
decode_parser.add_argument('--codec', type=Method, choices=list(Method), help="解码器(如果需要) 默认为None")
decode_parser.add_argument('--rate', help="输出音频码率，解码情况下则会直接传输给ffmpeg")
decode_parser.add_argument('output', help="输出文件名")
decode_parser.set_defaults(func=decode)

player_parser = subparsers.add_parser("play", help="播放")
player_parser.add_argument('input', help="输入文件", required=True)
player_parser.set_defaults(func=play_audio)


if __name__ == "__main__":
    args = parser.parse_args()
    dict_args = vars(args)

    if (func := dict_args.pop("func")) != play_audio:
        dict_args["input_voice"] = dict_args.pop("i")
        dict_args["output_voice"] = dict_args.pop("output")
        func(**dict_args)
    else:
        b = Path(dict_args["input"]).read_bytes()
        if issilk(b):
            b = decode(b, codec=Method.wave)
        elif iswave(b):
            ...
        
        play_audio(b)