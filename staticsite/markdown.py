# coding: utf-8

from .core import Page
import re
import os
import pytz
import datetime
import markdown

class MarkdownContent:
    def __init__(self):
        # Markdown parser
        self.parser = markdown.Markdown(
            extensions=[
                "markdown.extensions.extra",
                "markdown.extensions.codehilite",
                "markdown.extensions.fenced_code",
                "markdown.extensions.meta",
            ],
            output_format="html5"
        )

    def try_create(self, site, relpath):
        if not relpath.endswith(".md"): return None
        return MarkdownPage(self.parser, site, relpath)

class MarkdownPage(Page):
    TYPE = "markdown"

    def __init__(self, parser, site, relpath):
        super().__init__(site, relpath)

        self.markdown = parser

        # Sequence of content.* objects from the parsed page contents
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

        self.tree = None

    def get_content(self):
        src = os.path.join(self.site.root, self.orig_relpath)
        with open(src, "rt") as fd:
            return fd.read()

    def analyze(self):
        # Read the contents
        src = os.path.join(self.site.root, self.relpath)
        if self.date is None:
            self.date = pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(src)))
        #self.parser.reset()
        #with open(src, "rt") as fd:
        #    self.parser.convert(fd.read())
        #    #self.tree = self.parser.build_etree(fd.read())

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
