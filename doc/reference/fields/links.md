# links: Extra metadata for external links.

Extra metadata for external links.

It is a list of dicts of metadata, one for each link. In each dict, these keys are recognised:

* `title`: str: short title for the link
* `url`: str: external URL
* `abstract`: str: long description or abstract for the link
* `archive`: str: URL to an archived version of the site
* `tags`: List[str]: tags for this link
* `related`: List[Dict[str, str]]: other related links, as a list of dicts with
  `title` and `url` keys

[Back to reference index](../README.md)
