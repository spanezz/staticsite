# Template designed documentation

## Social media previews

[The Essential Meta Tags for Social Media](https://css-tricks.com/essential-meta-tags-social-media/)
is a good introduction for creating social media preview metadata for web pages.

In staticsite templates, this becomes:

```jinja2
<meta property="og:title" content="{{page.meta.title}}">
{% if page.meta.description -%}
  <meta name="description" property="og:description" content="{{page.meta.description|striptags}}" />
{%- endif %}
{% if page.meta.image -%}
  <meta property="og:image" content="{{url_for(page.meta.image, absolute=True)}}" />
  <meta name="twitter:card" content="{{url_for(page.meta.image, absolute=True)}}" />
{%- endif %}
<meta property="og:url" content="{{url_for(page, absolute=True)}}" />
```

Notes:

* [`og:description` should not contain HTML tags](https://stackoverflow.com/questions/7759782/can-opengraph-description-fields-contain-html)
* [`description` and `og:description` can be combined](https://stackoverflow.com/questions/6203984/combining-the-meta-description-and-open-graph-protocol-description-into-one-tag)

## Testing social media previews

**Facebook**:

* [Sharing debugger](https://developers.facebook.com/tools/debug/sharing/) (requires login)
* [Object Graph Object debugger](https://developers.facebook.com/tools/debug/og/object/) (requires login)

**Twitter**:

* [Twitter card validator](https://cards-dev.twitter.com/validator) (requires login)

**Telegram**:

* [@webpagebot](https://telegramgeeks.com/2016/03/you-can-update-link-preview-telegram/)
  can be asked to (re)generate and show link previews

## Other useful links

* [Open Graph Check](https://opengraphcheck.com/)
* [Description of Open Graph types](https://stackoverflow.com/questions/8263493/ogtype-and-valid-values-constantly-being-parsed-as-ogtype-website)
