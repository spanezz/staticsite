#!/usr/bin/env python3

from setuptools import setup

setup(
    name="staticsite",
    python_requires=">= 3.7",
    install_requires=[
        'markdown', 'docutils',
        'toml', 'pyyaml', 'ruamel.yaml',
        'jinja2>3', 'Pillow',
        'python_dateutil', 'python_slugify', 'pytz'],

    # http://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies
    extras_require={
        'serve': ['tornado', 'pyinotify'],
        'fast_caching': ['lmdb'],
    },
    version="2.3",
    description="Static site generator",
    author="Enrico Zini",
    author_email="enrico@enricozini.org",
    url="https://github.com/spanezz/staticsite",
    license="http://www.gnu.org/licenses/gpl-3.0.html",
    packages=[
        "staticsite",
        "staticsite.utils",
        "staticsite.features",
        "staticsite.features.links",
        "staticsite.cmd",
        "staticsite.cmd.serve"],
    scripts=['ssite']
)
