from setuptools import Extension
from glob import glob
import sys


ext = Extension('graiax.silkcoder._silkv3',
                sources=[*glob('src/c_silkv3/src/*.c'),
                         "src/c_silkv3/coder.cpp",],
                include_dirs=["src/c_silkv3/interface/"])


if sys.byteorder == "big":
    ext.define_macros.append(("_SYSTEM_IS_BIG_ENDIAN", True))


def build(setup_kwargs):
    """
    This function is mandatory in order to build the extensions.
    """

    setup_kwargs.update(ext_modules=[ext])
