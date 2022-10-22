# staticsite

Static site generator.

Builds a website out of [markdown](https://en.wikipedia.org/wiki/Markdown),
[restructuredText](https://en.wikipedia.org/wiki/ReStructuredText),
and [Jinja2](https://jinja.palletsprojects.com/) pages, and
[json](https://en.wikipedia.org/wiki/JSON)/[yaml](https://en.wikipedia.org/wiki/YAML)/[toml](https://en.wikipedia.org/wiki/TOML)
datasets.

Create a blog, tag your posts, publish post series.

Live preview your website, updated as you write it.

Freely organise your contents, and turn any directory into a website.

## Installation

For Debian systems: `apt install staticsite`

For RPM based systems:

```
python3 setup.py bdist_rpm \
   --requires="python3-inotify python3-markdown python3-docutils python3-jinja2 python3-pytz python3-dateutil python3-pyyaml python3-pillow"`
```


## Get started

* [A new blog in under one minute!](doc/tutorial/blog.md)
* [See more quickstart guides](doc/tutorial/README.md)


## Add features

* [HOWTO guides](doc/howto/README.md): step by step guides for getting specific
  works done with staticsite

## Get serious

* [Reference documentation](doc/reference/README.md): description of each part of
  staticsite
* [Developer documentation](doc/devel/README.md): documentation for developing
  staticsite itself


## Example sites

This is a list of sites using staticsite, whose sources are public, that can be
used as examples:

* <https://www.enricozini.org>: `git clone https://git.enricozini.org/site.git`


## License

> This program is free software: you can redistribute it and/or modify
> it under the terms of the GNU General Public License as published by
> the Free Software Foundation, either version 3 of the License, or
> (at your option) any later version.
>
> This program is distributed in the hope that it will be useful,
> but WITHOUT ANY WARRANTY; without even the implied warranty of
> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
> GNU General Public License for more details.
>
> You should have received a copy of the GNU General Public License
> along with this program.  If not, see <http://www.gnu.org/licenses/>.


## Author

Enrico Zini <enrico@enricozini.org>
