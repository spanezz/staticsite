# Page

`Page` objects are the base for all elements in the site. Different content is
loaded with different instances of `Page`, like `Asset`, `Image`, and
`MarkdownPage`.

## `meta`

Dictionary with all the [metadata](metadata.md) collected for the page or resource.

You can inspect this using the `ssite dump_meta` command.


## `find_pages(…)`

Find resources in the site relative to the current page.

The full signature is:

```py
Page.find_pages(
            path: Optional[str] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None,
            root: Optional[str] = None,
            **kw) -> List[Page]
```

See [page filter documentation](page-filter.md) for details.


## `resolve_path(target: Union[str, Page]) -> Page`

Find a page by path, relative to the current page.

If target is already a `Page`, it is returned as-is.


## `url_for(target: Union[str, "Page"], absolute=False) -> str`

Return a URL that can be used in this page to link to `target`.

Set `absolute=True` to force it to be an absolute URL.


[Back to reference index](README.md)
