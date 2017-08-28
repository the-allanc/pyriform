#!/usr/bin/env python

#
# Extract the project identity from the README.
#
import io
import setuptools

with io.open('README.rst', encoding='utf-8') as readme:
    readme = readme.read()

def get_definition(prefix):
    for line in readme.split('\n'):
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    err = 'no line in README.rst with prefix {!r}'.format(prefix)
    raise AssertionError(err)

def get_description():
    d_start = '|summary|\n'
    d_end = '.. all-content-above-will-be-included-in-sphinx-docs'
    i_start = readme.index(d_start) + len(d_start)
    return readme[i_start:readme.index(d_end)].strip()

name = get_definition('.. |name| replace:: ')
url = get_definition('.. _repository: ')
summary = get_definition('.. |summary| replace:: ')
description = get_description()

#
# End extraction code.
#

params = dict(
    name=name,
    version='0.1', # Remove if not using bumpversion.
    author="Allan Crooks",
    author_email="allan@increment.one",
    description=summary or name,
    long_description=description,
    license='MIT',
    url=url,
    keywords=[],
    py_modules=['pyriform'],
    include_package_data=True,
    namespace_packages=name.split('.')[:-1],
    python_requires='>=2.7',
    install_requires=[
        'requests',
        'six',
        'webtest',
    ],
    extras_require={
        'testing': [
            'pytest>=2.8',
            'pytest-sugar',
            'pytest-pep8',
            'httpbin',
        ],
        'docs': [
            'sphinx',
            'jaraco.packaging>=3.2',
            'rst.linker>=1.9',
            'allanc-sphinx[yeen]',
        ],
    },
    setup_requires=[
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        #"Development Status :: 4 - Beta",
        #"Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
    ],
    entry_points={
    },
)

if __name__ == '__main__':
    setuptools.setup(**params)