from distutils.core import Extension
from distutils.core import Distribution
from distutils.command.build_ext import build_ext
from glob import glob
import shutil

ext_modules = [
    Extension('graiax.silkcoder._silkv3',
              sources=glob('graiax/silkcoder/_c_silkv3/src/*.c'),
              include_dirs=["graiax/silkcoder/_c_silkv3/interface/"]
              )]

def build(setup_kwargs):
    """
    This function is mandatory in order to build the extensions.
    """
    '''
    distribution = Distribution(dict(name="graiax-silkcoder", ext_modules=ext_modules))
    distribution.package_dir = r"graia/silkcoder"
    ext = build_ext(distribution)
    ext.ensure_finalized()
    ext.run()
    shutil.rmtree('graiax/silkcoder/_c_silkv3')
    '''
    setup_kwargs['ext_modules'] = ext_modules