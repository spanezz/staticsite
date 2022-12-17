# links: Collect links and link metadata from page metadata.

## Page types

* [links](../pages/links.md): Page with a link collection posted as metadata only.
* [links_index](../pages/links_index.md): Root page for the browseable archive of annotated external links in the
site

## Documentation

## Annotated external links

The Links feature allows to annotate external links with extra metadata, like
an abstract, tags, a URL with an archived version of the site, or other related
links.

You can add a `links` list to the metadata of the page, containing a dict for
each external link to annotate in the page.

See [metadata documentation](metadata.md) for a reference on the `links` field.

You can create a [data page](data.md) with a `links` list and a `data-type:
links` to have the data page render as a collection of links.


### Links metadata

This is the full list of supported links metadata:

* `url: str`: the link URL
* `archive: str`: URL to an archived version of the site
* `title: str`: short title for the link
* `abstract: str`: long description or abstract for the link
* `tags: List[str]`: tags for this link
* `related: List[Dict[str, str]]`: other related links, as a list of dicts with
  `title` and `url` keys


## Templates

The template used to render link collections is `data-links.html`, which works
both on [data-only](data.md) link collections, and on `.links`-generated pages.


## Link indices

If you add a `name.links` file, empty or containing some metadata, it will be
rendered as a hierarchy of index pages one for each link tag found.

`data-links.html` is used as default template for `.links`-generated pages.

[Back to reference index](../README.md)
