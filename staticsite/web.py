# coding: utf-8

import json
import os
import re
import shutil
import logging

log = logging.getLogger()

#class Webpage(BodyWriter):
#    def generate_codebegin(self, el):
#        self.chunks.append("```{lang}\n".format(lang=el.lang))
#
#    def generate_codeend(self, el):
#        self.chunks.append("```\n")
#
#    def generate_ikiwikimap(self, el):
#        self.chunks.append("[[!map {content}]]\n".format(content=el.content))
#
#    def generate_inlineimage(self, el):
#        if el.target is None:
#            self.chunks.append("(missing image: {alt})".format(alt=el.text))
#        else:
#            path = os.path.relpath(el.target.relpath, os.path.dirname(el.page.relpath))
#            self.chunks.append('[[!img {fname} alt="{alt}"]]'.format(fname=path, alt=el.text))
#
#    def generate_internallink(self, el):
#        if el.target is None:
#            if el.text is None:
#                log.warn("%s:%s: found link with no text and unresolved target", el.page.relpath, el.lineno)
#            else:
#                self.chunks.append(el.text)
#        elif el.target.TYPE == "markdown":
#            path = os.path.relpath(el.target.relpath_without_extension, os.path.dirname(el.page.relpath))
#            if path.startswith("../"):
#                path = el.target.relpath_without_extension
#            if el.text is None or el.text == path:
#                self.chunks.append('[[{target}]]'.format(target=path))
#            else:
#                self.chunks.append('[[{text}|{target}]]'.format(text=el.text, target=path))
#        else:
#            path = os.path.relpath(el.target.relpath, os.path.dirname(el.page.relpath))
#            if path.startswith("../"):
#                path = el.target.relpath
#            if el.text is None:
#                self.chunks.append('[[{target}]]'.format(target=path))
#            else:
#                self.chunks.append('[[{text}|{target}]]'.format(text=el.text, target=path))
#
#    def generate_directive(self, el):
#        super().generate_directive(el)
#        self.chunks.append("[[{}]]".format(el.content))


class WebWriter:
    def __init__(self, root):
        # Root directory of the destination
        self.root = root

    def clear_outdir(self, outdir):
        for f in os.listdir(outdir):
            abs = os.path.join(outdir, f)
            if os.path.isdir(abs):
                shutil.rmtree(abs)
            else:
                os.unlink(abs)

    def write(self, site):
        # Clear the target directory, but keep the root path so that a web
        # server running on it does not find itself running nowhere
        outdir = os.path.join(self.root, "web")
        if os.path.exists(outdir):
            self.clear_outdir(outdir)

        ## Remove leading spaces from markdown content
        #for page in site.pages.values():
        #    if page.TYPE != "markdown": continue
        #    while page.body and page.body[0].is_blank:
        #        page.body.pop(0)

        # Generate output
        for page in site.pages.values():
            page.write(self)

        ## Generate tag indices
        #for taxonomy in site.taxonomies.items():
        #    # Render index
        #    try:
        #        template = self.jinja2.get_template(taxonomy.index_template)
        #    except:
        #        log.exception("taxonomy %s: cannot load template %s", taxonomy.name, taxonomy.index_template)
        #        continue

        #    for val in taxonomy.values:
        #        kwargs = {
        #            taxonomy.name: taxonomy,
        #            taxonomy.item_name:
        #        }
        #        rendered = template.render(

        #        dst_relpath = os.path.join(taxonomy.output_dir, taxonomy.index_template)
        #        dst = self.output_abspath(dst_relpath)
        #        with open(dst, "wt") as out:
        #            out.write(self.page_template.render(
        #                content=html,
        #                **page.meta,
        #            ))

        #            new_page = J2Page(self.site, os.path.join(dirname, new_basename), self.template_relpath)
        #            new_page.meta["taxonomy_name"] = metaname
        #            new_page.meta["taxonomy_item"] = e
        #            new_page.meta["taxonomy_slug"] = slug
        #            new_page.meta["pages"] = sorted(pages.get(e, ()), key=lambda x:x.meta.get("date", None), reverse=True)
        #            self.site.pages[new_page.src_relpath] = new_page

        #            # Mark this as taxonomy index
        #            if ext == ".html":


        #for tag in tags:
        #    dst = os.path.join(self.root, "web", "tags", tag + ".mdwn")
        #    os.makedirs(os.path.dirname(dst), exist_ok=True)
        #    with open(dst, "wt") as out:
        #        desc = site.tag_descriptions.get(tag, None)
        #        if desc is None:
        #            desc = [tag.capitalize() + "."]
        #        for line in desc:
        #            print(line, file=out)
        #        print(file=out)
        #        print('[[!inline pages="link(tags/{tag})" show="10"]]'.format(tag=tag), file=out)


        #def transform(self):
        #    basename = os.path.basename(self.src_relpath)
        #    mo = re_metaname.match(basename)
        #    if not mo:
        #        return

        #    metaname = mo.group("name")
        #    ext = mo.group("ext")

        #    # We are a metapage: remove ourself from the site and add instead the
        #    # resolved versions
        #    dirname = os.path.dirname(self.src_relpath)
        #    del self.site.pages[self.src_relpath]

        #    # Resolve the file name into a taxonomy
        #    elements = self.site.taxonomies.get(metaname, None)
        #    if elements is None:
        #        log.warn("%s: taxonomy %s not found", self.src_relpath, metaname)
        #        return

        #    # Get the pages for each taxonomy value
        #    pages = defaultdict(list)
        #    for p in self.site.pages.values():
        #        vals = p.meta.get(metaname, None)
        #        if vals is None: continue
        #        for v in vals:
        #            pages[v].append(p)

        #    # Generate new J2Page elements for each expansion
        #    for e in elements:
        #        slug = self.site.slugify(e)
        #        new_basename = slug + ext
        #        new_page = J2Page(self.site, os.path.join(dirname, new_basename), self.template_relpath)
        #        new_page.meta["taxonomy_name"] = metaname
        #        new_page.meta["taxonomy_item"] = e
        #        new_page.meta["taxonomy_slug"] = slug
        #        new_page.meta["pages"] = sorted(pages.get(e, ()), key=lambda x:x.meta.get("date", None), reverse=True)
        #        self.site.pages[new_page.src_relpath] = new_page

        #        # Mark this as taxonomy index
        #        if ext == ".html":
        #            self.site.taxonomy_indices[metaname][e] = new_page



        ## Generate index of tags
        #dst = os.path.join(self.root, "web", "tags/index.mdwn")
        #os.makedirs(os.path.dirname(dst), exist_ok=True)
        #with open(dst, "wt") as out:
        #    print('[[!pagestats pages="tags/*"]]', file=out)
        #    print('[[!inline pages="tags/*"]]', file=out)

    def output_abspath(self, relpath):
        abspath = os.path.join(self.root, "web", relpath)
        os.makedirs(os.path.dirname(abspath), exist_ok=True)
        return abspath

