#!/usr/bin/env python3

from setuptools import setup

setup(
    name="staticsite",
    install_requires=['unidecode', 'markdown', 'toml', 'PyYAML', 'jinja2', 'python_dateutil', 'python_slugify', 'pytz'],
    # http://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies
    extras_require={
        'serve': ['livereload'],
    },
    version="0.6",
    description="Static site generator",
    author=["Enrico Zini"],
    author_email=["enrico@enricozini.org"],
    url="https://github.com/spanezz/staticsite",
    license="http://www.gnu.org/licenses/gpl-3.0.html",
    packages=["staticsite"],
    scripts=['ssite']
)
