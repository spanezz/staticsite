from staticsite.render import RenderedString
from staticsite import Page, Feature
from staticsite.utils import parse_front_matter, write_front_matter
from staticsite.archetypes import Archetype
import jinja2
import os
import io
import pytz
import datetime
import markdown
import dateutil.parser
from urllib.parse import urlparse, urlunparse
import logging

log = logging.getLogger()


class LinkResolver(markdown.treeprocessors.Treeprocessor):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.page = None
        self.substituted = {}

    def set_page(self, page):
        self.page = page
        self.substituted = {}

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
        new_url = self.substituted.get(url)
        if new_url is not None:
            return new_url
        new_url = self.page.resolve_url(url)
        if new_url is not None:
            self.substituted[url] = new_url
        return new_url


class StaticSiteExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md, md_globals):
        self.link_resolver = LinkResolver(md)
        # Insert instance of 'mypattern' before 'references' pattern
        md.treeprocessors.add('staticsite', self.link_resolver, '_end')
        md.registerExtension(self)

    def reset(self):
        pass

    def set_page(self, page):
        self.link_resolver.set_page(page)


class MarkdownPages(Feature):
    """
    Render ``.md`` markdown pages, with front matter.

    See doc/markdown.md for details.
    """
    RUN_BEFORE = ["tags"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        md_staticsite = StaticSiteExtension()
        self.markdown = markdown.Markdown(
            extensions=self.site.settings.MARKDOWN_EXTENSIONS + [
                md_staticsite,
            ],
            extension_configs=self.site.settings.MARKDOWN_EXTENSION_CONFIGS,
            output_format="html5",
        )
        self.link_resolver = md_staticsite.link_resolver
        # Cached templates
        self._page_template = None
        self._redirect_template = None

        self.j2_filters["markdown"] = self.jinja2_markdown

        self.render_cache = self.site.caches.get("markdown")

    @jinja2.contextfilter
    def jinja2_markdown(self, context, mdtext):
        return jinja2.Markup(self.render_snippet(context.parent["page"], mdtext))

    @property
    def page_template(self):
        if not self._page_template:
            self._page_template = self.site.theme.jinja2.get_template("page.html")
        return self._page_template

    @property
    def redirect_template(self):
        if not self._redirect_template:
            self._redirect_template = self.site.theme.jinja2.get_template("redirect.html")
        return self._redirect_template

    def render_page(self, page):
        """
        Render markdown in the context of the given page.
        """
        self.link_resolver.set_page(page)

        cached = self.render_cache.get(page.src.relpath)
        if cached and cached["mtime"] != page.mtime:
            cached = None
        if cached:
            for src, dest in cached["paths"]:
                if self.link_resolver.resolve_url(src) != dest:
                    cached = None
                    break
        if cached:
            # log.info("%s: markdown cache hit", page.src.relpath)
            return cached["rendered"]

        content = page.get_content()
        self.markdown.reset()
        rendered = self.markdown.convert(content)

        self.render_cache.put(page.src.relpath, {
            "mtime": page.mtime,
            "rendered": rendered,
            "paths": list(self.link_resolver.substituted.items()),
        })

        return rendered

    def render_snippet(self, page, content):
        """
        Render markdown in the context of the given page.

        It renders the page content by default, unless `content` is set to a
        different markdown string.
        """
        if content is None:
            content = page.get_content()
        self.link_resolver.set_page(page)
        self.markdown.reset()
        return self.markdown.convert(content)

    def try_load_page(self, src):
        if not src.relpath.endswith(".md"):
            return None
        try:
            return MarkdownPage(self, src)
        except Exception:
            log.warn("%s: Failed to parse markdown page: skipped", src)
            return None

    def try_load_archetype(self, archetypes, relpath, name):
        if os.path.basename(relpath) != name + ".md":
            return None
        return MarkdownArchetype(archetypes, relpath, self)


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
    def __init__(self, archetypes, relpath, mdpages):
        super().__init__(archetypes, relpath)
        self.mdpages = mdpages

    def render(self, **kw):
        meta, rendered = super().render(**kw)

        # Reparse the rendered version
        with io.StringIO(rendered) as fd:
            # Reparse it separating front matter and markdown content
            front_matter, body = parse_markdown_with_front_matter(fd)
        try:
            style, meta = parse_front_matter(front_matter)
        except Exception:
            log.exception("archetype %s: failed to parse front matter", self.relpath)

        # Make a copy of the full parsed metadata
        archetype_meta = dict(meta)

        # Remove the path entry
        meta.pop("path", None)

        # Reserialize the page with the edited metadata
        front_matter = write_front_matter(meta, style)
        with io.StringIO() as fd:
            fd.write(front_matter)
            print(file=fd)
            for line in body:
                print(line, file=fd)
            post_body = fd.getvalue()

        return archetype_meta, post_body

#    def read_md(self, **kw):
#        """
#        Process the archetype returning its parsed front matter in a dict, and
#        its contents in a string
#        """
#
#        return style, meta, body


class MarkdownPage(Page):
    TYPE = "markdown"

    FINDABLE = True

    def __init__(self, mdpages, src):
        dirname, basename = os.path.split(src.relpath)
        if basename in ("index.md", "README.md"):
            linkpath = dirname
        else:
            linkpath = os.path.splitext(src.relpath)[0]
        super().__init__(
            site=mdpages.site,
            src=src,
            src_linkpath=linkpath,
            dst_relpath=os.path.join(linkpath, "index.html"),
            dst_link=os.path.join(mdpages.site.settings.SITE_ROOT, linkpath))

        # Shared markdown environment
        self.mdpages = mdpages

        # Sequence of lines found in the front matter
        self.front_matter = []

        # Sequence of lines found in the body
        self.body = []

        # Markdown content of the page rendered into html
        self.md_html = None

        # Modification time of the file
        self.mtime = self.src.stat.st_mtime

        # Read the contents
        if self.meta.get("date", None) is None:
            self.meta["date"] = pytz.utc.localize(datetime.datetime.utcfromtimestamp(self.mtime))

        # Parse separating front matter and markdown content
        with open(self.src.abspath, "rt") as fd:
            self.front_matter, self.body = parse_markdown_with_front_matter(fd)

        try:
            style, meta = parse_front_matter(self.front_matter)
            self.meta.update(**meta)
        except Exception:
            log.exception("%s: failed to parse front matter", self.src.relpath)

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

    def get_content(self):
        return "\n".join(self.body)

    def check(self, checker):
        self.mdpages.render_page(self)

    @property
    def content(self):
        if self.md_html is None:
            self.md_html = self.mdpages.render_page(self)
        return self.md_html

    def render(self):
        res = {}

        html = self.mdpages.page_template.render(
            page=self,
            content=self.content,
            **self.meta
        )
        res[self.dst_relpath] = RenderedString(html)

        for relpath in self.meta.get("aliases", ()):
            html = self.mdpages.redirect_template.render(
                page=self,
            )
            res[os.path.join(relpath, "index.html")] = RenderedString(html)

        return res

    def target_relpaths(self):
        res = [self.dst_relpath]
        for relpath in self.meta.get("aliases", ()):
            res.append(os.path.join(relpath, "index.html"))
        return res


FEATURES = {
    "md": MarkdownPages,
}
