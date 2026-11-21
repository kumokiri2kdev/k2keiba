from setuptools import setup

setup(
    name='k2keiba',
    version='0.2.0',
    packages=['k2kparser', 'k2kvideo'],
    install_requires=['beautifulsoup4', 'aiohttp'],
    extras_require={
        'video': ['selenium'],      # k2kvideo only
        'test': ['pytest'],
    },
    url='',
    license='free',
    author='kumokiri2k',
    author_email='',
    description='k2keiba JRA data parser'
)
