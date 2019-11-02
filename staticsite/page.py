import os
import logging

log = logging.getLogger()


class Page:
    """
    A source page in the site.

    This can be a static asset, a file to be rendered, a taxonomy, a
    directory listing, or anything else.

    All pages have a number of members to describe their behaviour in the site:

    `site`:
        the Site that contains the page
    `root_abspath`:
        the absolute path of the root of the directory tree under which the
        page was found. This is where src_relpath is rooted.
    `src_relpath`:
        the relative path under `root_abspath` for the source file of the page
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

    def __init__(self, site, root_abspath, src_relpath, src_linkpath, dst_relpath, dst_link):
        self.site = site
        self.root_abspath = root_abspath
        self.src_relpath = src_relpath
        self.src_linkpath = src_linkpath
        self.dst_relpath = dst_relpath
        self.dst_link = dst_link
        self.meta = {}
        log.debug("%s: new page, src_link: %s", src_relpath, src_linkpath)

    @property
    def src_abspath(self):
        return os.path.join(self.root_abspath, self.src_relpath)

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
            # log.debug("%s: resolve %s using %s", self.src_relpath, target, dirname)
            target = dirname
        # else:
            # log.debug("%s: resolve %s using %s", self.src_relpath, target, target)

        # Absolute URLs are resolved as is
        if target.startswith("/"):
            if target == "/":
                target_relpath = ""
            else:
                target_relpath = os.path.normpath(target.lstrip("/"))
            # log.debug("%s: resolve absolute path using %s", self.src_relpath, target_relpath)
            return self.site.pages.get(target_relpath, None)

        root = os.path.dirname(self.src_relpath)
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

    def read_metadata(self):
        """
        Fill in self.meta scanning the page contents
        """
        # Assign page to its taxonomies
        taxonomy_series = []
        for taxonomy in self.site.taxonomies:
            vals = self.meta.get(taxonomy.name, None)
            if not vals:
                continue
            taxonomy_series_names = taxonomy.add_page(self, vals)
            # Allow a taxonomy to auto-define a series
            for taxonomy_series_name in taxonomy_series_names:
                if taxonomy_series_name is not None and (
                        not taxonomy_series or taxonomy_series_name != taxonomy_series[0]):
                    taxonomy_series.append(taxonomy_series_name)

        # If the page is part of a series, take note of it
        series_name = self.meta.get("series", None)
        if series_name is None:
            if not taxonomy_series:
                pass
            elif len(taxonomy_series) == 1:
                series_name = taxonomy_series[0]
            else:
                log.warn(
                    "%s: %d series defined via taxonomies (%s) but only one can be used;"
                    " I cannot choose, so I'll use none. Use the 'series' metadata to choose which one",
                    self.src_relpath, len(taxonomy_series), ", ".join(taxonomy_series))

        # Assign page to its series
        if series_name is not None:
            self.meta["series"] = series_name
            self.site.features["series"].add_page(self, series_name)

    def check(self, checker):
        pass

    def target_relpaths(self):
        return [self.dst_relpath]

    def __str__(self):
        return self.src_relpath

    def __repr__(self):
        return "{}:{}".format(self.TYPE, self.src_relpath)
