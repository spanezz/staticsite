from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, NamedTuple

import jinja2
import markupsafe

from staticsite.feature import Feature
from staticsite.page import ChangeExtent, Page, SourcePage, TemplatePage
from staticsite.page_filter import compile_page_match
from staticsite.utils import front_matter

if TYPE_CHECKING:
    from staticsite import file, fstree
    from staticsite.source_node import SourcePageNode

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
                log.warning(
                    "%s: cannot extract title from {%% block title %%}: %s",
                    template.name,
                    e,
                )
                title = None
            if title:
                meta["title"] = title

    return meta


class J2Pages(Feature):
    """
    Render jinja2 templates from the contents directory.

    See doc/reference/templates.md for details.
    """

    def get_used_page_types(self) -> list[type[Page]]:
        return [J2Page]

    def load_dir_meta(self, directory: fstree.Tree) -> dict[str, Any] | None:
        # Load front matter from index.html
        if (index := directory.files.get("index.html")) is None:
            return None

        try:
            template = self.site.theme.jinja2.get_template("content:" + index.relpath)
        except Exception:
            log.exception("%s: cannot load template", index.relpath)
        else:
            if front_matter := load_front_matter(template):
                return front_matter
        return None

    def load_dir(
        self,
        node: SourcePageNode,
        directory: fstree.Tree,
        files: dict[str, tuple[dict[str, Any], file.File]],
    ) -> list[Page]:
        # Precompile JINJA2_PAGES patterns
        want_patterns = [compile_page_match(p) for p in self.site.settings.JINJA2_PAGES]

        taken: list[str] = []
        pages: list[Page] = []
        for fname, (kwargs, src) in files.items():
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
                kwargs.update(front_matter)

            kwargs["page_cls"] = J2Page
            kwargs["src"] = src
            kwargs["template"] = template

            # TODO: Is this replace still needed? Do we still
            # support the .j2 trick?
            fname = fname.replace(".j2", "")

            if fname == "index.html":
                page = node.create_source_page_as_index(**kwargs)
            else:
                page = node.create_source_page_as_file(dst=fname, **kwargs)

            if page is not None:
                pages.append(page)

            taken.append(fname)

        for fname in taken:
            del files[fname]

        return pages


class Block(NamedTuple):
    name: str
    block: Callable[[jinja2.runtime.Context], Iterator[str]]


class RenderPartialTemplateMixin(TemplatePage):
    def _find_block(self, *names: str) -> Block | None:
        for name in names:
            block = self.page_template.blocks.get("page_content")
            block_name = "page_content"
            if block is not None:
                return Block(block_name, block)
        log.warning(
            "%s: `page_content` and `content` not found in template %s",
            self,
            self.page_template.name,
        )
        return None

    @jinja2.pass_context
    def html_body(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        if (block := self._find_block("page_content", "content")) is None:
            return ""
        return self.render_template_block(block, context, render_style="body")

    @jinja2.pass_context
    def html_inline(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        if (block := self._find_block("page_content", "content")) is None:
            return ""
        return self.render_template_block(block, context, render_style="inline")

    @jinja2.pass_context
    def html_feed(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        if (block := self._find_block("page_content", "content")) is None:
            return ""
        return self.render_template_block(block, context, render_style="feed")

    def render_template_block(
        self, block: Block, context: jinja2.runtime.Context, **kw: Any
    ) -> str:
        render_stack = list(context.get("render_stack", ()))

        render_style = kw.get("render_style")

        if (self, render_style) in render_stack:
            render_stack.append((self, render_style))
            render_stack_path = " → ".join(f"{p}:{s}" for p, s in render_stack)
            raise RuntimeError(f"{self}: render loop detected: {render_stack_path}")

        render_stack.append((self, render_style))
        kw["render_stack"] = render_stack
        kw["page"] = self

        try:
            return markupsafe.Markup(
                "".join(
                    block.block(
                        self.page_template.new_context(context, shared=True, locals=kw)
                    )
                )
            )
        except jinja2.TemplateError as e:
            log.error(
                "%s: %s: failed to render block %s: %s",
                self,
                self.page_template.filename,
                block.name,
                e,
            )
            log.debug(
                "%s: %s: failed to render block %s: %s",
                self,
                self.page_template.filename,
                block.name,
                e,
                exc_info=True,
            )
            # TODO: return a "render error" page? But that risks silent errors
            return ""


class J2Page(RenderPartialTemplateMixin, TemplatePage, SourcePage):
    """
    Jinja2 pages

    You can put [jinja2 templates](templates.md) in your site contents, and they
    will be rendered as site pages.

    This can be used to generate complex index pages, blog front pages, and
    anything else [Jinja2](http://jinja.pocoo.org/) is able to generate.

    You can set `JINJA2_PAGES` in the [site settings](settings.md) to a list of
    patterns (globs or regexps as in [page filters](page-filter.md)) matching file
    names to consider jinja2 templates by default. It defaults to
    `["*.html", "*.j2.*"]`.

    Any file with `.j2.` in their file name will be rendered as a template,
    stripping `.j2.` in the destination file name.

    For example, `dir/robots.j2.txt` will become `dir/robots.txt` when the site is
    built.

    ## Front matter

    If a page defines a jinja2 block called `front_matter`, the block is rendered
    and parsed as front matter.

    **Note**: [jinja2 renders all contents it finds before
    `{% extends %}`](https://jinja.palletsprojects.com/en/2.10.x/templates/#child-template).
    To prevent your front matter from ending up in the rendered HTML, place the
    `front_matter` block after the `{% extends %}` directive, or manage your front
    matter from [`.staticfile` directory metadata](content.md).

    If you want to use `template_*` entries, you can wrap the front matter around
    `{% raw %}` to prevent jinja2 from rendering their contents as part of the rest
    of the template.
    """

    TYPE = "jinja2"

    def __init__(self, *args: Any, template: jinja2.Template, **kw: Any):
        # Indexed by default
        kw.setdefault("indexed", True)
        super().__init__(*args, **kw)

        self.template = template

    def _compute_change_extent(self) -> ChangeExtent:
        # TODO: with some more infrastructure, we can track what pages
        # contributed the links, and compute something better.
        #
        # To track this we need to study the template system to see if there is
        # a way to find what page filter expressions are used, or what pages
        # are looked up, during last render.
        return ChangeExtent.ALL


FEATURES = {
    "jinja2": J2Pages,
}
