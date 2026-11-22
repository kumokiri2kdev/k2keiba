from setuptools import setup

setup(
    name='k2keiba',
    version='0.2.0',
    packages=['k2kparser', 'k2kvideo', 'k2kmcp', 'k2kodds'],
    install_requires=['beautifulsoup4', 'aiohttp'],
    extras_require={
        'video': ['selenium'],      # k2kvideo only
        'mcp': ['mcp>=2,<3'],       # k2kmcp (MCP server)
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': ['k2keiba-mcp = k2kmcp.server:main'],
    },
    url='',
    license='free',
    author='kumokiri2k',
    author_email='',
    description='k2keiba JRA data parser'
)
