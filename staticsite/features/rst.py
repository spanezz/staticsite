from staticsite.render import RenderedString
from staticsite import Page, Feature
from staticsite.archetypes import Archetype
import docutils.io
import docutils.core
import docutils.nodes
import docutils.writers.html5_polyglot
import os
import pytz
import datetime
import dateutil.parser
from urllib.parse import urlparse, urlunparse
import logging

log = logging.getLogger()


def split_tags(x):
    """
    Split a tag list from a string of comma separated possibly quoted tags names
    """
    import shlex
    # Use shlex to split strings with or without quotes. There may be better
    # implementations, or possibly it can all boil down to a simple regexp
    return list(x for x in shlex.shlex(x, posix=True, punctuation_chars=",") if not x.startswith(","))

# class LinkResolver(markdown.treeprocessors.Treeprocessor):
#     def __init__(self, *args, **kw):
#         super().__init__(*args, **kw)
#         self.page = None
#         self.substituted = {}
#
#     def set_page(self, page):
#         self.page = page
#         self.substituted = {}
#
#     def run(self, root):
#         for a in root.iter("a"):
#             new_url = self.resolve_url(a.attrib.get("href", None))
#             if new_url is not None:
#                 a.attrib["href"] = new_url
#
#         for a in root.iter("img"):
#             new_url = self.resolve_url(a.attrib.get("src", None))
#             if new_url is not None:
#                 a.attrib["src"] = new_url
#
#     def resolve_url(self, url):
#         """
#         Resolve internal URLs.
#
#         Returns None if the URL does not need changing, else returns the new URL.
#         """
#         from markdown.util import AMP_SUBSTITUTE
#         if not url:
#             return None
#         if url.startswith(AMP_SUBSTITUTE):
#             # Possibly an overencoded mailto: link.
#             # see https://bugs.debian.org/816218
#             #
#             # Markdown then further escapes & with utils.AMP_SUBSTITUTE, so
#             # we look for it here.
#             return None
#         parsed = urlparse(url)
#         if parsed.scheme or parsed.netloc:
#             return None
#         if not parsed.path:
#             return None
#         dest = self.page.resolve_link(parsed.path)
#         # Also allow .md extension in
#         if dest is None and parsed.path.endswith(".md"):
#             dirname, basename = os.path.split(parsed.path)
#             if basename in ("index.md", "README.md"):
#                 dest = self.page.resolve_link(dirname)
#             else:
#                 dest = self.page.resolve_link(parsed.path[:-3])
#         if dest is None:
#             log.warn("%s: internal link %r does not resolve to any site page", self.page.src.relpath, url)
#             return None
#
#         res = urlunparse(
#             (parsed.scheme, parsed.netloc, dest.dst_link, parsed.params, parsed.query, parsed.fragment)
#         )
#         self.substituted[url] = res
#         return res
#
#
# class StaticSiteExtension(markdown.extensions.Extension):
#     def extendMarkdown(self, md, md_globals):
#         self.link_resolver = LinkResolver(md)
#         # Insert instance of 'mypattern' before 'references' pattern
#         md.treeprocessors.add('staticsite', self.link_resolver, '_end')
#         md.registerExtension(self)
#
#     def reset(self):
#         pass
#
#     def set_page(self, page):
#         self.link_resolver.set_page(page)


class DoctreeScan:
    def __init__(self, doctree):
        # Doctree root node
        self.doctree = doctree
        # Information useful to locate and remove the docinfo element
        self.docinfo = None
        self.docinfo_idx = None
        # First title element
        self.first_title = None
        # All <target> link elements that need rewriting on rendering
        self.links_target = []
        # All <image> link elements that need rewriting on rendering
        self.links_image = []
        # Return True if the link targets have been rewritten
        self.links_rewritten = False

        # Scan tree contents looking for significant nodes
        self.scan(self.doctree)

        # Remove docinfo element from tree
        if self.docinfo is not None:
            self.docinfo.parent.pop(self.docinfo_idx)

    def scan(self, element):
        """
        Scan the doctree collecting significant elements
        """
        for idx, node in enumerate(element.children):
            if self.first_title is None and isinstance(node, docutils.nodes.title):
                self.first_title = element
            elif isinstance(node, docutils.nodes.target):
                self.links_target.append(node)
            elif isinstance(node, docutils.nodes.image):
                self.links_image.append(node)
            elif isinstance(node, docutils.nodes.docinfo):
                self.docinfo = node
                self.docinfo_idx = idx
                # Do not recurse into a docinfo
                continue

            # Recursively descend
            self.scan(node)


