from __future__ import annotations

import json
import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

import jinja2

from staticsite.feature import Feature, PageTrackingMixin, TrackedField
from staticsite.features.data import DataPage, DataPages
from staticsite.features.links.data import Link, LinkCollection
from staticsite.features.links.index import LinkIndexPage
from staticsite.page import Page, TemplatePage

if TYPE_CHECKING:
    import argparse

    from staticsite import file, fstree
    from staticsite.source_node import SourcePageNode

log = logging.getLogger("links")


class LinksField(TrackedField["LinksPageMixin", list[dict[str, Any]]]):
    """
    Extra metadata for external links.

    It is a list of dicts of metadata, one for each link. In each dict, these keys are recognised:

    * `title`: str: short title for the link
    * `url`: str: external URL
    * `abstract`: str: long description or abstract for the link
    * `archive`: str: URL to an archived version of the site
    * `tags`: List[str]: tags for this link
    * `related`: List[Dict[str, str]]: other related links, as a list of dicts with
      `title` and `url` keys
    """

    tracked_by = "links"

    def _clean(self, page: LinksPageMixin, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise TypeError(
                f"value for {page!r}.{self.name} has type {type(value).__name__} instead of dict"
            )
        return value


class LinksPageMixin(Page):
    # Allow every page to contribute links information
    links = LinksField()


class LinksTemplatePageMixin(LinksPageMixin, TemplatePage):
    @jinja2.pass_context
    def html_body(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        rendered = super().html_body(context, **kw)

        # If the page has rendered pointers to external links, add a dataset
        # with extra information for them
        if not (external_links := getattr(self, "rendered_external_links", ())):
            return rendered

        feature = cast(Links, self.site.features["links"])
        links = feature.links
        if not feature.indices:
            return rendered

        tag_indices = feature.indices[0].by_tag
        data: dict[str, dict[str, Any]] = {}
        for url in external_links:
            if (linfo := links.get(url)) is None:
                continue
            info = linfo.as_dict()

            # Resolve tag urls for page into a { title: …,  url: … } dict
            tags = info.get("tags")
            if tags:
                tag_dicts = []
                for tag in tags:
                    dest = tag_indices[tag]
                    tag_dicts.append({"tag": tag, "url": self.url_for(dest)})
                info["tags"] = tag_dicts

            data[url] = info
        if data:
            rendered += (
                "\n<script type='application/json' class='links-metadata'>"
                f"{json.dumps(data)}"
                "</script>\n"
            )

        return rendered


class LinksPage(LinksPageMixin, DataPage):
    """
    Page with a link collection posted as metadata only.
    """

    TYPE = "links"

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        if self.links:
            self.link_collection = LinkCollection(
                {link["url"]: Link(link, page=self) for link in self.links}
            )
        else:
            self.link_collection = LinkCollection({})


class Links(PageTrackingMixin[LinksPageMixin], Feature):
    """
    Collect links and link metadata from page metadata.

    ## Annotated external links

    The Links feature allows to annotate external links with extra metadata, like
    an abstract, tags, a URL with an archived version of the site, or other related
    links.

    You can add a `links` list to the metadata of the page, containing a dict for
    each external link to annotate in the page.

    See [metadata documentation](metadata.md) for a reference on the `links` field.

    You can create a [data page](data.md) with a `links` list and a `data-type:
    links` to have the data page render as a collection of links.


    ### Links metadata

    This is the full list of supported links metadata:

    * `url: str`: the link URL
    * `archive: str`: URL to an archived version of the site
    * `title: str`: short title for the link
    * `abstract: str`: long description or abstract for the link
    * `tags: List[str]`: tags for this link
    * `related: List[Dict[str, str]]`: other related links, as a list of dicts with
      `title` and `url` keys


    ## Templates

    The template used to render link collections is `data-links.html`, which works
    both on [data-only](data.md) link collections, and on `.links`-generated pages.


    ## Link indices

    If you add a `name.links` file, empty or containing some metadata, it will be
    rendered as a hierarchy of index pages one for each link tag found.

    `data-links.html` is used as default template for `.links`-generated pages.
    """

    RUN_AFTER = ["data"]

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.j2_globals["links_tag_index_url"] = self.links_tag_index_url

        # Shortcut to access the Data feature
        self.data = cast(DataPages, self.site.features["data"])

        # Let the Data feature render link collections from pure yaml files,
        # when they have a `data_type: links` metadata
        self.data.register_page_class("links", LinksPage)

        # Index of all links
        self.links = LinkCollection()

        # Pages for .links files found in the site
        self.indices: list[LinkIndexPage] = []

        self.by_tag: dict[str, LinkCollection]

    def get_page_bases(self, page_cls: type[Page]) -> Sequence[type[Page]]:
        if issubclass(page_cls, TemplatePage):
            return (LinksTemplatePageMixin,)
        else:
            return (LinksPageMixin,)

    def get_used_page_types(self) -> list[type[Page]]:
        return [LinksPage, LinkIndexPage]

    def load_dir(
        self,
        node: SourcePageNode,
        directory: fstree.Tree,
        files: dict[str, tuple[dict[str, Any], file.File]],
    ) -> list[Page]:
        """
        Handle .links pages that generate the browseable archive of annotated
        external links
        """
        taken: list[str] = []
        pages: list[Page] = []
        for fname, (kwargs, src) in files.items():
            if not fname.endswith(".links"):
                continue
            taken.append(fname)

            name = fname[:-6]

            try:
                fm_meta = self.load_file_meta(directory, fname)
            except Exception:
                log.exception("%s: cannot parse taxonomy information", src.relpath)
                continue
            kwargs.update(fm_meta)

            page = node.create_source_page_as_path(
                page_cls=LinkIndexPage,
                src=src,
                name=name,
                links=self,
                link_collection=self.links,
                **kwargs,
            )
            if page is not None:
                pages.append(page)
                self.indices.append(page)

        for fname in taken:
            del files[fname]

        return pages

    def load_file_meta(self, directory: fstree.Tree, fname: str) -> dict[str, Any]:
        """
        Parse the links file to read its description
        """
        from staticsite.utils import front_matter

        with directory.open(fname, "rt") as fd:
            fmt, meta = front_matter.read_whole(fd)
        return meta

    @jinja2.pass_context
    def links_tag_index_url(self, context: jinja2.runtime.Context, tag: str) -> str:
        dest = self.indices[0].by_tag[tag]
        page: Page = context.parent["page"]
        return page.url_for(dest)

    def organize(self) -> None:
        # Index links by tag
        self.by_tag = defaultdict(LinkCollection)
        for page in self.tracked_pages:
            if not page.links:
                continue
            for link_dict in page.links:
                link = Link(link_dict)
                self.links.append(link)
                for tag in link.tags:
                    self.by_tag[tag].append(link)

    def generate(self) -> None:
        # Call analyze on all .links pages, to populate them
        for index in self.indices:
            index.organize()

    def add_site_commands(self, subparsers: argparse._SubParsersAction[Any]) -> None:
        super().add_site_commands(subparsers)
        from staticsite.features.links.cmdline import LinkLint

        LinkLint.add_subparser(subparsers)


FEATURES = {
    "links": Links,
}
