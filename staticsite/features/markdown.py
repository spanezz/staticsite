from __future__ import annotations
from typing import List, Tuple, Optional, Dict, Set
from staticsite import Page, Feature
from staticsite.page import PageNotFoundError
from staticsite.utils import front_matter
from staticsite.archetypes import Archetype
from staticsite.contents import ContentDir
from staticsite.utils.typing import Meta
from urllib.parse import urlparse, urlunparse
import jinja2
import re
import os
import io
import markdown
import logging

log = logging.getLogger("markdown")


class LinkResolver(markdown.treeprocessors.Treeprocessor):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.page: Optional[Page] = None
        self.absolute: bool = False
        self.substituted: Dict[str, str] = {}
        self.external_links: Set[str] = set()

    def set_page(self, page, absolute=False):
        self.page = page
        self.absolute = absolute
        self.substituted = {}
        self.external_links = set()

    def run(self, root):
        for a in root.iter("a"):
            page, new_url = self.resolve_url(a.attrib.get("href", None))
            if new_url is not None:
                a.attrib["href"] = new_url

        for img in root.iter("img"):
            orig_url = img.attrib.get("src", None)
            if orig_url is None:
                continue

            page, parsed = self.resolve_page(orig_url)
            if page is None:
                continue

            try:
                attrs = self.page.get_img_attributes(page, absolute=self.absolute)
            except PageNotFoundError as e:
                log.warn("%s: %s", self.page, e)
                continue

            img.attrib.update(attrs)

    def resolve_page(self, url) -> Tuple[Page, Tuple]:
        from markdown.util import AMP_SUBSTITUTE
        if url.startswith(AMP_SUBSTITUTE):
            # Possibly an overencoded mailto: link.
            # see https://bugs.debian.org/816218
            #
            # Markdown then further escapes & with utils.AMP_SUBSTITUTE, so
            # we look for it here.
            return None, None

        parsed = urlparse(url)

        # If it's an absolute url, leave it unchanged
        if parsed.scheme or parsed.netloc:
            self.external_links.add(url)
            return None, url

            return None, parsed

        # If it's an anchor inside the page, leave it unchanged
        if not parsed.path:
            return None, parsed

        # Try with cache
        site_path = self.substituted.get(parsed.path)
        if site_path is not None:
            try:
                return self.page.site.pages[site_path], parsed
            except KeyError:
                log.warn("%s: url %s resolved via cache to %s which does not exist in the site. Cache out of date?",
                         self.page, url, site_path)

        # Resolve as a path
        try:
            page = self.page.resolve_path(parsed.path)
        except PageNotFoundError as e:
            log.warn("%s: %s", self.page, e)
            return None, parsed

        # Cache the page site_path
        self.substituted[url] = page.meta["site_path"]

        return page, parsed

    def resolve_url(self, url) -> Tuple[Page, str]:
        """
        Resolve internal URLs.

        Returns None if the URL does not need changing, else returns the new URL.
        """
        page, parsed = self.resolve_page(url)
        if page is None:
            return page, url

        new_url = self.page.url_for(page, absolute=self.absolute)
        dest = urlparse(new_url)

        return page, urlunparse(
            (dest.scheme, dest.netloc, dest.path,
             parsed.params, parsed.query, parsed.fragment)
        )


class StaticSiteExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md, md_globals):
        self.link_resolver = LinkResolver(md)
        # Insert instance of 'mypattern' before 'references' pattern
        md.treeprocessors.add('staticsite', self.link_resolver, '_end')
        md.registerExtension(self)

    def reset(self):
        pass

    def set_page(self, page: Page, absolute: bool):
        self.link_resolver.set_page(page, absolute)


