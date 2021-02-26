# -*- coding: utf-8 -*-
from setuptools import setup

package_dir = \
{'': 'src'}

packages = \
['graiax', 'graiax.silkcoder']

package_data = \
{'': ['*']}

setup_kwargs = {
    'name': 'graiax-silkcoder',
    'version': '0.0.1',
    'description': 'transform audio file to silk',
    'long_description': '# Graiax-silkcoder\n一个silk转换器，还没测试',
    'author': 'I_love_study',
    'author_email': '1450069615@qq.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': 'https://github.com/I-love-study/graiax-silkcoder',
    'package_dir': package_dir,
    'packages': packages,
    'package_data': package_data,
    'python_requires': '>=3.8,<4.0',
}
from build import *
build(setup_kwargs)

setup(**setup_kwargs)
