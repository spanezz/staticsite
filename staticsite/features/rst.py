from staticsite.render import RenderedString
from staticsite import Page, Feature
from staticsite.archetypes import Archetype
import docutils.io
import docutils.core
import docutils.nodes
import docutils.writers.html5_polyglot
import os
import io
import datetime
import dateutil.parser
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


class DoctreeScan:
    def __init__(self, doctree, remove_docinfo=True):
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
        if remove_docinfo and self.docinfo is not None:
            self.docinfo.parent.pop(self.docinfo_idx)

    def scan(self, element):
        """
        Scan the doctree collecting significant elements
        """
        for idx, node in enumerate(element.children):
            if self.first_title is None and isinstance(node, docutils.nodes.title):
                self.first_title = node
            elif isinstance(node, (docutils.nodes.target, docutils.nodes.reference)):
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

    def parse_rest(self, fd, remove_docinfo=True):
        """
        Parse a rest document.

        Return a tuple of 2 elements:
            * a dict with the first docinfo entries
            * the doctree with the docinfo removed
        """
        # Parse input into doctree
        doctree = docutils.core.publish_doctree(
                fd, source_class=docutils.io.FileInput, settings_overrides={"input_encoding": "unicode"})

        doctree_scan = DoctreeScan(doctree, remove_docinfo=remove_docinfo)

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

        if doctree_scan.first_title is not None:
            if "title" not in meta:
                meta["title"] = doctree_scan.first_title.astext()
            # If the title element is at the beginning of the doctree, remove
            # it to avoid a duplicate title in the rendered content
            if (doctree_scan.docinfo
                    and doctree_scan.docinfo.children
                    and doctree_scan.docinfo.children[0] == doctree_scan.first_title):
                doctree_scan.doctree.children.pop(0)

        # Normalise well-known metadata elements
        date = meta.get("date")
        if date is not None and not isinstance(date, datetime.datetime):
            date = dateutil.parser.parse(date)
            if date.tzinfo is None:
                date = self.site.timezone.localize(date)
            meta["date"] = date

        for taxonomy in self.site.settings.TAXONOMIES:
            elements = meta.get(taxonomy, None)
            if elements is not None and isinstance(elements, str):
                # if vals is a string, parse it
                meta[taxonomy] = split_tags(elements)

        return meta, doctree_scan

    def try_load_page(self, src):
        if not src.relpath.endswith(".rst"):
            return None
        try:
            return RstPage(self, src)
        except Exception:
            log.debug("%s: Failed to parse RestructuredText page: skipped", src, exc_info=True)
            log.warn("%s: Failed to parse RestructuredText page: skipped", src)
            return None

    def try_load_archetype(self, archetypes, relpath, name):
        if os.path.basename(relpath) != name + ".rst":
            return None
        return RestArchetype(archetypes, relpath, self)


class RestArchetype(Archetype):
    def __init__(self, archetypes, relpath, feature):
        super().__init__(archetypes, relpath)
        self.rst = feature

    def render(self, **kw):
        meta, rendered = super().render(**kw)

        # Reparse the rendered version
        with io.StringIO(rendered) as fd:
            parsed_meta, doctree_scan = self.rst.parse_rest(fd, remove_docinfo=False)

        meta.update(**parsed_meta)

        # # Remove path from docinfo
        # if doctree_scan.docinfo:
        #     for idx, node in doctree_scan.docinfo.children:
        #         if node.tagname == 'field' and node.attributes.get('classes')[0] == "path":
        #             doctree_scan.docinfo.pop(idx)
        #             break
        #
        # It would be good if we could now serialize the doctree back to reSt,
        # but there seems to be no writer for that.
        #
        # But no. Fall back to brutally hacking the rendered text.
        if doctree_scan.docinfo:
            lines = []
            head = True
            for line in rendered.splitlines():
                line = line.rstrip()
                if head:
                    if not line:
                        lines.append(line)
                        head = False
                    else:
                        if not line.startswith(":path: "):
                            lines.append(line)
                else:
                    lines.append(line)
            rendered = "\n".join(lines) + "\n"

        return meta, rendered


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

        if meta.get("date") is None:
            self.meta["date"] = self.site.localized_timestamp(self.src.stat.st_mtime)

    def check(self, checker):
        self._render_page()

    def _render_page(self):
        if not self.doctree_scan.links_rewritten:
            for node in self.doctree_scan.links_target:
                new_val = self.resolve_url(node.attributes["refuri"])
                if new_val is not None:
                    node.attributes["refuri"] = new_val
            for node in self.doctree_scan.links_image:
                new_val = self.resolve_url(node.attributes["uri"])
                if new_val is not None:
                    node.attributes["uri"] = new_val

        # TODO: caching
        # cached = self.render_cache.get(page.src.relpath)
        # if cached and cached["mtime"] != page.mtime:
        #     cached = None
        # if cached:
        #     for src, dest in cached["paths"]:
        #         if self.link_resolver.resolve_url(src) != dest:
        #             cached = None
        #             break
        # if cached:
        #     # log.info("%s: markdown cache hit", page.src.relpath)
        #     return cached["rendered"]

        writer = docutils.writers.html5_polyglot.Writer()
        # TODO: study if/how we can con configure publish_programmatically to
        # do as little work as possible
        output, pub = docutils.core.publish_programmatically(
            source=self.doctree_scan.doctree, source_path=None,
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
        # self.render_cache.put(page.src.relpath, {
        #     "mtime": page.mtime,
        #     "rendered": parts["body"],
        #     "paths": list(self.link_resolver.substituted.items()),
        # })
        return parts["body"]

    @property
    def content(self):
        if self.body_html is None:
            self.body_html = self._render_page()
        return self.body_html

    def render(self):
        res = {}

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