class MarkdownPages(Feature):
    """
    Render ``.md`` markdown pages, with front matter.

    See doc/reference/markdown.md for details.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        md_staticsite = StaticSiteExtension()
        self.markdown = markdown.Markdown(
            extensions=self.site.settings.MARKDOWN_EXTENSIONS + [
                md_staticsite,
            ],
            extension_configs=self.site.settings.MARKDOWN_EXTENSION_CONFIGS,
            output_format="html5",
        )
        self.link_resolver = md_staticsite.link_resolver

        self.j2_filters["markdown"] = self.jinja2_markdown

        self.render_cache = self.site.caches.get("markdown")

    @jinja2.contextfilter
    def jinja2_markdown(self, context, mdtext):
        return jinja2.Markup(self.render_snippet(context.parent["page"], mdtext))

    def render_page(self, page: Page, body: List[str], render_type: str, absolute: bool = False):
        """
        Render markdown in the context of the given page.
        """
        self.link_resolver.set_page(page, absolute)

        cache_key = f"{render_type}:{page.src.relpath}"

        # Try fetching rendered content from cache
        cached = self.render_cache.get(cache_key)
        if cached and cached["mtime"] != page.src.stat.st_mtime:
            # If the source has changed, drop the cached version
            cached = None
        if cached:
            # If the destination of links has changed, drop the cached version.
            # This will as a side effect prime the link resolver cache,
            # avoiding links from being looked up again during rendering
            for src, dest in cached["paths"]:
                if self.link_resolver.resolve_url(src) != dest:
                    cached = None
                    break
        if cached:
            # log.info("%s: markdown cache hit", page.src.relpath)
            return cached["rendered"]

        self.markdown.reset()
        rendered = self.markdown.convert("\n".join(body))

        rendered = self.site.metadata.on_contents_rendered(
                page, rendered,
                render_type=render_type,
                external_links=self.link_resolver.external_links)

        self.render_cache.put(cache_key, {
            "mtime": page.src.stat.st_mtime,
            "rendered": rendered,
            "paths": list(self.link_resolver.substituted.items()),
        })

        return rendered

    def render_snippet(self, page, content):
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

    def load_dir(self, sitedir: ContentDir) -> List[Page]:
        taken: List[str] = []
        pages: List[Page] = []
        for fname, src in sitedir.files.items():
            if not fname.endswith(".md"):
                continue
            taken.append(fname)

            meta = sitedir.meta_file(fname)
            if fname not in ("index.md", "README.md"):
                meta["site_path"] = os.path.join(sitedir.meta["site_path"], fname[:-3])
            else:
                meta["site_path"] = sitedir.meta["site_path"]

            try:
                fm_meta, body = self.load_file_meta(sitedir, src, fname)
            except Exception as e:
                log.warn("%s: Failed to parse markdown page front matter (%s): skipped", src, e)
                log.debug("%s: Failed to parse markdown page front matter: skipped", src, exc_info=e)
                continue

            meta.update(fm_meta)

            page = MarkdownPage(self.site, src, meta=meta, dir=sitedir, feature=self, body=body)
            pages.append(page)

        for fname in taken:
            del sitedir.files[fname]

        return pages

    def load_dir_meta(self, sitedir: ContentDir):
        # Load front matter from index.md
        # Do not try to load front matter from README.md, as one wouldn't
        # clutter a repo README with staticsite front matter
        src = sitedir.files.get("index.md")
        if src is None:
            return

        try:
            meta, body = self.load_file_meta(sitedir, src, "index.md")
        except Exception as e:
            log.debug("%s: failed to parse front matter", src.relpath, exc_info=e)
            log.warn("%s: failed to parse front matter", src.relpath)
        else:
            return meta

    def load_file_meta(self, sitedir, src, fname) -> Tuple[Meta, List[str]]:
        """
        Load metadata for a file.

        Returns the metadata and the markdown lines for the rest of the file
        """
        # Read the contents

        # Parse separating front matter and markdown content
        with sitedir.open(fname, src, "rb") as fd:
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
    def __init__(self, archetypes, relpath, mdpages):
        super().__init__(archetypes, relpath)
        self.mdpages = mdpages

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


class MarkdownPage(Page):
    TYPE = "markdown"

    # Match a Markdown divider line
    re_divider = re.compile(r"^____+$")

    def __init__(self, *args, feature: MarkdownPages, body: List[str], **kw):
        super().__init__(*args, **kw)

        self.meta["build_path"] = os.path.join(self.meta["site_path"], "index.html")

        # Indexed by default
        self.meta.setdefault("indexed", True)

        # Shared markdown environment
        self.mdpages = feature

        # Sequence of lines found in the body before the divider line, if any
        self.body_start: List[str]

        # Sequence of lines found in the body including and after the divider
        # line, nor None if there is no divider line
        self.body_rest: Optional[List[str]]

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

    def check(self, checker):
        self.render()

    @jinja2.contextfunction
    def html_body(self, context, **kw) -> str:
        absolute = self != context["page"]
        if self.content_has_split:
            body = self.body_start + ["", "<a name='sep'></a>", ""] + self.body_rest
            return self.mdpages.render_page(self, body, render_type="hb", absolute=absolute)
        else:
            return self.mdpages.render_page(self, self.body_start, render_type="s", absolute=absolute)

    @jinja2.contextfunction
    def html_inline(self, context, **kw) -> str:
        absolute = self != context["page"]
        if self.content_has_split:
            body = self.body_start + ["", f"[(continue reading)](/{self.src.relpath})"]
            return self.mdpages.render_page(self, body, render_type="h", absolute=absolute)
        else:
            return self.mdpages.render_page(self, self.body_start, render_type="s", absolute=absolute)

    @jinja2.contextfunction
    def html_feed(self, context, **kw) -> str:
        absolute = self != context["page"]
        if self.content_has_split:
            body = self.body_start + [""] + self.body_rest
            return self.mdpages.render_page(self, body, render_type="f", absolute=absolute)
        else:
            return self.mdpages.render_page(self, self.body_start, render_type="f", absolute=absolute)


FEATURES = {
    "md": MarkdownPages,
}
