from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional, Any
from staticsite import structure
from staticsite.page import Page
from staticsite.feature import Feature
from staticsite.utils import front_matter
from staticsite.page_filter import compile_page_match
import jinja2
import markupsafe
import logging

if TYPE_CHECKING:
    from staticsite import file, fstree

log = logging.getLogger("jinja2")


def load_front_matter(template: jinja2.Template) -> dict[str, Any]:
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
    def load_dir_meta(self, directory: fstree.Tree) -> Optional[dict[str, Any]]:
        # Load front matter from index.html
        if (index := directory.files.get("index.html")) is None:
            return None

        try:
            template = self.site.theme.jinja2.get_template("content:" + index.relpath)
        except Exception:
            log.exception("%s: cannot load template", index.relpath)
        else:
            if (front_matter := load_front_matter(template)):
                return front_matter

    def load_dir(
            self,
            node: structure.Node,
            directory: fstree.Tree,
            files: dict[str, tuple[dict[str, Any], file.File]]) -> list[Page]:
        # Precompile JINJA2_PAGES patterns
        want_patterns = [compile_page_match(p) for p in self.site.settings.JINJA2_PAGES]

        taken: List[str] = []
        pages: List[Page] = []
        for fname, (meta_values, src) in files.items():
            # Skip files that do not match JINJA2_PAGES
            for pattern in want_patterns:
                if pattern.match(fname):
                    break
            else:
                continue

            try:
                template = self.site.theme.jinja2.get_template("content:" + src.relpath)
            except Exception:
                log.exception("%s: cannot load template", src.relpath)
                continue

            front_matter = load_front_matter(template)
            if front_matter:
                meta_values.update(front_matter)

            if (directory_index := fname == "index.html"):
                dst = None
            else:
                # Is this still needed?
                fname = fname.replace(".j2", "")
                dst = fname

            page = node.create_page(
                    page_cls=J2Page,
                    src=src,
                    dst=dst,
                    meta_values=meta_values,
                    template=template,
                    directory_index=directory_index)
            pages.append(page)
            taken.append(fname)

        for fname in taken:
            del files[fname]

        return pages


class RenderPartialTemplateMixin:
    def _find_block(self, *names):
        for name in names:
            block = self.page_template.blocks.get("page_content")
            block_name = "page_content"
            if block is not None:
                return block_name, block
        log.warn("%s: `page_content` and `content` not found in template %s", self, self.page_template.name)
        return None, None

    @jinja2.pass_context
    def html_body(self, context, **kw) -> str:
        self.prepare_render()
        block_name, block = self._find_block("page_content", "content")
        if block is None:
            return ""
        return self.render_template_block(block, block_name, context, render_style="body")

    @jinja2.pass_context
    def html_inline(self, context, **kw) -> str:
        self.prepare_render()
        block_name, block = self._find_block("page_content", "content")
        if block is None:
            return ""
        return self.render_template_block(block, block_name, context, render_style="inline")

    @jinja2.pass_context
    def html_feed(self, context, **kw) -> str:
        self.prepare_render()
        block_name, block = self._find_block("page_content", "content")
        if block is None:
            return ""
        return self.render_template_block(block, block_name, context, render_style="feed")

    def render_template_block(self, block, block_name, context, **kw) -> str:
        render_stack = list(context.get("render_stack", ()))

        render_style = kw.get("render_style")

        if (self, render_style) in render_stack:
            render_stack.append((self, render_style))
            render_stack_path = ' → '.join(f"{p}:{s}" for p, s in render_stack)
            raise RuntimeError(f"{self}: render loop detected: {render_stack_path}")

        render_stack.append((self, render_style))
        kw["render_stack"] = render_stack
        kw["page"] = self

        try:
            return markupsafe.Markup("".join(block(self.page_template.new_context(context, shared=True, locals=kw))))
        except jinja2.TemplateError as e:
            log.error("%s: %s: failed to render block %s: %s", self, self.page_template.filename, block_name, e)
            log.debug("%s: %s: failed to render block %s: %s",
                      self, self.page_template.filename, block_name, e, exc_info=True)
            # TODO: return a "render error" page? But that risks silent errors
            return ""


class J2Page(RenderPartialTemplateMixin, Page):
    TYPE = "jinja2"

    def __init__(self, *args, template: jinja2.Template, **kw):
        # Indexed by default
        kw["meta_values"].setdefault("indexed", True)
        super().__init__(*args, **kw)

        self.meta["template"] = template


FEATURES = {
    "jinja2": J2Pages,
}
