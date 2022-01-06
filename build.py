from setuptools import Extension
from glob import glob

ext_modules = [
    Extension('graiax.silkcoder._silkv3',
              sources=glob('src/c_silkv3/src/*.c'),
              include_dirs=["src/c_silkv3/interface/"])
]


def build(setup_kwargs):
    """
    This function is mandatory in order to build the extensions.
    """

    setup_kwargs.update(ext_modules=ext_modules)
