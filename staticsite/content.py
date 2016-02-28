# coding: utf-8
import logging

log = logging.getLogger()


class Base:
    def __init__(self, page, lineno):
        self.page = page
        self.lineno = lineno

    @property
    def is_blank(self):
        return False


class Line(Base):
    def __init__(self, page, lineno, line):
        super().__init__(page, lineno)
        self.line = line

    @property
    def is_blank(self):
        return not self.line or self.line.isspace()


class CodeBegin(Base):
    def __init__(self, page, lineno, lang):
        super().__init__(page, lineno)
        self.lang = lang


class CodeEnd(Base):
    pass


class IkiwikiMap(Base):
    def __init__(self, page, lineno, content):
        super().__init__(page, lineno)
        self.content = content


class Text(Base):
    def __init__(self, page, lineno, text):
        super().__init__(page, lineno)
        self.text = text

    @property
    def is_blank(self):
        return self.text.isspace()


class EOL(Base):
    @property
    def is_blank(self):
        return True


class InternalLink(Base):
    def __init__(self, page, lineno, text, target):
        super().__init__(page, lineno)
        self.text = text
        self.target = self.page.resolve_link(target)
        if self.target is None:
            log.warn("%s:%d: link %s cannot be resolved to a known resource",
                     self.page.relpath, self.lineno, target)

class InlineImage(Base):
    def __init__(self, page, lineno, fname, alt):
        super().__init__(page, lineno)
        self.text = alt
        self.target = self.page.resolve_link(fname)
        if self.target is None:
            log.warn("%s:%d: image %s cannot be resolved to a known resource",
                     self.page.relpath, self.lineno, fname)


class Directive(Base):
    def __init__(self, page, lineno, content):
        super().__init__(page, lineno)
        self.content = content

