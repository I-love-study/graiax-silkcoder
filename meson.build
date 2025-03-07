project(
    'graiax-silkcoder',
    'c',
    meson_version: '>=1.3.0'
)

python = import('python').find_installation(pure: false)

subdir('src/c_silkv3')

python.install_sources(
    files([
        'src' / 'graiax' / 'silkcoder' / '__init__.py',
        'src' / 'graiax' / 'silkcoder' / '__main__.py',
        'src' / 'graiax' / 'silkcoder' / 'ffmpeg.py',
        'src' / 'graiax' / 'silkcoder' / 'libsndfile.py',
        'src' / 'graiax' / 'silkcoder' / 'wav.py',
        'src' / 'graiax' / 'silkcoder' / 'silkv3.py',
        'src' / 'graiax' / 'silkcoder' / 'typing.py',
        'src' / 'graiax' / 'silkcoder' / 'utils.py',
        'src' / 'graiax' / 'silkcoder' / 'version.py',
    ]),
    subdir: 'graiax' / 'silkcoder',
)