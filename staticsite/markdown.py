# coding: utf-8

from .core import Page
import re
import os
import pytz
import datetime
import markdown
import dateutil.parser
from urllib.parse import urlparse, urlunparse
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

    def render(self, page):
        self.md_staticsite.set_page(page)
        self.markdown.reset()
        return self.markdown.convert(page.get_content())

    def try_create(self, site, relpath):
        if not relpath.endswith(".md"): return None
        return MarkdownPage(self, site, relpath[:-3])


class MarkdownPage(Page):
    TYPE = "markdown"

    FINDABLE = True

    def __init__(self, mdenv, site, relpath):
        super().__init__(site, relpath)

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
        src = os.path.join(self.site.root, self.src_relpath + ".md")
        if self.meta.get("date", None) is None:
            self.meta["date"] = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(src)))

        # Parse separating front matter and markdown content
        with open(src, "rt") as fd:
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
                    self.front_matter.append(line)
                    if lineno > 1 and line == front_matter_end:
                        in_front_matter = False
                else:
                    self.body.append(line)

        from .utils import parse_front_matter
        self.meta.update(**parse_front_matter(self.front_matter))

        # Remove leading empty lines
        while self.body and not self.body[0]:
            self.body.pop(0)

        # Read title from first # title if not specified in metadata
        if not self.meta.get("title", ""):
            if self.body and self.body[0].startswith("# "):
                self.meta["title"] = self.body[0][2:].strip()

        date = self.meta.get("date", None)
        if date is not None:
            self.meta["date"] = dateutil.parser.parse(date)

    def check(self, checker):
        self.mdenv.render(self)

    @property
    def content(self):
        if self.md_html is None:
            self.md_html = self.mdenv.render(self)
        return self.md_html

    def write(self, writer):
        html = self.mdenv.page_template.render(
            page=self,
            content=self.content,
            **self.meta,
        )
        dst = writer.output_abspath(self.dst_relpath)
        with open(dst, "wt") as out:
            out.write(html)

#        for relpath in page.aliases:
#            dst = os.path.join(self.root, relpath)
#            os.makedirs(os.path.dirname(dst), exist_ok=True)
#            with open(dst, "wt") as out:
#                print('[[!meta redir="{relpath}"]]'.format(relpath=page.relpath_without_extension), file=out)

