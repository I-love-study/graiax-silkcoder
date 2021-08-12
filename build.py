from distutils.core import Extension
from distutils.core import Distribution
from distutils.command.build_ext import build_ext
from glob import glob
import shutil

ext_modules = [
    Extension('graiax.silkcoder._silkv3',
              sources=glob('src/c_silkv3/src/*.c'),
              include_dirs=["src/c_silkv3/interface/"]
              )]

def build(setup_kwargs):
    """
    This function is mandatory in order to build the extensions.
    """
    setup_kwargs["ext_modules"] = ext_modules
    setup_kwargs["zip_safe"]    = False