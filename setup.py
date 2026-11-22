from setuptools import setup

setup(
    name='k2keiba',
    version='0.3.1',
    packages=['k2kparser', 'k2kmcp', 'k2kodds'],
    install_requires=['beautifulsoup4', 'aiohttp'],
    extras_require={
        'mcp': ['mcp>=2,<3'],       # k2kmcp (MCP server)
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': ['k2keiba-mcp = k2kmcp.server:main'],
    },
    url='',
    license='MIT',
    author='kumokiri2k',
    author_email='',
    description='k2keiba JRA data parser'
)
