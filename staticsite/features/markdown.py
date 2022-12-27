from __future__ import annotations

import io
import logging
import os
import re
from typing import TYPE_CHECKING, Any, BinaryIO, List, Optional, Type

import jinja2
import markdown
import markupsafe
from markdown.util import AMP_SUBSTITUTE

from staticsite.archetypes import Archetype
from staticsite.feature import Feature
from staticsite.markup import MarkupFeature, MarkupPage
from staticsite.node import Path
from staticsite.page import (FrontMatterPage, Page, PageNotFoundError,
                             TemplatePage)
from staticsite.utils import front_matter

if TYPE_CHECKING:
    from staticsite import file, fstree
    from staticsite.node import Node

log = logging.getLogger("markdown")


class FixURLs(markdown.treeprocessors.Treeprocessor):
    """
    Markdown Treeprocessor that fixes internal links in HTML tags
    """
    def __init__(self, *args, link_resolver, **kw) -> None:
        super().__init__(*args, **kw)
        self.link_resolver = link_resolver

    def should_resolve(self, url: str) -> bool:
        if url.startswith(AMP_SUBSTITUTE):
            # Possibly an overencoded mailto: link.
            # see https://bugs.debian.org/816218
            #
            # Markdown then further escapes & with utils.AMP_SUBSTITUTE, so
            # we look for it here.
            return False
        return True

    def run(self, root):
        # Replace <a href=…>
        for a in root.iter("a"):
            if (orig_url := a.attrib.get("href", None)) is None:
                continue

            if not self.should_resolve(orig_url):
                continue

            page, new_url = self.link_resolver.resolve_url(orig_url)
            if new_url is not None:
                a.attrib["href"] = new_url

        # Replace <img src=…>
        for img in root.iter("img"):
            if (orig_url := img.attrib.get("src", None)) is None:
                continue

            if not self.should_resolve(orig_url):
                continue

            page, parsed = self.link_resolver.resolve_page(orig_url)
            if page is None:
                continue

            try:
                attrs = self.link_resolver.page.get_img_attributes(page, absolute=self.link_resolver.absolute)
            except PageNotFoundError as e:
                log.warn("%s: %s", self.page, e)
                continue

            img.attrib.update(attrs)


class StaticSiteExtension(markdown.extensions.Extension):
    def __init__(self, *, link_resolver, **kwargs):
        super().__init__(**kwargs)
        self.link_resolver = link_resolver

    def extendMarkdown(self, md):
        md.treeprocessors.register(FixURLs(md, link_resolver=self.link_resolver), 'staticsite', 0)
        md.registerExtension(self)

    def reset(self):
        pass

    def set_page(self, page: Page, absolute: bool):
        self.link_resolver.set_page(page, absolute)


