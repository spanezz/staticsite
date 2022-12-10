from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, List

import jinja2

from staticsite import fields
from staticsite.feature import Feature
from staticsite.features.data import DataPage
from staticsite.features.links.data import Link, LinkCollection
from staticsite.features.links.index import LinkIndexPage
from staticsite.node import Node, Path
from staticsite.page_filter import PageFilter

if TYPE_CHECKING:
    from staticsite import Page, file, scan

log = logging.getLogger("links")


class LinksPageMixin(metaclass=fields.FieldsMetaclass):
    links = fields.Field(doc="""
        Extra metadata for external links.

        It is a list of dicts of metadata, one for each link. In each dict, these keys are recognised:

        * `title`: str: short title for the link
        * `url`: str: external URL
        * `abstract`: str: long description or abstract for the link
        * `archive`: str: URL to an archived version of the site
        * `tags`: List[str]: tags for this link
        * `related`: List[Dict[str, str]]: other related links, as a list of dicts with
          `title` and `url` keys
    """)

    @jinja2.pass_context
    def html_body(self, context, **kw) -> str:
        rendered = super().html_body(context, **kw)

        # If the page has rendered pointers to external links, add a dataset
        # with extra information for them
        if self.rendered_external_links:
            feature = self.site.features["links"]
            links = feature.links
            if feature.indices:
                tag_indices = feature.indices[0].by_tag
                data = {}
                for url in self.rendered_external_links:
                    info = links.get(url)
                    if info is None:
                        continue
                    info = info.as_dict()

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


class LinksPage(DataPage):
    """
    Page with a link collection posted as metadata only.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.link_collection = LinkCollection({link["url"]: Link(link, page=self) for link in self.meta["links"]})


class Links(Feature):
    """
    Collect links and link metadata from page metadata.

    Optionally generate link collections.
    """
    RUN_AFTER = ["data"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.j2_globals["links_merged"] = self.links_merged
        self.j2_globals["links_tag_index_url"] = self.links_tag_index_url
        self.page_mixins.append(LinksPageMixin)

        # Shortcut to access the Data feature
        self.data = self.site.features["data"]

        # Let the Data feature render link collections from pure yaml files,
        # when they have a `data_type: links` metadata
        self.data.register_page_class("links", LinksPage)

        # Collect 'links' metadata
        self.site.structure.add_tracked_metadata("links")

        # Pages for .links files found in the site
        self.indices: List[LinkIndexPage] = []

    def load_dir(
            self,
            node: Node,
            directory: scan.Directory,
            files: dict[str, tuple[dict[str, Any], file.File]]) -> list[Page]:
        """
        Handle .links pages that generate the browseable archive of annotated
        external links
        """
        taken: List[str] = []
        pages: List[Page] = []
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

            page = node.create_page(
                    page_cls=LinkIndexPage,
                    src=src,
                    name=name,
                    links=self,
                    path=Path((name,)),
                    **kwargs)
            pages.append(page)

            self.indices.append(page)

        for fname in taken:
            del files[fname]

        return pages

    def load_file_meta(self, directory: scan.Directory, fname) -> dict[str, Any]:
        """
        Parse the links file to read its description
        """
        from staticsite.utils import front_matter
        with directory.open(fname, "rt") as fd:
            fmt, meta = front_matter.read_whole(fd)
        if meta is None:
            meta = {}
        return meta

    @jinja2.pass_context
    def links_merged(self, context, path=None, limit=None, sort=None, link_tags=None, **kw):
        page_filter = PageFilter(
                self.site, path=path, limit=limit, sort=sort, allow=self.data.by_type.get("links", ()), **kw)

        # Build link tag filter
        if link_tags is not None:
            if isinstance(link_tags, str):
                link_tags = {link_tags}
            else:
                link_tags = set(link_tags)

        links = LinkCollection()
        if link_tags is None:
            for page in page_filter.filter():
                links.merge(page.links)
        else:
            for page in page_filter.filter():
                for link in page.link_collection:
                    if link_tags is not None and not link_tags.issubset(link.tags):
                        continue
                    links.append(link)

        return links

    @jinja2.pass_context
    def links_tag_index_url(self, context, tag):
        dest = self.indices[0].by_tag[tag]
        page = context.parent["page"]
        return page.url_for(dest)

    def analyze(self):
        # Index of all links
        self.links = LinkCollection()

        # Index links by tag
        self.by_tag = defaultdict(LinkCollection)
        for page in self.site.structure.pages_by_metadata["links"]:
            for link in page.links:
                link = Link(link)
                self.links.append(link)
                for tag in link.tags:
                    self.by_tag[tag].append(link)

        # Call analyze on all .links pages, to populate them
        for index in self.indices:
            index.analyze()

    def add_site_commands(self, subparsers):
        super().add_site_commands(subparsers)
        from staticsite.features.links.cmdline import LinkLint
        LinkLint.make_subparser(subparsers)


FEATURES = {
    "links": Links,
}
