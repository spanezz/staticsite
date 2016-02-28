# coding: utf-8
import os
import re
import datetime
import json
import logging
import pytz
from . import content

log = logging.getLogger()

tz_local = pytz.timezone("Europe/Rome")

class Page:
    def __init__(self, site, relpath):
        # Site that owns this page
        self.site = site

        # Relative path of the page, with the markdown extension
        self.relpath = relpath

        # Original path of the page, before relocation
        self.orig_relpath = relpath

        # Page creation date
        self.date = None

        # Page title
        self.title = None

        # Page tags
        self.tags = set()

        # Alternative relpaths for this page
        self.aliases = []

    @property
    def date_as_iso8601(self):
        from dateutil.tz import tzlocal
        tz = tzlocal()
        ts = self.date.astimezone(tz)
        offset = tz.utcoffset(ts)
        offset_sec = (offset.days * 24 * 3600 + offset.seconds)
        offset_hrs = offset_sec // 3600
        offset_min = offset_sec % 3600
        if offset:
            tz_str = '{0:+03d}:{1:02d}'.format(offset_hrs, offset_min // 60)
        else:
            tz_str = 'Z'
        return ts.strftime("%Y-%m-%d %H:%M:%S") + tz_str

    @property
    def relpath_without_extension(self):
        return os.path.splitext(self.relpath)[0]

    def resolve_link(self, target):
        target_relpath = self.resolve_link_relpath(target)
        target_page = self.site.pages.get(target_relpath, None)
        return target_page

    def resolve_link_relpath(self, target):
        target = target.lstrip("/")
        root = self.relpath_without_extension
        while True:
            target_relpath = os.path.join(root, target)
            abspath = os.path.join(self.site.root, target_relpath)
            if os.path.exists(abspath + ".mdwn"):
                return target_relpath + ".mdwn"
            if os.path.exists(abspath):
                return target_relpath
            if not root or root == "/":
                return None
            root = os.path.dirname(root)

    def analyze(self):
        pass


class Site:
    def __init__(self, root):
        self.root = root

        # Extra ctime information
        self.ctimes = None

        # Site pages
        self.pages = {}

        # Description of tags
        self.tag_descriptions = {}

        # Map input file patterns to resource handlers
        from .markdown import MarkdownContent
        #from .jinja2 import Jinja2Page
        self.page_handlers = [
            MarkdownContent(),
        ]

    def read_tree(self, relpath=None):
        from .asset import Asset

        if relpath is None:
            log.info("Loading site directory %s", self.root)
            abspath = os.path.join(self.root)
        else:
            log.debug("Loading directory %s", relpath)
            abspath = os.path.join(self.root, relpath)
        for f in os.listdir(abspath):
            if relpath is None:
                page_relpath = f
            else:
                page_relpath = os.path.join(relpath, f)

            absf = os.path.join(self.root, page_relpath)
            if os.path.isdir(absf):
                self.read_tree(page_relpath)
                continue

            for handler in self.page_handlers:
                p = handler.try_create(self, page_relpath)
                if p is not None:
                    self.pages[page_relpath] = p
                    break
            else:
                if os.path.isfile(absf):
                    log.debug("Loading static file %s", page_relpath)
                    self.pages[page_relpath] = Asset(self, page_relpath)

    def read_tag_descriptions(self, relpath):
        log.info("Loading tag info from %s", relpath)
        abspath = os.path.join(self.root, relpath)
        for f in os.listdir(abspath):
            # Skip tag index
            if f == "index.mdwn": continue
            if not f.endswith(".mdwn"): continue
            desc = []
            tag = os.path.splitext(f)[0]
            with open(os.path.join(abspath, f), "rt") as fd:
                for line in fd:
                    line = line.rstrip()
                    if line.startswith("[[!"):
                        if re.match(r'\[\[!inline pages="link\(tags/{tag}\)" show="\d+"\]\]'.format(tag=tag), line): continue
                        log.warn("%s: found unsupported tag lookup: %s", os.path.join(relpath, f), line)
                    else:
                        desc.append(line)

            # Strip leading and trailing empty lines
            while desc and not desc[0]:
                desc.pop(0)
            while desc and not desc[-1]:
                desc.pop(-1)
            self.tag_descriptions[tag] = desc

    def _instantiate(self, Resource, relpath, *args, **kw):
        if self.ctimes is not None:
            ctime = self.ctimes.by_relpath.get(relpath, None)
        else:
            ctime = None
        return Resource(self, relpath, ctime, *args, **kw)

    def read_page(self, relpath):
        log.debug("Loading page %s", relpath)
        with open(os.path.join(self.root, relpath), "rt") as fd:
            content = fd.read().strip()
        # Catch alias pages
        mo = re.match(r'\[\[!meta redir="(?P<relpath>[^"]+)"\]\]', content)
        if mo:
            page = self._instantiate(AliasPage, relpath, mo.group("relpath"))
            self.alias_pages[relpath] = page
        else:
            page = self._instantiate(MarkdownPage, relpath)
            self.pages[relpath] = page

    def relocate(self, page, dest_relpath):
        log.info("Relocating %s to %s", page.relpath, dest_relpath)
        if dest_relpath in self.pages:
            log.warn("Cannot relocate %s to existing page %s", page.relpath, dest_relpath)
            return
        self.pages[dest_relpath] = page
        page.aliases.append(page.relpath)
        page.relpath = dest_relpath

    def analyze(self):
        for page in self.pages.values():
            page.analyze()


class BodyWriter:
    def __init__(self):
        self.chunks = []

    def write(self, out):
        out.write("".join(self.chunks))

    def is_empty(self):
        for chunk in self.chunks:
            if not chunk.isspace():
                return False
        return True

    def read(self, page):
        for el in page.body:
            getattr(self, "generate_" + el.__class__.__name__.lower())(el)

    def generate_line(self, el):
        self.chunks.append(el.line + "\n")

    def generate_codebegin(self, el):
        pass

    def generate_codeend(self, el):
        pass

    def generate_ikiwikimap(self, el):
        if el.lineno != 1:
            log.warn("%s:%s: found map tag not in first line", el.page.relpath, el.lineno)

    def generate_text(self, el):
        self.chunks.append(el.text)

    def generate_eol(self, el):
        self.chunks.append("\n")

    def generate_internallink(self, el):
        pass

    def generate_inlineimage(self, el):
        pass

    def generate_directive(self, el):
        log.warn("%s:%s: found unsupported custom tag [[%s]]", el.page.relpath, el.lineno, el.content)
