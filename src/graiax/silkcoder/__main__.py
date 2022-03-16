from . import decode, encode
import argparse

parser = argparse.ArgumentParser(prog="silkcoder", description="silkv3的编解码器（超简单ver.）")

subparsers = parser.add_subparsers()
encode_parser = subparsers.add_parser("encode", help="编码")
encode_parser.add_argument('-i', help="输入文件", required=True)
encode_parser.add_argument('--audio_format', help="音频格式，默认为None")
encode_parser.add_argument('--codec', help="编码器(如果需要) 默认为None")
encode_parser.add_argument('--ensure_ffmpeg',action='store_true', help="是否强制使用ffmpeg，默认为False")
encode_parser.add_argument('--rate', help="silk码率 默认为None 编码情况下此时编码器将会尝试将码率限制在980kb(若时常在10min内，将严守1Mb线)")
encode_parser.add_argument('output', help="输出文件名")
encode_parser.add_argument('-ss', type=int, help="开始读取时间,对应ffmpeg/avconc中的ss(只能精确到秒) 默认为0(如t为0则忽略)")
encode_parser.add_argument('-t', type=int, help="持续读取时间,对应ffmpeg/avconc中的t(只能精确到秒) 默认为0(不剪切)")
encode_parser.set_defaults(func=encode)

decode_parser = subparsers.add_parser("decode", help="解码")
decode_parser.add_argument('-i', help="输入文件", required=True)
decode_parser.add_argument('--audio_format', help="音频格式，默认为None")
decode_parser.add_argument('--codec', help="编码器(如果需要) 默认为None")
decode_parser.add_argument('--ensure_ffmpeg',action='store_true', help="是否强制使用ffmpeg，默认为False")
decode_parser.add_argument('--rate', help="输出音频码率，解码情况下则会直接传输给ffmpeg")
decode_parser.add_argument('output', help="输出文件名")
decode_parser.set_defaults(func=decode)

if __name__ == "__main__":

    args = parser.parse_args()
    print(args)
    func = args.func

    dict_args = vars(args)
    dict_args["input_voice"] = dict_args.pop("i")
    dict_args["output_voice"] = dict_args.pop("output")
    dict_args.pop("func")
    func(**dict_args)