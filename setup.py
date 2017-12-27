import codecs
import os.path
from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))
with codecs.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='postgres-db-diff',
    version='0.9.1',  # cause triggers, sequences are missing
    description='Command line tool to compare two PostgreSQL databases',
    long_description=long_description,
    url='https://github.com/petraszd/postgres-db-diff',
    author='Petras Zdanavicius',
    author_email='petraszd@gmail.com',


    keywords='postgresql database comparison command line utility',
    # packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    py_modules=['postgresdbdiff'],
    install_requires=[],
    extras_require={
        'dev': [],
        'test': [],
    },

    entry_points={
        'console_scripts': ['postgres-db-diff=postgresdbdiff:main'],
    },

    classifiers=[
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Topic :: Utilities',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
