from __future__ import annotations
from typing import List, Tuple
from staticsite import Page, Feature
from staticsite.archetypes import Archetype
from staticsite.utils import yaml_codec
from staticsite.contents import ContentDir
from staticsite.utils.typing import Meta
from staticsite.file import File
import docutils.io
import docutils.core
import docutils.nodes
import docutils.writers.html5_polyglot
import jinja2
import os
import io
import logging

log = logging.getLogger("rst")


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
    Render ``.rst`` reStructuredText pages, with front matter.

    See doc/reference/rst.rst for details.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        # self.render_cache = self.site.caches.get("markdown")

        # Names of tags whose content should be parsed as yaml
        self.yaml_tags = {"files", "dirs"}
        self.yaml_tags_filled = False

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

        # If requested, parse some tag contents as yaml
        if self.yaml_tags:
            for tag in self.yaml_tags:
                val = meta.get(tag)
                if val is not None and isinstance(val, str):
                    meta[tag] = yaml_codec.loads(val)

        return meta, doctree_scan

    def load_dir_meta(self, sitedir: ContentDir):
        # Load front matter from index.rst
        # Do not try to load front matter from README.md, as one wouldn't
        # clutter a repo README with staticsite front matter
        index = sitedir.files.get("index.rst")
        if index is None:
            return

        # Parse to get at the front matter
        with open(index.abspath, "rt") as fd:
            meta, doctree_scan = self.parse_rest(fd, remove_docinfo=False)

        return meta

    def load_dir(self, sitedir: ContentDir) -> List[Page]:
        # Update the list of yaml tags with information from site.metadata
        if not self.yaml_tags_filled:
            for meta in self.site.metadata.values():
                if meta.structure:
                    self.yaml_tags.add(meta.name)
            self.yaml_tags_filled = True

        taken: List[str] = []
        pages: List[Page] = []
        for fname, src in sitedir.files.items():
            if not fname.endswith(".rst"):
                continue
            taken.append(fname)

            meta = sitedir.meta_file(fname)
            if fname not in ("index.rst", "README.rst"):
                meta["site_path"] = os.path.join(sitedir.meta["site_path"], fname[:-4])
            else:
                meta["site_path"] = sitedir.meta["site_path"]

            try:
                fm_meta, doctree_scan = self.load_file_meta(sitedir, src, fname)
            except Exception as e:
                log.debug("%s: Failed to parse RestructuredText page: skipped", src, exc_info=True)
                log.warn("%s: Failed to parse RestructuredText page: skipped (%s)", src, e)
                continue

            meta.update(fm_meta)

            page = RstPage(self.site, src, meta=meta, dir=sitedir, feature=self, doctree_scan=doctree_scan)
            pages.append(page)

        for fname in taken:
            del sitedir.files[fname]

        return pages

    def load_file_meta(self, sitedir: ContentDir, src: File, fname: str) -> Tuple[Meta, DoctreeScan]:
        # Parse document into a doctree and extract docinfo metadata
        with sitedir.open(fname, src, "rt") as fd:
            meta, doctree_scan = self.parse_rest(fd)

        return meta, doctree_scan

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

    def __init__(self, *args, feature: RestructuredText, doctree_scan: DoctreeScan, **kw):
        super().__init__(*args, **kw)

        self.meta["build_path"] = os.path.join(self.meta["site_path"], "index.html")

        # Indexed by default
        self.meta.setdefault("indexed", True)

        # Shared RestructuredText environment
        self.rst = feature

        # Document doctree root node
        self.doctree_scan = doctree_scan

    def check(self, checker):
        self._render_page()

    def _render_page(self):
        if not self.doctree_scan.links_rewritten:
            for node in self.doctree_scan.links_target:
                node.attributes["refuri"] = self.resolve_url(node.attributes["refuri"])
            for node in self.doctree_scan.links_image:
                node.attributes["uri"] = self.resolve_url(node.attributes["uri"])

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

    @jinja2.contextfunction
    def html_body(self, context, **kw) -> str:
        return self._render_page()

    @jinja2.contextfunction
    def html_inline(self, context, **kw) -> str:
        return self._render_page()

    @jinja2.contextfunction
    def html_feed(self, context, **kw) -> str:
        return self._render_page()


FEATURES = {
    "rst": RestructuredText,
}
