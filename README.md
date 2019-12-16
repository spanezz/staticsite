# staticsite

Static site generator, rendering contents with as little complication as
possible.


## Features

* Input as [markdown](https://en.wikipedia.org/wiki/Markdown) ([github flavored](https://github.github.com/gfm/))
* Input as [restructuredText](https://en.wikipedia.org/wiki/ReStructuredText)
* Input as [json](https://en.wikipedia.org/wiki/JSON),
  [yaml](https://en.wikipedia.org/wiki/YAML), and
  [toml](https://en.wikipedia.org/wiki/TOML) data files
* Free site structure, no need to split contents and assets
* [Jinja2](https://jinja.palletsprojects.com/) templates
* Live preview


## Dependencies

```sh
apt install python3-tz python3-dateutil python3-slugify \
            python3-markdown python3-docutils \
	    python3-toml python3-ruamel.yaml \
	    python3-jinja2 python3-livereload
```

## Quick start

Example steps to create a new post, seeing it in the live preview, and build
the site ready to be published:

1. Start a preview of the site: `ssite serve example`
2. Open <http://localhost:8000> in the browser.
3. Create a new post: `ssite new example`
4. Save the new post, it automatically appears in the home page in the browser.
5. Finally, build the site: `ssite build example`
6. The built site will be in `example/web` ready to be served by a web server.

Useful tips:

* keep your browser open on `ssite serve` for an automatic live preview of
  everything you do
* you can use `python3 -m http.server 8000 --bind 127.0.0.1` to serve the
  result of `ssite build` and test your website before publishing
* a quick rsync command for publishing the site:
  `rsync -avz example/web/ server:/path/to/webspace`


## Index of the documentation

* [Reference documentation](doc/reference.md)


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
