from distutils.core import Extension
from distutils.errors import CCompilerError, DistutilsExecError, DistutilsPlatformError
from distutils.command.build_ext import build_ext
from pathlib import Path


def get_file_list(path: str):
    return [str(f) for f in Path(path).iterdir() if f.is_file() and f.suffix == '.c']

ext_modules = [
    Extension('graiax.silkcoder._silkv3',
        sources=get_file_list('graiax/silkcoder/_c_silkv3/src'),
        include_dirs=["graiax/silkcoder/_c_silkv3/interface/"]
        )]

class BuildFailed(Exception):
    pass


class ExtBuilder(build_ext):

    def run(self):
        try:
            build_ext.run(self)
        except (DistutilsPlatformError, FileNotFoundError):
            print('Could not compile C extension.')

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except (CCompilerError, DistutilsExecError, DistutilsPlatformError, ValueError):
            print('Could not compile C extension.')


def build(setup_kwargs):
    """
    This function is mandatory in order to build the extensions.
    """
    setup_kwargs.update(
        {"ext_modules": ext_modules, "cmdclass": {"build_ext": ExtBuilder}}
    )