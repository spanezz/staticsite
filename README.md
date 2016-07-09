# staticsite

Static site generator.

Input:

* a configuration file
* markdown files
* jinja2 templates
* any other file that should be published as-is

Output:

* a site with the same structure as the input

## Dependencies

```sh
apt install python3-tz python3-unidecode python3-markdown python3-toml \
            python3-yaml python3-jinja2 python3-dateutil python3-livereload \
            python3-slugify
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

* [doc/site.md: layout of a `staticsite` site](doc/site.md)
* [doc/settings.md: site `settings.py` reference](doc/settings.md)
* [doc/contents.md: `site/` reference](doc/contents.md)
* [doc/theme.md: `theme/` reference](doc/theme.md)
* [doc/archetypes.md: `archetypes/` reference](doc/archetypes.md)
* [doc/markdown.md: Markdown pages reference](doc/markdown.md)
* [doc/templates.md: Jinja2 templates reference](doc/templates.md)
* [doc/taxonomies.md: taxonomy reference](doc/taxonomies.md)


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
