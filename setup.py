from setuptools import setup, find_packages

import furo2

setup(
    name='furo2',
    version=furo2.version,
    install_requires=['PyYAML>=3.12'],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'furo2 = furo2.furo2:run',
        ],
    },
    author='motemen',
    author_email='motemen@hatena.ne.jp',
    url='https://github.com/motemen/furoshiki2',
)
