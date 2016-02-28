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

class Ctimes:
    def __init__(self, fname):
        self.by_relpath = {}
        for fname, ctime in self.parse(fname):
            self.by_relpath[fname] = ctime

    def parse(self, fname):
        with open(fname, "rt") as fd:
            data = json.load(fd)
            for fname, info in data.items():
                yield fname, info["ctime"]


class Page:
    def __init__(self, site, relpath, ctime=None):
        # Site that owns this page
        self.site = site

        # Relative path of the page, with the markdown extension
        self.relpath = relpath

        # Original path of the page, before relocation
        self.orig_relpath = relpath

        # Page date
        if ctime is not None:
            self.date = pytz.utc.localize(datetime.datetime.utcfromtimestamp(ctime))
        else:
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

    def scan(self):
        pass


class MarkdownPage(Page):
    TYPE = "markdown"

    def __init__(self, site, relpath, ctime=None):
        super().__init__(site, relpath, ctime)

        # Sequence of content.* objects from the parsed page contents
        self.body = []

        # Rules used to match metadata lines
        self.meta_line_rules = [
            (re.compile(r"^#\s*(?P<title>.+)"), self.parse_title),
            (re.compile(r"^\[\[!tag (?P<tags>[^\]]+)\]\]"), self.parse_tags),
            (re.compile(r'^\[\[!meta date="(?P<date>[^"]+)"\]\]'), self.parse_date),
        ]

        # Rules used to match whole lines
        self.body_line_rules = [
            (re.compile(r'^\[\[!format (?P<lang>\S+) """'), content.CodeBegin),
            (re.compile(r"^\[\[!format (?P<lang>\S+) '''"), content.CodeBegin),
            (re.compile(r'^"""\]\]'), content.CodeEnd),
            (re.compile(r"^'''\]\]"), content.CodeEnd),
            (re.compile(r"^\[\[!map\s+(?P<content>.+)]]\s*$"), content.IkiwikiMap),
        ]

        # Rules used to parse directives
        self.body_directive_rules = [
            (re.compile(r'!img (?P<fname>\S+) alt="(?P<alt>[^"]+)"'), content.InlineImage),
            (re.compile(r"(?P<text>[^|]+)\|(?P<target>[^\]]+)"), content.InternalLink),
        ]

    def scan(self):
        # Read the contents
        src = os.path.join(self.site.root, self.relpath)
        if self.date is None:
            self.date = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(src)))
        with open(src, "rt") as fd:
            self.parse_body(fd)

    def resolve_link_title(self, target_relpath):
        # Resolve mising text from target page title
        dest_page = self.site.pages.get(target_relpath, None)
        if dest_page is not None:
            return dest_page.title
        else:
            return None

    def parse_title(self, lineno, line, title, **kw):
        if self.title is None:
            self.title = title
            # Discard the main title
            return None
        else:
            return line

    def parse_tags(self, lineno, line, tags, **kw):
        for t in tags.split():
            if t.startswith("tags/"):
                t = t[5:]
            self.tags.add(t)
        # Line is discarded
        return None

    def parse_date(self, lineno, line, date, **kw):
        import dateutil
        from dateutil.parser import parse
        self.date = dateutil.parser.parse(date)
        if self.date.tzinfo is None:
            self.date = tz_local.localize(self.date)
        return None

    def parse_body(self, fd):
        for lineno, line in enumerate(fd, 1):
            line = line.rstrip()

            # Search entire body lines for whole-line metadata directives
            for regex, func in self.meta_line_rules:
                mo = regex.match(line)
                if mo:
                    line = func(lineno, line, **mo.groupdict())
                    break

            if line is not None:
                self.parse_line(lineno, line)

    def parse_line(self, lineno, line):
        # Search entire body lines for whole-line directives
        for regex, func in self.body_line_rules:
            mo = regex.match(line)
            if mo:
                self.body.append(func(self, lineno, **mo.groupdict()))
                return

        # Split the line looking for ikiwiki directives
        re_directive = re.compile(r"\[\[([^\]]+)\]\]")
        parts = re_directive.split(line)
        if len(parts) == 1:
            self.body.append(content.Line(self, lineno, line))
            return

        res = []
        for idx, p in enumerate(parts):
            if idx % 2 == 0:
                self.body.append(content.Text(self, lineno, p))
            else:
                self.parse_body_directive(lineno, p)
        self.body.append(content.EOL(self, lineno))

    def parse_body_directive(self, lineno, text):
        for regex, func in self.body_directive_rules:
            mo = regex.match(text)
            if mo:
                self.body.append(func(self, lineno, **mo.groupdict()))
                return

        # Just target names in [[..]] resolve as links
        target_relpath = self.resolve_link_relpath(text)
        if target_relpath is not None:
            self.body.append(content.InternalLink(self, lineno, text=None, target=text))
            return

        self.body.append(content.Directive(self, lineno, text))


class AliasPage(Page):
    TYPE = "alias"

    def __init__(self, site, relpath, ctime, dest):
        super().__init__(site, relpath, ctime)
        self.dest = dest


class StaticFile(Page):
    TYPE = "static"

    def __init__(self, site, relpath, ctime):
        super().__init__(site, relpath, ctime)
        self.title = os.path.basename(relpath)


class Site:
    def __init__(self, root):
        self.root = root

        # Extra ctime information
        self.ctimes = None

        # Site pages
        self.pages = {}

        # Pages that only redirect to other pages
        self.alias_pages = {}

        # Description of tags
        self.tag_descriptions = {}

    def load_extrainfo(self, pathname):
        self.ctimes = Ctimes(pathname)

    def read_years(self):
        for d in os.listdir(self.root):
            if not re.match(r"^\d{4}$", d): continue
            self.read_tree(d)

    def read_blog(self):
        blogroot = os.path.join(self.root, "blog")
        for d in os.listdir(blogroot):
            if not re.match(r"^\d{4}$", d): continue
            self.read_tree(os.path.join("blog", d))

    def read_talks(self):
        talks_dir = os.path.join(self.root, "talks")
        if not os.path.isdir(talks_dir): return
        self.read_tree("talks")

    def read_tree(self, relpath):
        log.info("Loading directory %s", relpath)
        abspath = os.path.join(self.root, relpath)
        for f in os.listdir(abspath):
            absf = os.path.join(abspath, f)
            if os.path.isdir(absf):
                self.read_tree(os.path.join(relpath, f))
            elif f.endswith(".mdwn"):
                self.read_page(os.path.join(relpath, f))
            elif os.path.isfile(absf):
                self.read_static(os.path.join(relpath, f))

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
        log.info("Loading page %s", relpath)
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

    def read_static(self, relpath):
        log.info("Loading static file %s", relpath)
        static = self._instantiate(StaticFile, relpath)
        self.pages[relpath] = static

    def relocate(self, page, dest_relpath):
        log.info("Relocating %s to %s", page.relpath, dest_relpath)
        if dest_relpath in self.pages:
            log.warn("Cannot relocate %s to existing page %s", page.relpath, dest_relpath)
            return
        self.pages[dest_relpath] = page
        page.aliases.append(page.relpath)
        page.relpath = dest_relpath

    def scan(self):
        # Remove alias pages from self.pages, adding them instead as aliases to
        # the Page they refer to
        for p in self.alias_pages.values():
            dest_relpath = p.resolve_link_relpath(p.dest)
            dest = self.pages.get(dest_relpath, None)
            if dest is None:
                log.warn("%s: redirects to missing page %s", p.relpath, p.dest)
            else:
                dest.aliases.append(p.relpath)

        for page in self.pages.values():
            page.scan()


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
