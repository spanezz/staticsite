from __future__ import annotations

import io
import logging
import os
import re
from typing import IO, TYPE_CHECKING, Any, BinaryIO, List, Optional, Type, cast

import jinja2
import markdown
import markdown.treeprocessors
import markupsafe
from markdown.util import AMP_SUBSTITUTE

from staticsite.archetypes import Archetype
from staticsite.feature import Feature
from staticsite.markup import MarkupFeature, MarkupPage
from staticsite.page import FrontMatterPage, ImagePage, Page, TemplatePage
from staticsite.utils import front_matter

if TYPE_CHECKING:
    import xml.etree.ElementTree as ET

    from staticsite import file, fstree
    from staticsite.archetypes import Archetypes
    from staticsite.markup import LinkResolver
    from staticsite.source_node import SourcePageNode

log = logging.getLogger("markdown")


class FixURLs(markdown.treeprocessors.Treeprocessor):
    """
    Markdown Treeprocessor that fixes internal links in HTML tags
    """
    def __init__(self, *args: Any, link_resolver: LinkResolver, **kw: Any) -> None:
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

    def run(self, root: ET.ElementTree) -> None:
        # Replace <a href=…>
        for a in root.iter("a"):
            if (orig_url := a.attrib.get("href", None)) is None:
                continue

            if not self.should_resolve(orig_url):
                continue

            new_url = self.link_resolver.resolve_url(orig_url)
            if new_url is not None:
                a.attrib["href"] = new_url

        # Replace <img src=…>
        for img in root.iter("img"):
            if (orig_url := img.attrib.get("src", None)) is None:
                continue

            if not self.should_resolve(orig_url):
                continue

            if (resolved := self.link_resolver.resolve_page(orig_url)) is None:
                continue

            if isinstance(resolved.page, ImagePage):
                attrs = resolved.page.get_img_attributes(absolute=self.link_resolver.absolute)
            else:
                log.warning(
                        "%s: img src= resolves to %s which is not an image page",
                        self.link_resolver.page, resolved.page)
                continue

            img.attrib.update(attrs)


class StaticSiteExtension(markdown.extensions.Extension):
    def __init__(self, *, link_resolver: LinkResolver, **kwargs: Any):
        super().__init__(**kwargs)
        self.link_resolver = link_resolver

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        md.treeprocessors.register(FixURLs(md, link_resolver=self.link_resolver), 'staticsite', 0)
        md.registerExtension(self)

    def reset(self) -> None:
        pass

    def set_page(self, page: Page, absolute: bool) -> None:
        self.link_resolver.set_page(page, absolute)


class MarkdownPages(MarkupFeature, Feature):
    """
    Render ``.md`` markdown pages, with front matter.

    See doc/reference/markdown.md for details.
    """
    def __init__(self, *args: Any, **kw: Any):
        super().__init__(*args, **kw)
        self.markdown = markdown.Markdown(
            extensions=self.site.settings.MARKDOWN_EXTENSIONS + [
                StaticSiteExtension(link_resolver=self.link_resolver),
            ],
            extension_configs=self.site.settings.MARKDOWN_EXTENSION_CONFIGS,
            output_format="html",
        )

        self.j2_filters["markdown"] = self.jinja2_markdown

        self.render_cache = self.site.caches.get("markdown")

    def get_used_page_types(self) -> list[Type[Page]]:
        return [MarkdownPage]

    @jinja2.pass_context
    def jinja2_markdown(self, context: jinja2.runtime.Context, mdtext: str) -> str:
        return markupsafe.Markup(self.render_snippet(context.parent["page"], mdtext))

    def render_snippet(self, page: Page, content: str) -> str:
        """
        Render markdown in the context of the given page.

        It renders the page content by default, unless `content` is set to a
        different markdown string.
        """
        self.link_resolver.set_page(page, absolute=False)
        self.markdown.reset()
        return self.markdown.convert(content)

    def load_dir(
            self,
            node: SourcePageNode,
            directory: fstree.Tree,
            files: dict[str, tuple[dict[str, Any], file.File]]) -> list[Page]:
        taken: list[str] = []
        pages: list[Page] = []
        for fname, (kwargs, src) in files.items():
            if not fname.endswith(".md"):
                continue
            taken.append(fname)

            try:
                fm_meta, body = self.load_file_meta(directory, fname)
            except Exception as e:
                log.warning("%s: Failed to parse markdown page front matter (%s): skipped", src, e)
                log.debug("%s: Failed to parse markdown page front matter: skipped", src, exc_info=e)
                continue

            kwargs.update(fm_meta)
            kwargs["feature"] = self
            kwargs["src"] = src
            kwargs["page_cls"] = MarkdownPage
            kwargs["front_matter"] = fm_meta
            kwargs["body"] = body

            page: Optional[Page]
            if fname in ("index.md", "README.md"):
                page = node.create_source_page_as_index(**kwargs)
            else:
                page = node.create_source_page_as_path(
                        name=fname[:-3],
                        **kwargs)

            if page is not None:
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
            log.warning("%s: failed to parse front matter", src.relpath)
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

    def read_file_meta(self, fd: IO[bytes]) -> tuple[dict[str, Any], list[str]]:
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

    def try_load_archetype(self, archetypes: Archetypes, relpath: str, name: str) -> Optional[MarkdownArchetype]:
        if os.path.basename(relpath) != name + ".md":
            return None
        return MarkdownArchetype(archetypes, relpath, self)


