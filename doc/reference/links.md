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

TODO
