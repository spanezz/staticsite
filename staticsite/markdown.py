# coding: utf-8

from .core import Archetype, Page, RenderedString
import re
import os
import io
import pytz
import datetime
import markdown
import dateutil.parser
from urllib.parse import urlparse, urlunparse
from .utils import parse_front_matter
import logging

log = logging.getLogger()

class LinkResolver(markdown.treeprocessors.Treeprocessor):
    def run(self, root):
        for a in root.iter("a"):
            new_url = self.resolve_url(a.attrib.get("href", None))
            if new_url is not None:
                a.attrib["href"] = new_url

        for a in root.iter("img"):
            new_url = self.resolve_url(a.attrib.get("src", None))
            if new_url is not None:
                a.attrib["src"] = new_url

    def resolve_url(self, url):
        """
        Resolve internal URLs.

        Returns None if the URL does not need changing, else returns the new URL.
        """
        from markdown.util import AMP_SUBSTITUTE
        if not url:
            return None
        if url.startswith(AMP_SUBSTITUTE):
            # Possibly an overencoded mailto: link.
            # see https://bugs.debian.org/816218
            #
            # Markdown then further escapes & with utils.AMP_SUBSTITUTE, so
            # we look for it here.
            return None
        parsed = urlparse(url)
        if parsed.scheme or parsed.netloc:
            return None
        if not parsed.path:
            return None
        dest = self.page.resolve_link(parsed.path)
        if dest is None:
            log.warn("%s: internal link %r does not resolve to any site page", self.page.src_relpath, url)
            return None

        return urlunparse(
            (parsed.scheme, parsed.netloc, dest.dst_link, parsed.params, parsed.query, parsed.fragment)
        )


class StaticSiteExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md, md_globals):
        self.link_resolver = LinkResolver(md)
        # Insert instance of 'mypattern' before 'references' pattern
        md.treeprocessors.add('staticsite', self.link_resolver, '_end')
        md.registerExtension(self)

    def reset(self):
        pass

    def set_page(self, page):
        self.page = page
        self.link_resolver.page = page


class MarkdownPages:
    def __init__(self, j2env):
        self.jinja2 = j2env
        self.md_staticsite = StaticSiteExtension()
        self.markdown = markdown.Markdown(
            extensions=[
                "markdown.extensions.extra",
                "markdown.extensions.codehilite",
                "markdown.extensions.fenced_code",
                self.md_staticsite,
            ],
            output_format="html5",
        )
        self.page_template = self.jinja2.get_template("page.html")
        self.redirect_template = self.jinja2.get_template("redirect.html")

    def render(self, page):
        self.md_staticsite.set_page(page)
        self.markdown.reset()
        return self.markdown.convert(page.get_content())

    def try_load_page(self, site, relpath):
        if not relpath.endswith(".md"): return None
        return MarkdownPage(self, site, relpath)

    def try_load_archetype(self, site, relpath, name):
        if not relpath.endswith(".md"): return None
        if not (relpath.endswith(name) or relpath.endswith(name + ".md")): return None
        return MarkdownArchetype(self, site, relpath)


def parse_markdown_with_front_matter(fd):
    """
    Parse lines of markdown with front matter.

    Returns two arrays: one with the lines of front matter and one with the
    lines of markdown.
    """
    front_matter = []
    body = []

    front_matter_end = None
    in_front_matter = True

    for lineno, line in enumerate(fd, 1):
        line = line.rstrip()
        if lineno == 1:
            if line == "{":
                front_matter_end = "}"
            elif line == "---":
                front_matter_end = "---"
            elif line == "+++":
                front_matter_end = "+++"
            else:
                in_front_matter = False

        if in_front_matter:
            front_matter.append(line)
            if lineno > 1 and line == front_matter_end:
                in_front_matter = False
        else:
            body.append(line)

    return front_matter, body


class MarkdownArchetype(Archetype):
    def __init__(self, mdenv, site, relpath):
        super().__init__(site, relpath)
        self.mdenv = mdenv

    def render(self, **kw):
        """
        Process the archetype returning its parsed front matter in a dict, and
        its contents in a string
        """
        # Render the archetype with jinja2
        abspath = os.path.join(self.site.archetypes_root, self.relpath)
        with open(abspath, "rt") as fd:
            template = self.site.jinja2.from_string(fd.read())

        rendered = template.render(**kw)

        with io.StringIO(rendered) as fd:
            # Reparse it separating front matter and markdown content
            front_matter, body = parse_markdown_with_front_matter(fd)

            try:
                style, meta = parse_front_matter(front_matter)
            except:
                log.exception("archetype %s: failed to parse front matter", self.relpath)

        return style, meta, body



class MarkdownPage(Page):
    TYPE = "markdown"

    FINDABLE = True

    def __init__(self, mdenv, site, relpath):
        super().__init__(site, relpath)

        self.link_relpath = os.path.splitext(self.link_relpath)[0]

        # Shared markdown environment
        self.mdenv = mdenv

        # Sequence of lines found in the front matter
        self.front_matter = []

        # Sequence of lines found in the body
        self.body = []

        # Destination file name
        self.dst_relpath = os.path.join(self.src_relpath, "index.html")

        # Markdown content of the page rendered into html
        self.md_html = None

    def get_content(self):
        return "\n".join(self.body)

    def read_metadata(self):
        # Read the contents
        src = os.path.join(self.site.site_root, self.src_relpath)
        if self.meta.get("date", None) is None:
            self.meta["date"] = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(src)))

        # Parse separating front matter and markdown content
        with open(src, "rt") as fd:
            self.front_matter, self.body = parse_markdown_with_front_matter(fd)

        try:
            style, meta = parse_front_matter(self.front_matter)
            self.meta.update(**meta)
        except:
            log.exception("%s: failed to parse front matter", self.src_relpath)

        # Remove leading empty lines
        while self.body and not self.body[0]:
            self.body.pop(0)

        # Read title from first # title if not specified in metadata
        if not self.meta.get("title", ""):
            if self.body and self.body[0].startswith("# "):
                self.meta["title"] = self.body.pop(0)[2:].strip()

                # Remove leading empty lines again
                while self.body and not self.body[0]:
                    self.body.pop(0)

        date = self.meta.get("date", None)
        if date is not None and not isinstance(date, datetime.datetime):
            self.meta["date"] = dateutil.parser.parse(date)

    def check(self, checker):
        self.mdenv.render(self)

    @property
    def content(self):
        if self.md_html is None:
            self.md_html = self.mdenv.render(self)
        return self.md_html

    def render(self):
        res = {}

        html = self.mdenv.page_template.render(
            page=self,
            content=self.content,
            **self.meta
        )
        res[self.dst_relpath] = RenderedString(html)

        for relpath in self.meta.get("aliases", ()):
            html = self.mdenv.redirect_template.render(
                page=self,
                **self.meta
            )
            res[os.path.join(relpath, "index.html")] = RenderedString(html)

        return res

    def target_relpaths(self):
        res = [self.dst_relpath]
        for relpath in self.meta.get("aliases", ()):
            res.append(os.path.join(relpath, "index.html"))
        return res
