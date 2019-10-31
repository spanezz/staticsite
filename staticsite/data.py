from .core import Page, RenderedString
import pytz
import dateutil.parser
import jinja2
import re
import os
import datetime
from collections import defaultdict
import logging

log = logging.getLogger()


re_ext = re.compile(r"\.(json|toml|yaml)$")


class DataPages:
    def __init__(self, site):
        self.site = site
        self.by_type = defaultdict(list)

    def try_load_page(self, root_abspath, relpath):
        mo = re_ext.search(relpath)
        if not mo:
            return None
        page = DataPage(self.site, root_abspath, relpath, mo.group(1))
        data_type = page.meta.get("type")
        self.by_type[data_type].append(page)
        return page

    def finalize(self):
        for type, pages in self.by_type.items():
            pages.sort(key=lambda x: x.meta["date"])


class DataPage(Page):
    TYPE = "data"
    FINDABLE = True

    def __init__(self, site, root_abspath, relpath, fmt):
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
        if self.meta.get("date", None) is None:
            self.meta["date"] = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(src)))

        if fmt == "json":
            import json
            with open(src, "rt") as fd:
                try:
                    data = json.load(fd)
                except Exception:
                    log.exception("%s: failed to parse %s content", self.src_relpath, fmt)
                    return
        elif fmt == "toml":
            import toml
            with open(src, "rt") as fd:
                try:
                    data = toml.load(fd)
                except Exception:
                    log.exception("%s: failed to parse %s content", self.src_relpath, fmt)
                    return
        elif fmt == "yaml":
            import yaml
            with open(src, "rt") as fd:
                try:
                    data = yaml.load(fd, Loader=yaml.CLoader)
                except Exception:
                    log.exception("%s: failed to parse %s content", self.src_relpath, fmt)
                    return
        else:
            log.error("%s: unsupported format: %s", self.src_relpath, fmt)
            return

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
