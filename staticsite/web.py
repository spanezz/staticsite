# coding: utf-8

from .core import BodyWriter, MarkdownPage
import json
import os
import re
import shutil
import logging

log = logging.getLogger()

class Webpage(BodyWriter):
    def generate_codebegin(self, el):
        self.chunks.append("```{lang}\n".format(lang=el.lang))

    def generate_codeend(self, el):
        self.chunks.append("```\n")

    def generate_ikiwikimap(self, el):
        self.chunks.append("[[!map {content}]]\n".format(content=el.content))

    def generate_inlineimage(self, el):
        if el.target is None:
            self.chunks.append("(missing image: {alt})".format(alt=el.text))
        else:
            path = os.path.relpath(el.target.relpath, os.path.dirname(el.page.relpath))
            self.chunks.append('[[!img {fname} alt="{alt}"]]'.format(fname=path, alt=el.text))

    def generate_internallink(self, el):
        if el.target is None:
            if el.text is None:
                log.warn("%s:%s: found link with no text and unresolved target", el.page.relpath, el.lineno)
            else:
                self.chunks.append(el.text)
        elif el.target.TYPE == "markdown":
            path = os.path.relpath(el.target.relpath_without_extension, os.path.dirname(el.page.relpath))
            if path.startswith("../"):
                path = el.target.relpath_without_extension
            if el.text is None or el.text == path:
                self.chunks.append('[[{target}]]'.format(target=path))
            else:
                self.chunks.append('[[{text}|{target}]]'.format(text=el.text, target=path))
        else:
            path = os.path.relpath(el.target.relpath, os.path.dirname(el.page.relpath))
            if path.startswith("../"):
                path = el.target.relpath
            if el.text is None:
                self.chunks.append('[[{target}]]'.format(target=path))
            else:
                self.chunks.append('[[{text}|{target}]]'.format(text=el.text, target=path))

    def generate_directive(self, el):
        super().generate_directive(el)
        self.chunks.append("[[{}]]".format(el.content))


class WebWriter:
    def __init__(self, root):
        # Root directory of the destination
        self.root = root

        # Markdown compiler
        from markdown import Markdown
        self.markdown = Markdown(
            extensions=["markdown.extensions.extra"],
            output_format="html5"
        )

        # Jinja2 compiler
        from jinja2 import Environment, FileSystemLoader
        self.jinja2 = Environment(
            loader=FileSystemLoader(os.path.join(self.root, "templates"))
        )

        self.page_template = self.jinja2.get_template("__page__.html")

    def write(self, site):
        outdir = os.path.join(self.root, "web")
        # Clear the target directory
        if os.path.exists(outdir):
            shutil.rmtree(outdir)

        # Copy static content
        staticroot = os.path.join(self.root, "static")
        if os.path.isdir(staticroot):
            shutil.copytree(staticroot, outdir)

        # Remove leading spaces from markdown content
        for page in site.pages.values():
            if page.TYPE != "markdown": continue
            while page.body and page.body[0].is_blank:
                page.body.pop(0)

        # Generate output
        for page in site.pages.values():
            getattr(self, "write_" + page.TYPE)(page)

        # Generate tag indices
        tags = set()
        tags.update(*(x.tags for x in site.pages.values()))
        for tag in tags:
            dst = os.path.join(self.root, "web", "tags", tag + ".mdwn")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wt") as out:
                desc = site.tag_descriptions.get(tag, None)
                if desc is None:
                    desc = [tag.capitalize() + "."]
                for line in desc:
                    print(line, file=out)
                print(file=out)
                print('[[!inline pages="link(tags/{tag})" show="10"]]'.format(tag=tag), file=out)

        # Generate index of tags
        dst = os.path.join(self.root, "web", "tags/index.mdwn")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wt") as out:
            print('[[!pagestats pages="tags/*"]]', file=out)
            print('[[!inline pages="tags/*"]]', file=out)

    def write_static(self, page):
        dst = os.path.join(self.root, "web", page.relpath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(page.site.root, page.orig_relpath), dst)

    def write_markdown(self, page):
        writer = Webpage()
        writer.read(page)
        if writer.is_empty():
            return

        dst = os.path.join(self.root, "web", page.relpath_without_extension + ".html")
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        with open(dst, "wt") as out:
            text = []
            if page.title is not None:
                text.append("# {title}\n".format(title=page.title))
            text += writer.chunks
            html = self.markdown.convert("".join(text))
            out.write(self.page_template.render(
                content=html,
                title=page.title,
                tags=sorted(page.tags),
            ))

#        for relpath in page.aliases:
#            dst = os.path.join(self.root, relpath)
#            os.makedirs(os.path.dirname(dst), exist_ok=True)
#            with open(dst, "wt") as out:
#                print('[[!meta redir="{relpath}"]]'.format(relpath=page.relpath_without_extension), file=out)

