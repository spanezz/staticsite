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

This is how to create a new site with markdown pages:

**Create a new website**

```sh
mkdir mysite
cd mysite
```

**Create your main index page**

Write a file called `index.md`:
```md
# My new website

This is the introduction of my new website
```

**Preview your site while you work on it**

Run `ssite serve`, and visit <http://localhost:8000> for a live preview: each
time you save `index.md`, you will see the preview updating automatically

**Add pages**

Create `about.md`

Link it from the `index.md` as a normal markdown link, like:
`[About this site](about.md)`

**Build the site**

Run `ssite build -o web`, and the site will be built inside the `web/`
directory

**Keep going: you have a new website!**


Some tips:

* Keep your browser open on `ssite serve` for an automatic live preview of
  everything you do
* You can use `python3 -m http.server 8000` to create a little web server
  serving the version of your site built with `ssite build`. This is a
  comfortable way to can have a look at it before publishing.
* Here's a quick rsync command for publishing the site:
  `rsync -avz web/ server:/path/to/webspace`
* Run `ssite serve` on the example site provided with staticsite, and look at
  its sources, to see examples of the various functions of staticsite.


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
