# coding: utf-8

from .core import BodyWriter
import os
import shutil
import json
import logging

log = logging.getLogger()

class BodyDumper(BodyWriter):
    def print(self, *args):
        parts = [str(self.lineno)]
        parts.extend(str(x) for x in args)
        self.output.append(" ".join(parts))

    def line_code_begin(self, lang, **kw):
        self.print("code_begin", lang)

    def line_code_end(self, **kw):
        self.print("code_end")

    def line_include_map(self, **kw):
        self.print("map", self.line)

    def line_text(self, **kw):
        self.print("line", self.line)

    def line_multi(self, parts, **kw):
        self.print("multi", self.line)
        for name, kw in parts:
            getattr(self, name)(**kw)

    def part_img(self, fname, alt, **kw):
        self.print("  img", fname, alt)

    def part_internal_link(self, text, target, **kw):
        self.print("  internal_link", target, text)

    def part_text(self, text):
        self.print("  text", text)

    def part_directive(self, text):
        self.print("  directive", text)


class DumpWriter:
    def __init__(self, root):
        self.root = root

    def write(self, site):
        for page in site.pages.values():
            self.write_page(site.root, page)

        for static in site.static.values():
            self.write_static(site.root, static)

    def write_static(self, src_root, static):
        dst = os.path.join(self.root, static.relpath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(src_root, static.relpath), dst)

    def write_page(self, src_root, page):
        writer = BodyDumper(page)
        page.parse_body(writer)
        if writer.is_empty():
            return

        dst = os.path.join(self.root, page.relpath + ".md")
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        meta = {}
        if page.title is not None:
            meta["title"] = page.title
        if page.tags:
            meta["tags"] = sorted(page.tags)
        if page.date is not None:
            meta["date"] = page.date.strftime("%Y-%m-%d")

        with open(dst, "wt") as out:
            json.dump(meta, out, indent=2)
            out.write("\n")
            writer.write(out)


