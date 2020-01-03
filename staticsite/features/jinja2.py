from __future__ import annotations
from typing import List
from staticsite.page import Page
from staticsite.feature import Feature
from staticsite.contents import ContentDir
from staticsite.utils import front_matter
from staticsite.page_filter import compile_page_match
from staticsite.utils.typing import Meta
import jinja2
import os
import logging

log = logging.getLogger("jinja2")


class IgnorePage(Exception):
    pass


def load_front_matter(template: jinja2.Template) -> Meta:
    """
    Load front matter from a jinja2 template
    """
    # If the page has a front_matter block, render it to get the front matter
    front_matter_block = template.blocks.get("front_matter")
    if front_matter_block:
        fm = "".join(front_matter_block(template.new_context()))
        fmt, meta = front_matter.read_string(fm)
    else:
        meta = {}

    # If the metadata do not have a title, try rendering the title block
    if "title" not in meta:
        title_block = template.blocks.get("title")
        if title_block:
            try:
                title = "".join(title_block(template.new_context())).strip()
            except jinja2.exceptions.TemplateError as e:
                log.warn("%s: cannot extract title from {%% block title %%}: %s", template.name, e)
                title = None
            if title:
                meta["title"] = title

    return meta


class J2Pages(Feature):
    """
    Render jinja2 templates from the contents directory.

    See doc/reference/templates.md for details.
    """
    def load_dir_meta(self, sitedir: ContentDir):
        # Load front matter from index.html
        index = sitedir.files.get("index.html")
        if index is None:
            return

        try:
            template = self.site.theme.jinja2.get_template(index.relpath)
        except Exception:
            log.exception("%s: cannot load template", index.relpath)
        else:
            meta = load_front_matter(template)
            if meta:
                return meta

    def load_dir(self, sitedir: ContentDir) -> List[Page]:
        # Precompile JINJA2_PAGES patterns
        want_patterns = [compile_page_match(p) for p in self.site.settings.JINJA2_PAGES]

        taken: List[str] = []
        pages: List[Page] = []
        for fname, src in sitedir.files.items():
            # Skip files that do not match JINJA2_PAGES
            for pattern in want_patterns:
                if pattern.match(fname):
                    break
            else:
                continue

            meta = sitedir.meta_file(fname)
            if fname != "index.html":
                meta["site_path"] = os.path.join(sitedir.meta["site_path"], fname)
            else:
                meta["site_path"] = sitedir.meta["site_path"]

            try:
                page = J2Page(self.site, src, meta=meta, dir=sitedir, feature=self)
            except IgnorePage:
                continue

            taken.append(fname)
            pages.append(page)

        for fname in taken:
            del sitedir.files[fname]

        return pages


class J2Page(Page):
    TYPE = "jinja2"

    def __init__(self, *args, feature: J2Pages, **kw):
        super().__init__(*args, **kw)

        dirname, basename = os.path.split(self.src.relpath)
        dst_basename = basename.replace(".j2", "")

        self.meta["build_path"] = os.path.join(dirname, dst_basename)

        # Indexed by default
        self.meta.setdefault("indexed", True)

        try:
            template = self.site.theme.jinja2.get_template(self.src.relpath)
        except Exception:
            log.exception("%s: cannot load template", self.src.relpath)
            raise IgnorePage

        meta = load_front_matter(template)
        if meta:
            self.meta.update(**meta)

        self.meta["template"] = template


FEATURES = {
    "jinja2": J2Pages,
}
