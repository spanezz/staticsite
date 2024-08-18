from __future__ import annotations

import io
import logging
import os
from typing import IO, TYPE_CHECKING, Any, List, Optional, Tuple, Type, Union, cast

import docutils.core
import docutils.io
import docutils.nodes
import docutils.writers.html5_polyglot
import jinja2

from staticsite.archetypes import Archetype
from staticsite.feature import Feature
from staticsite.markup import MarkupFeature, MarkupPage
from staticsite.page import FrontMatterPage, Page, TemplatePage
from staticsite.utils import yaml_codec

if TYPE_CHECKING:
    import docutils.node

    from staticsite import file, fstree
    from staticsite.archetypes import Archetypes
    from staticsite.source_node import SourcePageNode

log = logging.getLogger("rst")


class DoctreeScan:
    def __init__(self, doctree: docutils.nodes.document) -> None:
        # Doctree root node
        self.doctree = doctree
        # Information useful to locate and remove the docinfo element
        self.docinfo: Optional[docutils.nodes.docinfo] = None
        self.docinfo_idx: Optional[int] = None
        # First title element
        self.first_title: Optional[docutils.nodes.title] = None
        # All <target> link elements that need rewriting on rendering
        self.links_target: list[Union[docutils.nodes.target, docutils.nodes.reference]] = []
        # All <image> link elements that need rewriting on rendering
        self.links_image: list[docutils.nodes.image] = []
        # Return True if the link targets have been rewritten
        self.links_rewritten = False

        # Scan tree contents looking for significant nodes
        self.scan(self.doctree)

    def remove_docinfo(self) -> None:
        # Remove docinfo element from tree
        if self.docinfo is not None:
            self.docinfo.parent.pop(self.docinfo_idx)

    def scan(self, element: docutils.node.Node) -> None:
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


class RestructuredText(MarkupFeature, Feature):
    """
    Render ``.rst`` reStructuredText pages, with front matter.

    See doc/reference/rst.rst for details.
    """

    def __init__(self, *args: Any, **kw: Any):
        super().__init__(*args, **kw)

        self.render_cache = self.site.caches.get("rst")

        # Names of tags whose content should be parsed as yaml
        self.yaml_tags = {"files", "dirs"}
        self.yaml_tags_filled = False

    def get_used_page_types(self) -> list[Type[Page]]:
        return [RstPage]

    def parse_rest(self, fd: IO[str], remove_docinfo: bool = True) -> tuple[dict[str, Any], DoctreeScan]:
        """
        Parse a rest document.

        Return a tuple of 2 elements:
            * a dict with the first docinfo entries
            * the doctree with the docinfo removed
        """
        # Parse input into doctree
        doctree = docutils.core.publish_doctree(fd, source_class=docutils.io.FileInput)

        doctree_scan = DoctreeScan(doctree)

        # Get metadata fields from docinfo
        meta = {}
        if doctree_scan.docinfo is not None:
            for child in doctree_scan.docinfo.children:
                if child.tagname == "field":
                    name = child.attributes.get("classes")[0]
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
            if (
                doctree_scan.docinfo
                and doctree_scan.docinfo.children
                and doctree_scan.docinfo.children[0] == doctree_scan.first_title
            ):
                doctree_scan.doctree.children.pop(0)

        # If requested, parse some tag contents as yaml
        if self.yaml_tags:
            for tag in self.yaml_tags:
                val = meta.get(tag)
                if val is not None and isinstance(val, str):
                    meta[tag] = yaml_codec.loads(val)

        if remove_docinfo:
            doctree_scan.remove_docinfo()

        return meta, doctree_scan

    def load_dir_meta(self, directory: fstree.Tree) -> Optional[dict[str, Any]]:
        # Load front matter from index.rst
        # Do not try to load front matter from README.md, as one wouldn't
        # clutter a repo README with staticsite front matter
        if "index.rst" not in directory.files:
            return None

        # Parse to get at the front matter
        with directory.open("index.rst", "rt") as fd:
            meta, doctree_scan = self.parse_rest(fd, remove_docinfo=False)

        return meta

    def load_dir(
        self, node: SourcePageNode, directory: fstree.Tree, files: dict[str, tuple[dict[str, Any], file.File]]
    ) -> list[Page]:
        if not self.yaml_tags_filled:
            cls = self.site.features.get_page_class(RstPage)
            for name, field in cls._fields.items():
                if field.structure:
                    self.yaml_tags.add(name)
            self.yaml_tags_filled = True

        taken: List[str] = []
        pages: List[Page] = []
        for fname, (kwargs, src) in files.items():
            if not fname.endswith(".rst"):
                continue
            taken.append(fname)

            try:
                fm_meta, doctree_scan = self.load_file_meta(directory, fname)
            except Exception as e:
                log.debug("%s: Failed to parse RestructuredText page: skipped", src, exc_info=True)
                log.warning("%s: Failed to parse RestructuredText page: skipped (%s)", src, e)
                continue

            kwargs.update(fm_meta)
            kwargs["page_cls"] = RstPage
            kwargs["src"] = src
            kwargs["feature"] = self
            kwargs["front_matter"] = fm_meta
            kwargs["doctree_scan"] = doctree_scan

            if fname in ("index.rst", "README.rst"):
                page = node.create_source_page_as_index(**kwargs)
            else:
                page = node.create_source_page_as_path(name=fname[:-4], **kwargs)
            if page is not None:
                pages.append(page)

        for fname in taken:
            del files[fname]

        return pages

    def load_file_meta(self, directory: fstree.Tree, fname: str) -> Tuple[dict[str, Any], DoctreeScan]:
        # Parse document into a doctree and extract docinfo metadata
        with directory.open(fname, "rt") as fd:
            meta, doctree_scan = self.parse_rest(fd)

        return meta, doctree_scan

    def try_load_archetype(self, archetypes: Archetypes, relpath: str, name: str) -> Optional[Archetype]:
        if os.path.basename(relpath) != name + ".rst":
            return None
        return RestArchetype(archetypes, relpath, self)