class RestructuredText(Feature):
    """
    Render ``.md`` markdown pages, with front matter.

    See doc/markdown.md for details.
    """
    RUN_BEFORE = ["tags"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        # md_staticsite = StaticSiteExtension()
        # self.markdown = markdown.Markdown(
        #     extensions=self.site.settings.MARKDOWN_EXTENSIONS + [
        #         md_staticsite,
        #     ],
        #     extension_configs=self.site.settings.MARKDOWN_EXTENSION_CONFIGS,
        #     output_format="html5",
        # )
        # self.link_resolver = md_staticsite.link_resolver

        # Cached templates
        self._page_template = None
        self._redirect_template = None

        # self.render_cache = self.site.caches.get("markdown")

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

    def render_page(self, page: "RstPage"):
        """
        Render a doctree in the context of the given page.
        """
        writer = docutils.writers.html5_polyglot.Writer()
        # TODO: study if/how we can con configure publish_programmatically to
        # do as little work as possible
        output, pub = docutils.core.publish_programmatically(
            source=page.doctree_scan.doctree, source_path=None,
            source_class=docutils.io.DocTreeInput,
            destination=None, destination_path=None,
            destination_class=docutils.io.StringOutput,
            reader=None, reader_name='doctree',
            parser=None, parser_name='null',
            writer=writer, writer_name=None,
            settings=None, settings_spec=None,
            settings_overrides=None,
            config_section=None,
            enable_exit_status=False
            )
        parts = pub.writer.parts
        return parts["body"]
#         self.link_resolver.set_page(page)
#
#         cached = self.render_cache.get(page.src.relpath)
#         if cached and cached["mtime"] != page.mtime:
#             cached = None
#         if cached:
#             for src, dest in cached["paths"]:
#                 if self.link_resolver.resolve_url(src) != dest:
#                     cached = None
#                     break
#         if cached:
#             # log.info("%s: markdown cache hit", page.src.relpath)
#             return cached["rendered"]
#
#         content = page.get_content()
#         self.markdown.reset()
#         rendered = self.markdown.convert(content)
#
#         self.render_cache.put(page.src.relpath, {
#             "mtime": page.mtime,
#             "rendered": rendered,
#             "paths": list(self.link_resolver.substituted.items()),
#         })
#
#         return rendered

    def parse_rest(self, fd):
        """
        Parse a rest document.

        Return a tuple of 2 elements:
            * a dict with the first docinfo entries
            * the doctree with the docinfo removed
        """
        # Parse input into doctree
        doctree = docutils.core.publish_doctree(
                fd, source_class=docutils.io.FileInput, settings_overrides={"input_encoding": "unicode"})

        doctree_scan = DoctreeScan(doctree)

        # Get metadata fields from docinfo
        meta = {}
        if doctree_scan.docinfo is not None:
            for child in doctree_scan.docinfo.children:
                if child.tagname == 'field':
                    name = child.attributes.get('classes')[0]
                    for fchild in child.children:
                        if fchild.tagname == "field_body":
                            meta[name] = fchild.astext().strip()
                else:
                    meta[child.tagname] = child.astext().strip()

        if "title" not in meta:
            # Recursively find the first title node in the document
            node = doctree_scan.first_title
            if node is not None:
                meta["title"] = node.astext()

        return meta, doctree_scan

    def try_load_page(self, src):
        if not src.relpath.endswith(".rst"):
            return None
        return RstPage(self, src)

    # def try_load_archetype(self, archetypes, relpath, name):
    #     if not relpath.endswith(".md"):
    #         return None
    #     if not (relpath.endswith(name) or relpath.endswith(name + ".md")):
    #         return None
    #     return MarkdownArchetype(archetypes, relpath, self)


# class MarkdownArchetype(Archetype):
#     def __init__(self, archetypes, relpath, mdpages):
#         super().__init__(archetypes, relpath)
#         self.mdpages = mdpages
#
#     def render(self, **kw):
#         meta, rendered = super().render(**kw)
#
#         # Reparse the rendered version
#         with io.StringIO(rendered) as fd:
#             # Reparse it separating front matter and markdown content
#             front_matter, body = parse_markdown_with_front_matter(fd)
#         try:
#             style, meta = parse_front_matter(front_matter)
#         except Exception:
#             log.exception("archetype %s: failed to parse front matter", self.relpath)
#
#         # Make a copy of the full parsed metadata
#         archetype_meta = dict(meta)
#
#         # Remove the path entry
#         meta.pop("path", None)
#
#         # Reserialize the page with the edited metadata
#         front_matter = write_front_matter(meta, style)
#         with io.StringIO() as fd:
#             fd.write(front_matter)
#             print(file=fd)
#             for line in body:
#                 print(line, file=fd)
#             post_body = fd.getvalue()
#
#         return archetype_meta, post_body
#
# #    def read_md(self, **kw):
# #        """
# #        Process the archetype returning its parsed front matter in a dict, and
# #        its contents in a string
# #        """
# #
# #        return style, meta, body


class RstPage(Page):
    TYPE = "rst"

    FINDABLE = True

    def __init__(self, feature, src):
        dirname, basename = os.path.split(src.relpath)
        if basename in ("index.rst", "README.rst"):
            linkpath = dirname
        else:
            linkpath = os.path.splitext(src.relpath)[0]
        super().__init__(
            site=feature.site,
            src=src,
            src_linkpath=linkpath,
            dst_relpath=os.path.join(linkpath, "index.html"),
            dst_link=os.path.join(feature.site.settings.SITE_ROOT, linkpath))

        # Shared RestructuredText environment
        self.rst = feature

        # Document doctree root node
        self.doctree_scan = None

        # Content of the page rendered into html
        self.body_html = None

        # Parse document into a doctree and extract docinfo metadata
        with open(self.src.abspath, "rt") as fd:
            meta, doctree_scan = self.rst.parse_rest(fd)

        self.doctree_scan = doctree_scan
        self.meta.update(**meta)

        # Normalise well-known metadata elements
        date = meta.get("date")
        if date is None:
            self.meta["date"] = pytz.utc.localize(datetime.datetime.utcfromtimestamp(self.src.stat.st_mtime))
        elif not isinstance(date, datetime.datetime):
            self.meta["date"] = dateutil.parser.parse(date)

        for taxonomy in self.site.settings.TAXONOMIES:
            elements = self.meta.get(taxonomy, None)
            if elements is not None and isinstance(elements, str):
                # if vals is a string, parse it
                self.meta[taxonomy] = split_tags(elements)

    def check(self, checker):
        self.rst.render_page(self)

    @property
    def content(self):
        if self.body_html is None:
            self.body_html = self.rst.render_page(self)
        return self.body_html

    def render(self):
        res = {}

        if not self.doctree_scan.links_rewritten:
            for node in self.doctree_scan.links_target:
                new_val = self.resolve_url(node["refuri"])
                if new_val is not None:
                    node["refuri"] = new_val
            for node in self.doctree_scan.links_image:
                new_val = self.resolve_url(node["uri"])
                if new_val is not None:
                    node["uri"] = new_val

        html = self.rst.page_template.render(
            page=self,
            content=self.content,
            **self.meta
        )
        res[self.dst_relpath] = RenderedString(html)

        for relpath in self.meta.get("aliases", ()):
            html = self.rst.redirect_template.render(
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
    "rst": RestructuredText,
}
