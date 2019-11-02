from staticsite.core import Archetype, RenderedString
from staticsite.page import Page
from staticsite.feature import Feature
import pytz
import dateutil.parser
import jinja2
import re
import os
import io
import datetime
from collections import defaultdict
import logging

log = logging.getLogger()


re_ext = re.compile(r"\.(json|toml|yaml)$")


class DataPages(Feature):
    def __init__(self, site):
        super().__init__(site)
        self.by_type = defaultdict(list)
        self.j2_globals["data_pages"] = self.jinja2_data_pages
        self.page_class_by_type = {}

    def register_page_class(self, type: str, cls):
        self.page_class_by_type[type] = cls

    def try_load_page(self, root_abspath, relpath):
        mo = re_ext.search(relpath)
        if not mo:
            return None
        data = load_data(os.path.join(root_abspath, relpath), relpath, mo.group(1))
        if data is None:
            return None
        type = data.get("type", None)
        if type is None:
            log.error("%s: data type not found: ignoring page", relpath)
            return None
        cls = self.page_class_by_type.get(type, DataPage)
        page = cls(self.site, root_abspath, relpath, data)
        data_type = page.meta.get("type")
        self.by_type[data_type].append(page)
        return page

    def try_load_archetype(self, archetypes, relpath, name):
        mo = re_ext.search(relpath)
        if not mo:
            return None
        # return DataArchetype(self, archetypes, relpath)
        return None

    def finalize(self):
        for type, pages in self.by_type.items():
            pages.sort(key=lambda x: x.meta["date"])

    @jinja2.contextfunction
    def jinja2_data_pages(self, context, type, path=None, limit=None, sort=None, **kw):
        from .theme import PageFilter
        page_filter = PageFilter(self.site, path=path, limit=limit, sort=sort, **kw)
        return page_filter.filter(self.by_type.get(type, []))


def load_data(abspath, relpath, fmt):
    if fmt == "json":
        import json
        with open(abspath, "rt") as fd:
            try:
                return json.load(fd)
            except Exception:
                log.exception("%s: failed to parse %s content", relpath, fmt)
                return
    elif fmt == "toml":
        import toml
        with open(abspath, "rt") as fd:
            try:
                return toml.load(fd)
            except Exception:
                log.exception("%s: failed to parse %s content", relpath, fmt)
                return
    elif fmt == "yaml":
        import yaml
        with open(abspath, "rt") as fd:
            try:
                return yaml.load(fd, Loader=yaml.CLoader)
            except Exception:
                log.exception("%s: failed to parse %s content", relpath, fmt)
                return
    else:
        log.error("%s: unsupported format: %s", relpath, fmt)
        return


class DataPage(Page):
    TYPE = "data"
    FINDABLE = True

    def __init__(self, site, root_abspath, relpath, data):
        dirname, basename = os.path.split(relpath)
        if basename.startswith("index.") or basename.startswith("README."):
            linkpath = dirname
        else:
            linkpath = os.path.splitext(relpath)[0]
        super().__init__(
            site=site,
            root_abspath=root_abspath,
            src_relpath=relpath,
            src_linkpath=linkpath,
            dst_relpath=os.path.join(linkpath, "index.html"),
            dst_link=os.path.join(site.settings.SITE_ROOT, linkpath))

        # Read and parse the contents
        src = self.src_abspath
        if src is None:
            if self.meta.get("date", None) is None:
                self.meta["date"] = self.site.generation_time
        else:
            if self.meta.get("date", None) is None:
                self.meta["date"] = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(src)))

        self.meta.update(data)
        self.data = data

        date = self.meta.get("date", None)
        if date is not None and not isinstance(date, datetime.datetime):
            self.meta["date"] = dateutil.parser.parse(date)

        self._content = None

    @property
    def content(self):
        if self._content is None:
            data_type = self.meta.get("type")
            template = None

            if data_type is not None:
                template_name = "data-" + data_type + ".html"
                try:
                    template = self.site.theme.jinja2.get_template(template_name)
                except jinja2.TemplateNotFound:
                    pass
                except Exception:
                    log.exception("%s: cannot load template %s", self.src_relpath, template_name)
                    return "cannot load template {}".format(template_name)

            if template is None:
                # Fallback to data.html
                try:
                    template = self.site.theme.jinja2.get_template("data.html")
                except Exception:
                    log.exception("%s: cannot load template", self.src_relpath)
                    return "cannot load template data.html"

            self._content = template.render(
                page=self,
                data=self.data,
            )

        return self._content

    def render(self):
        res = {}

        page_template = self.site.theme.jinja2.get_template("page.html")
        html = page_template.render(
            page=self,
            content=self.content,
            **self.meta
        )
        res[self.dst_relpath] = RenderedString(html)

        aliases = self.meta.get("aliases", ())
        if aliases:
            redirect_template = self.site.theme.jinja2.get_template("redirect.html")
            for relpath in aliases:
                html = redirect_template.render(
                    page=self,
                )
                res[os.path.join(relpath, "index.html")] = RenderedString(html)

        return res

    def target_relpaths(self):
        res = [self.dst_relpath]
        for relpath in self.meta.get("aliases", ()):
            res.append(os.path.join(relpath, "index.html"))
        return res


#class DataArchetype(Archetype):
#    def __init__(self, data_pages, archetypes, relpath):
#        super().__init__(data_pages.site, relpath)
#        self.archetypes = archetypes
#
#    def render(self, **kw):
#        """
#        Process the archetype returning its parsed front matter in a dict, and
#        its contents in a string
#        """
#        # Render the archetype with jinja2
#        abspath = os.path.join(self.archetypes.root, self.relpath)
#        with open(abspath, "rt") as fd:
#            template = self.site.theme.jinja2.from_string(fd.read())
#
#        rendered = template.render(**kw)
#
#        with io.StringIO(rendered) as fd:
#            data = load_data(
#            # Reparse it separating front matter and markdown content
#            front_matter, body = parse_markdown_with_front_matter(fd)
#
#            try:
#                style, meta = parse_front_matter(front_matter)
#            except Exception:
#                log.exception("archetype %s: failed to parse front matter", self.relpath)
#
#        return style, meta, body