class MarkdownArchetype(Archetype):
    def __init__(self, archetypes: Archetypes, relpath: str, feature: MarkdownPages):
        super().__init__(archetypes, relpath)
        self.feature = feature

    def render(self, **kw: Any) -> tuple[dict[str, Any], str]:
        meta, rendered = super().render(**kw)

        # Reparse the rendered version
        with io.BytesIO(rendered.encode()) as fd:
            # Reparse it separating front matter and markdown content
            try:
                style, meta, body = front_matter.read_markdown_partial(fd)
            except Exception as e:
                raise RuntimeError(f"archetype {self.relpath}: failed to parse front matter") from e

            if style is None:
                raise RuntimeError(f"archetype {self.relpath}: unrecognized style of front matter")

            # Make a copy of the full parsed metadata
            archetype_meta = dict(meta)

            # Remove the path entry
            meta.pop("path", None)

            # Reserialize the page with the edited metadata
            fmatter = front_matter.write(meta, style)
            with io.StringIO() as out:
                out.write(fmatter)
                print(file=out)
                for line in body:
                    print(line, file=out)
                post_body = out.getvalue()

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

    def __init__(self, *, body: List[str], **kw: Any):
        self.feature: MarkdownPages
        # Indexed by default
        kw.setdefault("indexed", True)
        super().__init__(**kw)

        # Sequence of lines found in the body before the divider line, if any
        self.body_start: list[str]

        # Sequence of lines found in the body including and after the divider
        # line, nor None if there is no divider line
        self.body_rest: Optional[list[str]]

        # External links found when rendering the page
        self.rendered_external_links: set[str] = set()

        # Split lead and rest of the post, if a divider line is present
        for idx, line in enumerate(body):
            if self.re_divider.match(line):
                self.body_start = body[:idx]
                self.body_rest = body[idx:]
                break
        else:
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

    def check(self) -> None:
        self.render()

    def _render_page(self, body: List[str], render_type: str, absolute: bool = False) -> str:
        """
        Render markdown in the context of the given page.
        """
        cache_key = f"{render_type}:{self.src.relpath}"

        with self.markup_render_context(cache_key, absolute=absolute) as context:
            if (rendered := context.cache.get("rendered")):
                # log.info("%s: markdown cache hit", page.src.relpath)
                return cast(str, rendered)

            self.feature.markdown.reset()
            rendered = self.feature.markdown.convert("\n".join(body))

            self.rendered_external_links.update(self.feature.link_resolver.external_links)

            context.cache["rendered"] = rendered

        return rendered

    @jinja2.pass_context
    def html_body(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        absolute = self != context["page"]
        if self.body_rest is not None:
            body = self.body_start + ["", "<a name='sep'></a>", ""] + self.body_rest
            return self._render_page(body, render_type="hb", absolute=absolute)
        else:
            return self._render_page(self.body_start, render_type="s", absolute=absolute)

    @jinja2.pass_context
    def html_inline(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        absolute = self != context["page"]
        if self.body_rest is not None:
            body = self.body_start + ["", f"[(continue reading)](/{self.src.relpath})"]
            return self._render_page(body, render_type="h", absolute=absolute)
        else:
            return self._render_page(self.body_start, render_type="s", absolute=absolute)

    @jinja2.pass_context
    def html_feed(self, context: jinja2.runtime.Context, **kw: Any) -> str:
        absolute = self != context["page"]
        if self.body_rest is not None:
            body = self.body_start + [""] + self.body_rest
            return self._render_page(body, render_type="f", absolute=absolute)
        else:
            return self._render_page(self.body_start, render_type="f", absolute=absolute)


FEATURES = {
    "md": MarkdownPages,
}