class MarkdownPages(MarkupFeature, Feature):
    """
    Render ``.md`` markdown pages, with front matter.

    See doc/reference/markdown.md for details.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.markdown = markdown.Markdown(
            extensions=self.site.settings.MARKDOWN_EXTENSIONS + [
                StaticSiteExtension(link_resolver=self.link_resolver),
            ],
            extension_configs=self.site.settings.MARKDOWN_EXTENSION_CONFIGS,
            output_format="html5",
        )

        self.j2_filters["markdown"] = self.jinja2_markdown

        self.render_cache = self.site.caches.get("markdown")

    def get_used_page_types(self) -> list[Type[Page]]:
        return [MarkdownPage]

    @jinja2.pass_context
    def jinja2_markdown(self, context, mdtext):
        return markupsafe.Markup(self.render_snippet(context.parent["page"], mdtext))

    def render_snippet(self, page: Page, content: str) -> str:
        """
        Render markdown in the context of the given page.

        It renders the page content by default, unless `content` is set to a
        different markdown string.
        """
        if content is None:
            content = page.get_content()
        self.link_resolver.set_page(page, absolute=False)
        self.markdown.reset()
        return self.markdown.convert(content)

    def load_dir(
            self,
            node: Node,
            directory: fstree.Tree,
            files: dict[str, tuple[dict[str, Any], file.File]]) -> list[Page]:
        taken: List[str] = []
        pages: List[Page] = []
        for fname, (kwargs, src) in files.items():
            if not fname.endswith(".md"):
                continue
            taken.append(fname)

            try:
                fm_meta, body = self.load_file_meta(directory, fname)
            except Exception as e:
                log.warn("%s: Failed to parse markdown page front matter (%s): skipped", src, e)
                log.debug("%s: Failed to parse markdown page front matter: skipped", src, exc_info=e)
                continue

            kwargs.update(fm_meta)

            if (directory_index := fname in ("index.md", "README.md")):
                path = Path()
            else:
                path = Path((fname[:-3],))

            # print("CREAT", fname, directory_index)
            page = node.create_source_page(
                    page_cls=MarkdownPage,
                    src=src,
                    feature=self,
                    front_matter=fm_meta,
                    body=body,
                    directory_index=directory_index,
                    path=path,
                    **kwargs)
            pages.append(page)

        for fname in taken:
            del files[fname]

        return pages

    def load_dir_meta(self, directory: fstree.Tree) -> Optional[dict[str, Any]]:
        # Load front matter from index.md
        # Do not try to load front matter from README.md, as one wouldn't
        # clutter a repo README with staticsite front matter
        if (src := directory.files.get("index.md")) is None:
            return None

        try:
            meta, body = self.load_file_meta(directory, "index.md")
        except Exception as e:
            log.debug("%s: failed to parse front matter", src.relpath, exc_info=e)
            log.warn("%s: failed to parse front matter", src.relpath)
        else:
            return meta

        return None

    def load_file_meta(self, directory: fstree.Tree, fname: str) -> tuple[dict[str, Any], list[str]]:
        """
        Load metadata for a file.

        Returns the metadata and the markdown lines for the rest of the file
        """
        # Read the contents

        # Parse separating front matter and markdown content
        with directory.open(fname, "rb") as fd:
            return self.read_file_meta(fd)

    def read_file_meta(self, fd: BinaryIO) -> tuple[dict[str, Any], list[str]]:
        """
        Load metadata for a file.

        Returns the metadata and the markdown lines for the rest of the file
        """
        fmt, meta, body = front_matter.read_markdown_partial(fd)

        body = list(body)

        # Remove leading empty lines
        while body and not body[0]:
            body.pop(0)

        # Read title from first # title if not specified in metadata
        if not meta.get("title", ""):
            if body and body[0].startswith("# "):
                meta["title"] = body.pop(0)[2:].strip()

            # Remove leading empty lines again
            while body and not body[0]:
                body.pop(0)

        return meta, body

    def try_load_archetype(self, archetypes, relpath, name):
        if os.path.basename(relpath) != name + ".md":
            return None
        return MarkdownArchetype(archetypes, relpath, self)


class MarkdownArchetype(Archetype):
    def __init__(self, archetypes, relpath, feature):
        super().__init__(archetypes, relpath)
        self.feature = feature

    def render(self, **kw):
        meta, rendered = super().render(**kw)

        # Reparse the rendered version
        with io.BytesIO(rendered.encode()) as fd:
            # Reparse it separating front matter and markdown content
            try:
                style, meta, body = front_matter.read_markdown_partial(fd)
            except Exception as e:
                log.debug("archetype %s: failed to parse front matter", self.relpath, exc_info=e)
                log.warn("archetype %s: failed to parse front matter", self.relpath)
                return

            # Make a copy of the full parsed metadata
            archetype_meta = dict(meta)

            # Remove the path entry
            meta.pop("path", None)

            # Reserialize the page with the edited metadata
            fmatter = front_matter.write(meta, style)
            with io.StringIO() as fd:
                fd.write(fmatter)
                print(file=fd)
                for line in body:
                    print(line, file=fd)
                post_body = fd.getvalue()

        return archetype_meta, post_body


class MarkdownPage(TemplatePage, MarkupPage, FrontMatterPage):
    """
    Markdown sources

    Markdown files have a `.md` extension and are prefixed by
    [front matter metadata](../front-matter.md).

    The flavour of markdown is what's supported by
    [python-markdown](http://pythonhosted.org/Markdown/) with the
    [Extra](http://pythonhosted.org/Markdown/extensions/extra.html),
    [CodeHilite](http://pythonhosted.org/Markdown/extensions/code_hilite.html)
    and [Fenced Code Blocks](http://pythonhosted.org/Markdown/extensions/fenced_code_blocks.html)
    extensions, and is quite close to
    [GitHub Flavored Markdown](https://github.github.com/gfm/) or
    [GitLab Markdown](https://docs.gitlab.com/ee/user/markdown.html).

    `staticsite` adds an extra internal plugin to Python-Markdown to postprocess
    the page contents to adjust internal links to guarantee that they point where
    they should.

    Adding a horizontal rule *using underscores* (3 or more underscores), creates a
    page fold. When rendering the page inline, such as in a blog index page, or in
    RSS/Atom syndication, the content from the horizontal rule onwards will not be
    shown.

    If you want to add a horizontal rule without introducing a page fold, use a
    sequence of three or more asterisks (`***`) or dashes (`---`) instead.


    ## Linking to other pages

    Pages can link to other pages via normal Markdown links (`[text](link)`).

    Links that start with a `/` will be rooted at the top of the site contents.

    Relative links are resolved relative to the location of the current page first,
    and failing that relative to its parent directory, and so on until the root of
    the site.

    For example, if you have `blog/2016/page.md` that contains a link like
    `![a photo](images/photo.jpg)`, the link will point to the first of this
    options that will be found:

    1. `blog/2016/images/photo.jpg`
    2. `blog/images/photo.jpg`
    3. `images/photo.jpg`

    This allows one to organise pages pointing to other pages or assets without needing
    to worry about where they are located in the site.

    You can link to other Markdown pages with the `.md` extension
    ([like GitHub does](https://help.github.com/articles/relative-links-in-readmes/))
    or without, as if you were editing a wiki.

    ## Page metadata

    The front matter of the post can be written in
    [TOML](https://github.com/toml-lang/toml),
    [YAML](https://en.wikipedia.org/wiki/YAML) or
    [JSON](https://en.wikipedia.org/wiki/JSON), just like in
    [Hugo](https://gohugo.io/content/front-matter/).

    Use `---` delimiters to mark YAML front matter. Use `+++` delimiters to mark
    TOML front matter. Use `{`…`}` delimiters to mark JSON front matter.

    You can also usea [triple-backticks code blocks](https://python-markdown.github.io/extensions/fenced_code_blocks/)
    first thing in the file to mark front matter, optionally specifying `yaml`,
    `toml`, or `json` as the format (yaml is used as a default):

    ~~~~{.markdown}
    ```yaml
    date: 2020-01-02 12:00
    ```
    # My page
    ~~~~

    If you want to start your markdown content with a code block, add an empty line
    at the top: front matter detection only happens on the first line of the file.

    See [page metadata](../metadata.md) for a list of commonly used metadata.


    ## Extra settings

    Markdown rendering makes use of these settings:

    ### `MARKDOWN_EXTENSIONS`

    Extensions used by python-markdown. Defaults to:

    ```py
    MARKDOWN_EXTENSIONS = [
        "markdown.extensions.extra",
        "markdown.extensions.codehilite",
        "markdown.extensions.fenced_code",
    ]
    ```

    ### `MARKDOWN_EXTENSION_CONFIGS`

    Configuration for markdown extensions. Defaults to:

    ```py
    MARKDOWN_EXTENSION_CONFIGS = {
        'markdown.extensions.extra': {
            'markdown.extensions.footnotes': {
                # See https://github.com/spanezz/staticsite/issues/13
                'UNIQUE_IDS': True,
            },
        },
    }
    ```

    ## Rendering markdown pages

    Besides the usual `meta`, markdown pages have also these attributes:

    * `page.contents`: the Markdown contents rendered as HTML. You may want to use
      it with the [`|safe` filter](https://jinja.palletsprojects.com/en/2.10.x/templates/#safe)
      to prevent double escaping
    """
    TYPE = "markdown"

    # Match a Markdown divider line
    re_divider = re.compile(r"^____+$")

    def __init__(self, *, feature: MarkdownPages, body: List[str], **kw):
        # Indexed by default
        kw.setdefault("indexed", True)
        super().__init__(**kw)

        # Shared markdown environment
        self.feature = feature

        # Sequence of lines found in the body before the divider line, if any
        self.body_start: list[str]

        # Sequence of lines found in the body including and after the divider
        # line, nor None if there is no divider line
        self.body_rest: Optional[list[str]]

        # True if this page can render a short version of itself
        self.content_has_split = False

        # External links found when rendering the page
        self.rendered_external_links: set[str] = set()

        # Split lead and rest of the post, if a divider line is present
        for idx, line in enumerate(body):
            if self.re_divider.match(line):
                self.content_has_split = True
                self.body_start = body[:idx]
                self.body_rest = body[idx:]
                break
        else:
            self.content_has_split = False
            self.body_start = body
            self.body_rest = None

    def front_matter_changed(self, fd: BinaryIO) -> bool:
        """
        Check if the front matter read from fd is different from ours
        """
        # TODO: refactor read_file_meta to skip reading the body if we don't
        # need it, but still parse until the title if the front matter doesn't
        # have one
        meta, body = self.feature.read_file_meta(fd)
        return self.front_matter != meta

    def check(self, checker):
        self.render()

    def render_page(self, body: List[str], render_type: str, absolute: bool = False) -> str:
        """
        Render markdown in the context of the given page.
        """
        self.feature.link_resolver.set_page(self, absolute)
        cache_key = f"{render_type}:{self.src.relpath}"

        with self.markup_render_context(cache_key) as context:
            if (paths := context.cache.get("paths")) is not None:
                # If the destination of links has changed, drop the cached version.
                # This will as a side effect prime the link resolver cache,
                # avoiding links from being looked up again during rendering
                for src, dest in paths:
                    if self.link_resolver.resolve_page(src)[0].site_path != dest:
                        context.reset_cache()
                        break
            if (rendered := context.cache.get("rendered")):
                # log.info("%s: markdown cache hit", page.src.relpath)
                return rendered

            self.feature.markdown.reset()
            rendered = self.feature.markdown.convert("\n".join(body))

            self.rendered_external_links.update(self.feature.link_resolver.external_links)

            context.cache["rendered"] = rendered
            context.cache["paths"] = list(self.feature.link_resolver.substituted.items())

        return rendered

    @jinja2.pass_context
    def html_body(self, context, **kw) -> str:
        absolute = self != context["page"]
        if self.content_has_split:
            body = self.body_start + ["", "<a name='sep'></a>", ""] + self.body_rest
            return self.render_page(body, render_type="hb", absolute=absolute)
        else:
            return self.render_page(self.body_start, render_type="s", absolute=absolute)

    @jinja2.pass_context
    def html_inline(self, context, **kw) -> str:
        absolute = self != context["page"]
        if self.content_has_split:
            body = self.body_start + ["", f"[(continue reading)](/{self.src.relpath})"]
            return self.render_page(body, render_type="h", absolute=absolute)
        else:
            return self.render_page(self.body_start, render_type="s", absolute=absolute)

    @jinja2.pass_context
    def html_feed(self, context, **kw) -> str:
        absolute = self != context["page"]
        if self.content_has_split:
            body = self.body_start + [""] + self.body_rest
            return self.render_page(body, render_type="f", absolute=absolute)
        else:
            return self.render_page(self.body_start, render_type="f", absolute=absolute)


FEATURES = {
    "md": MarkdownPages,
}
