# coding: utf-8

from .core import Page
import re
import os
import pytz
import datetime
import markdown
from urllib.parse import urlparse, urlunparse
import logging

log = logging.getLogger()

class LinkResolver(markdown.treeprocessors.Treeprocessor):
    def run(self, root):
        from markdown.util import AMP_SUBSTITUTE

        for a in root.iter("a"):
            url = a.attrib.get("href", None)
            if not url: continue
            if url.startswith(AMP_SUBSTITUTE):
                # Possibly an overencoded mailto: link.
                # see https://bugs.debian.org/816218
                #
                # Markdown then further escapes & with utils.AMP_SUBSTITUTE, so
                # we look for it here.
                continue
            parsed = urlparse(url)
            if parsed.scheme or parsed.netloc: continue
            if not parsed.path: continue
            dest = self.page.resolve_link(parsed.path)
            if dest is None:
                log.warn("%s: internal link %r does not resolve to any site page", self.page.src_relpath, url)
            else:
                a.attrib["href"] = urlunparse(
                    (parsed.scheme, parsed.netloc, dest.dst_relpath, parsed.params, parsed.query, parsed.fragment)
                )


class StaticSiteExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md, md_globals):
        self.link_resolver = LinkResolver(md)
        # Insert instance of 'mypattern' before 'references' pattern
        md.treeprocessors.add('staticsite', self.link_resolver, '_end')
        md.registerExtension(self)

    def reset(self):
        pass

    def set_page(self, page):
        self.page = page
        self.link_resolver.page = page


class MarkdownPage(Page):
    TYPE = "markdown"

    def __init__(self, site, relpath):
        super().__init__(site, relpath)

        # Sequence of lines found in the front matter
        self.front_matter = []

        # Sequence of lines found in the body
        self.body = []

#        # Rules used to match metadata lines
#        self.meta_line_rules = [
#            (re.compile(r"^#\s*(?P<title>.+)"), self.parse_title),
#            (re.compile(r"^\[\[!tag (?P<tags>[^\]]+)\]\]"), self.parse_tags),
#            (re.compile(r'^\[\[!meta date="(?P<date>[^"]+)"\]\]'), self.parse_date),
#        ]
#
#        # Rules used to match whole lines
#        self.body_line_rules = [
#            (re.compile(r'^\[\[!format (?P<lang>\S+) """'), content.CodeBegin),
#            (re.compile(r"^\[\[!format (?P<lang>\S+) '''"), content.CodeBegin),
#            (re.compile(r'^"""\]\]'), content.CodeEnd),
#            (re.compile(r"^'''\]\]"), content.CodeEnd),
#            (re.compile(r"^\[\[!map\s+(?P<content>.+)]]\s*$"), content.IkiwikiMap),
#        ]
#
#        # Rules used to parse directives
#        self.body_directive_rules = [
#            (re.compile(r'!img (?P<fname>\S+) alt="(?P<alt>[^"]+)"'), content.InlineImage),
#            (re.compile(r"(?P<text>[^|]+)\|(?P<target>[^\]]+)"), content.InternalLink),
#        ]

    def get_content(self):
        return "\n".join(self.body)

    def analyze(self):
        # Read the contents
        src = os.path.join(self.site.root, self.src_relpath + ".md")
        if self.meta.get("date", None) is None:
            self.meta["date"] = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(src)))

        # Parse separating front matter and markdown content
        with open(src, "rt") as fd:
            front_matter_end = None
            in_front_matter = True

            for lineno, line in enumerate(fd, 1):
                line = line.rstrip()
                if lineno == 1:
                    if line == "{":
                        front_matter_end = "}"
                    elif line == "---":
                        front_matter_end = "---"
                    elif line == "+++":
                        front_matter_end = "+++"
                    else:
                        in_front_matter = False

                if in_front_matter:
                    self.front_matter.append(line)
                    if lineno > 1 and line == front_matter_end:
                        in_front_matter = False
                else:
                    self.body.append(line)

        self.parse_front_matter(self.front_matter)

        # Remove leading empty lines
        while self.body and not self.body[0]:
            self.body.pop(0)

        # Read title from first # title if not specified in metadata
        if not self.meta.get("title", ""):
            if self.body and self.body[0].startswith("# "):
                self.meta["title"] = self.body[0][2:].strip()

    def parse_front_matter(self, lines):
        if not lines: return
        if lines[0] == "{":
            # JSON
            import json
            parsed = json.loads("\n".join(lines))
            self.meta.update(**parsed)
        elif lines[0] == "+++":
            # TOML
            import toml
            parsed = toml.loads("\n".join(lines))
        elif lines[0] == "---":
            # YAML
            import yaml
            parsed = yaml.load("\n".join(lines), Loader=yaml.CLoader)
        else:
            parsed = {}
        self.meta.update(**parsed)

    def resolve_link_title(self, target_relpath):
        # Resolve mising text from target page title
        dest_page = self.site.pages.get(target_relpath, None)
        if dest_page is not None:
            return dest_page.title
        else:
            return None

#    def parse_title(self, lineno, line, title, **kw):
#        if self.title is None:
#            self.title = title
#            # Discard the main title
#            return None
#        else:
#            return line
#
#    def parse_tags(self, lineno, line, tags, **kw):
#        for t in tags.split():
#            if t.startswith("tags/"):
#                t = t[5:]
#            self.tags.add(t)
#        # Line is discarded
#        return None
#
#    def parse_date(self, lineno, line, date, **kw):
#        import dateutil
#        from dateutil.parser import parse
#        self.date = dateutil.parser.parse(date)
#        if self.date.tzinfo is None:
#            self.date = tz_local.localize(self.date)
#        return None
#
#    def parse_body(self, fd):
#        for lineno, line in enumerate(fd, 1):
#            line = line.rstrip()
#
#            # Search entire body lines for whole-line metadata directives
#            for regex, func in self.meta_line_rules:
#                mo = regex.match(line)
#                if mo:
#                    line = func(lineno, line, **mo.groupdict())
#                    break
#
#            if line is not None:
#                self.parse_line(lineno, line)
#
#    def parse_line(self, lineno, line):
#        # Search entire body lines for whole-line directives
#        for regex, func in self.body_line_rules:
#            mo = regex.match(line)
#            if mo:
#                self.body.append(func(self, lineno, **mo.groupdict()))
#                return
#
#        # Split the line looking for ikiwiki directives
#        re_directive = re.compile(r"\[\[([^\]]+)\]\]")
#        parts = re_directive.split(line)
#        if len(parts) == 1:
#            self.body.append(content.Line(self, lineno, line))
#            return
#
#        res = []
#        for idx, p in enumerate(parts):
#            if idx % 2 == 0:
#                self.body.append(content.Text(self, lineno, p))
#            else:
#                self.parse_body_directive(lineno, p)
#        self.body.append(content.EOL(self, lineno))
#
#    def parse_body_directive(self, lineno, text):
#        for regex, func in self.body_directive_rules:
#            mo = regex.match(text)
#            if mo:
#                self.body.append(func(self, lineno, **mo.groupdict()))
#                return
#
#        # Just target names in [[..]] resolve as links
#        target_relpath = self.resolve_link_relpath(text)
#        if target_relpath is not None:
#            self.body.append(content.InternalLink(self, lineno, text=None, target=text))
#            return
#
#        self.body.append(content.Directive(self, lineno, text))

    @classmethod
    def try_create(cls, site, relpath):
        if not relpath.endswith(".md"): return None
        return cls(site, relpath[:-3])

