import os
import logging
import jinja2
from urllib.parse import urlparse, urlunparse

log = logging.getLogger()


class Page:
    """
    A source page in the site.

    This can be a static asset, a file to be rendered, a taxonomy, a
    directory listing, or anything else.

    All pages have a number of members to describe their behaviour in the site:

    `site`:
        the Site that contains the page
    `src`:
        the File object with informationm about the source file
    `src_linkpath`:
        the path used by other pages to link to this page, when referencing its
        source. For example, blog/2016/example.md is linked as
        blog/2016/example.
    `dst_relpath`:
        relative path of the file that will be generated for this page when it
        gets rendered.
        FIXME: now that a resource can generate multiple files, this is not
        really needed.
    `dst_link`:
        absolute path in the site namespace used to link to this page in
        webpages.
        FIXME: now that a resource can generate multiple files, this is not
        really needed.
    `meta`:
        a dictionary with the page metadata. See the README for documentation
        about its contents.
    """
    # In what pass must pages of this type be analyzed.
    ANALYZE_PASS = 1

    # True if the page can be found when search site contents
    FINDABLE = False

    # Preferred order of rendering, not for functional purposes for for
    # purposes of collecting reasonable timings. This can be used for example
    # to render markdown pages before taxonomies, so that the time of rendering
    # markdown is counted as such and not as time needed for rendering
    # taxonomies.
    RENDER_PREFERRED_ORDER = 1

    def __init__(self, site, src, src_linkpath, dst_relpath, dst_link):
        self.site = site
        self.src = src
        self.src_linkpath = src_linkpath
        self.dst_relpath = dst_relpath
        self.dst_link = dst_link
        self.meta = {}
        log.debug("%s: new page, src_link: %s", self.src.relpath, src_linkpath)

    @property
    def date_as_iso8601(self):
        from dateutil.tz import tzlocal
        ts = self.meta.get("date", None)
        if ts is None:
            return None
        # TODO: Take timezone from config instead of tzlocal()
        tz = tzlocal()
        ts = ts.astimezone(tz)
        offset = tz.utcoffset(ts)
        offset_sec = (offset.days * 24 * 3600 + offset.seconds)
        offset_hrs = offset_sec // 3600
        offset_min = offset_sec % 3600
        if offset:
            tz_str = '{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
        else:
            tz_str = 'Z'
        return ts.strftime("%Y-%m-%d %H:%M:%S") + tz_str

    def resolve_link(self, target):
        dirname, basename = os.path.split(target)
        if basename == "index.html":
            # log.debug("%s: resolve %s using %s", self.src.relpath, target, dirname)
            target = dirname
        # else:
            # log.debug("%s: resolve %s using %s", self.src.relpath, target, target)

        # Absolute URLs are resolved as is
        if target.startswith("/"):
            if target == "/":
                target_relpath = ""
            else:
                target_relpath = os.path.normpath(target.lstrip("/"))
            # log.debug("%s: resolve absolute path using %s", self.src.relpath, target_relpath)
            return self.site.pages.get(target_relpath, None)

        root = os.path.dirname(self.src.relpath)
        while True:
            target_relpath = os.path.normpath(os.path.join(root, target))
            if target_relpath == ".":
                target_relpath = ""
            res = self.site.pages.get(target_relpath, None)
            if res is not None:
                return res
            if not root or root == "/":
                return None
            root = os.path.dirname(root)

    def resolve_url(self, url):
        """
        Resolve internal URLs.

        Returns None if the URL does not need changing, else returns the new URL.
        """
        from markdown.util import AMP_SUBSTITUTE
        if not url:
            return None
        if url.startswith(AMP_SUBSTITUTE):
            # Possibly an overencoded mailto: link.
            # see https://bugs.debian.org/816218
            #
            # Markdown then further escapes & with utils.AMP_SUBSTITUTE, so
            # we look for it here.
            return None
        parsed = urlparse(url)
        if parsed.scheme or parsed.netloc:
            return None
        if not parsed.path:
            return None
        dest = self.resolve_link(parsed.path)
        if dest is None:
            # If resolving the full path failed, try resolving without extension
            pos = parsed.path.rfind(".")
            if pos == -1:
                return None

            # Treat .md and .rst as strippable extensions
            # TODO: deprecate this function and always link to full source
            #       paths with extension instead
            # TODO: have features provide this list instead of hardcoding it
            ext = parsed.path[pos:]
            if ext not in (".md", ".rst"):
                return None

            dirname, basename = os.path.split(parsed.path)
            # TODO: also generate this list from features
            if basename in ("index.md", "README.md", "index.rst", "README.rst"):
                dest = self.resolve_link(dirname)
            else:
                dest = self.resolve_link(parsed.path[:-len(ext)])
        if dest is None:
            log.warn("%s: internal link %r does not resolve to any site page", self.src.relpath, url)
            return None

        return urlunparse(
            (parsed.scheme, parsed.netloc, dest.dst_link, parsed.params, parsed.query, parsed.fragment)
        )

    def check(self, checker):
        pass

    def target_relpaths(self):
        return [self.dst_relpath]

    def __str__(self):
        return self.src.relpath

    def __repr__(self):
        return "{}:{}".format(self.TYPE, self.src.relpath)

    def render_template(self, template, **kwargs):
        """
        Render a jinja2 template, logging things if something goes wrong
        """
        try:
            return template.render(**kwargs)
        except jinja2.TemplateError as e:
            log.error("%s: failed to render %s: %s", template.filename, self.src.relpath, e)
            log.debug("%s: failed to render %s: %s", template.filename, self.src.relpath, e, exc_info=True)
            # TODO: return a "render error" page? But that risks silent errors
            return None
