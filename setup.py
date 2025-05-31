#!/usr/bin/env python3
"""
Setup script for QuickServer
"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    try:
        with open('README.md', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "QuickServer - A lightweight local file server with beautiful web interface"

setup(
    name='quickserver',
    version='0.1.0',
    author='xyanmi',
    author_email='',
    description='A lightweight local file server with a beautiful web interface',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    url='https://github.com/xyanmi/quickserver',
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
        # No external dependencies - uses only Python standard library
    ],
    entry_points={
        'console_scripts': [
            'quickserver=quickserver.__main__:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Topic :: System :: Filesystems',
    ],
    keywords='file server, http server, web interface, file sharing, local server',
    project_urls={
        'Bug Reports': 'https://github.com/quickserver/quickserver/issues',
        'Source': 'https://github.com/quickserver/quickserver',
    },
) 