class RestArchetype(Archetype):
    def __init__(self, archetypes: Archetypes, relpath: str, feature: RestructuredText):
        super().__init__(archetypes, relpath)
        self.feature = feature

    def render(self, **kw: Any) -> tuple[dict[str, Any], str]:
        meta, rendered = super().render(**kw)

        # Reparse the rendered version
        with io.StringIO(rendered) as fd:
            parsed_meta, doctree_scan = self.feature.parse_rest(fd, remove_docinfo=False)

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


class RstPage(FrontMatterPage, MarkupPage, TemplatePage):
    """
    RestructuredText files

    RestructuredText files have a `.rst` extension and their metadata are taken
    from docinfo information.

    `staticsite` will postprocess the RestructuredText doctree to adjust internal
    links to guarantee that they point where they should.


    ## Linking to other pages

    Pages can link to other pages via any of the normal reSt links.

    Links that start with a `/` will be rooted at the top of the site contents.

    Relative links are resolved relative to the location of the current page first,
    and failing that relative to its parent directory, and so on until the root of
    the site.

    For example, if you have `blog/2016/page.rst` that contains a link to
    `images/photo.jpg`, the link will point to the first of this
    options that will be found:

    1. `blog/2016/images/photo.jpg`
    2. `blog/images/photo.jpg`
    3. `images/photo.jpg`

    This allows organising pages pointing to other pages or assets without needing
    to worry about where they are located in the site.

    You can link to other Markdown or RestructuredText pages with the `.md` or
    `.rst` extension ([like GitHub does](https://help.github.com/articles/relative-links-in-readmes/))
    or without, as if you were editing a wiki.


    Page metadata
    -------------

    As in [Sphinx](http://www.sphinx-doc.org/en/stable/markup/misc.html#file-wide-metadata),
    a field list near the top of the file is parsed as front matter and removed
    from the generated files.

    All [bibliographic fields](http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#bibliographic-fields)
    known to docutils are parsed according to their respective type.

    All fields whose name matches a taxonomy defined in `TAXONOMY_NAMES`
    [settings](../settings.md)_ are parsed as yaml, and expected to be a list of
    strings, with the set of values (e.g. tags) of the given taxonomy for the
    current page.

    See [page metadata](../metadata.md) for a list of commonly used metadata.


    ## Rendering reStructuredText pages
    --------------------------------

    Besides the usual `meta`, reStructuredText pages have also these attributes:

    * `page.contents`: the reSt contents rendered as HTML. You may want to use
      it with the [`|safe` filter](https://jinja.palletsprojects.com/en/2.10.x/templates/#safe)
      to prevent double escaping
    """

    TYPE = "rst"

    def __init__(self, *, doctree_scan: DoctreeScan, **kw: Any):
        self.feature: RestructuredText
        # Indexed by default
        kw.setdefault("indexed", True)
        super().__init__(**kw)

        # Document doctree root node
        self.doctree_scan = doctree_scan

    def front_matter_changed(self, fd: IO[str]) -> bool:
        """
        Check if the front matter read from fd is different from ours
        """
        meta, doctree_scan = self.feature.parse_rest(fd)
        return self.front_matter != meta

    def check(self) -> None:
        self._render_page()

    def _render_page(self, absolute: bool = False) -> str:
        cache_key = self.src.relpath
        with self.markup_render_context(cache_key, absolute=absolute) as context:
            if cached := context.cache.get("rendered"):
                # log.info("%s: rst cache hit", page.src.relpath)
                return cast(str, cached)

            if not self.doctree_scan.links_rewritten:
                for node in self.doctree_scan.links_target:
                    node.attributes["refuri"] = context.link_resolver.resolve_url(node.attributes["refuri"])
                for node in self.doctree_scan.links_image:
                    node.attributes["uri"] = context.link_resolver.resolve_url(node.attributes["uri"])
                self.doctree_scan.links_rewritten = True

            writer = docutils.writers.html5_polyglot.Writer()
            # TODO: study if/how we can con configure publish_programmatically to
            # do as little work as possible
            output, pub = docutils.core.publish_programmatically(
                source=self.doctree_scan.doctree,
                source_path=None,
                source_class=docutils.io.DocTreeInput,
                destination=None,
                destination_path=None,
                destination_class=docutils.io.StringOutput,
                reader=None,
                reader_name="doctree",
                parser=None,
                parser_name="null",
                writer=writer,
                writer_name=None,
                settings=None,
                settings_spec=None,
                settings_overrides=None,
                config_section=None,
                enable_exit_status=False,
            )
            parts = pub.writer.parts
            rendered: str = parts["body"]
            context.cache["rendered"] = rendered
            return rendered

    @jinja2.pass_context
    def html_body(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        return self._render_page(absolute=self != context["page"])

    @jinja2.pass_context
    def html_inline(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        return self._render_page(absolute=self != context["page"])

    @jinja2.pass_context
    def html_feed(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        return self._render_page(absolute=self != context["page"])


FEATURES = {
    "rst": RestructuredText,
}
