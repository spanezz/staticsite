(function($) {
"use strict";

class ExternalLink
{
    constructor(el, info)
    {
        this.el = el;
        this.info = info;
        this.open_timeout = null;
        this.close_timeout = null;
        this.decorate();
    }

    decorate()
    {
        this.dropdown = document.createElement("span");
        this.dropdown.className = "dropdown";

        // Highlight external links
        this.icon = document.createElement("button");
        this.icon.className = "fa fa-external-link btn btn-link";
        this.icon.setAttribute("id", "dropdown1");
        this.icon.setAttribute("data-toggle", "dropdown");
        this.icon.setAttribute("aria-haspopup", "true");
        this.icon.setAttribute("aria-expanded", "false");
        this.dropdown.append(this.icon);

        let display = document.createElement("div");
        display.className = "dropdown-menu";
        display.style["max-width"] = "200px";
        display.setAttribute("aria-labelledby", "dropdown1");
        display.append("LALALA");

        this.dropdown.append(display);

        this.el.after(this.dropdown);

        // Show details on hover
        this.el.addEventListener("mouseenter", evt => { this.delayed_open(); });
        this.el.addEventListener("mouseleave", evt => { this.delayed_close(); });
        display.addEventListener("mouseenter", evt => { this.cancel_delayed_close(); });
    }

    delayed_open()
    {
        this.open_timeout = setTimeout(() => { this.open() }, 300);
    }

    cancel_delayed_open()
    {
        if (this.open_timeout === null)
            return;
        clearTimeout(this.open_timeout);
        this.open_timeout = null;
    }

    delayed_close()
    {
        this.close_timeout = setTimeout(() => { this.close() }, 300);
    }

    cancel_delayed_close()
    {
        if (this.close_timeout === null)
            return;
        clearTimeout(this.close_timeout);
        this.close_timeout = null;
    }

    open()
    {
        $(this.icon).dropdown("show");
        this.open_timeout = null;
    }

    close()
    {
        $(this.icon).dropdown("hide");
        this.close_timeout = null;
    }
};

class ExternalLinks
{
    constructor()
    {
        let el = document.getElementById("external-links");
        if (!el)
            return;
        this.links = JSON.parse(el.text);
        console.log(this.links);

        for (let el of document.getElementsByTagName("a"))
        {
            const href = el.getAttribute("href");
            const info = this.links[href];
            if (info === undefined)
                continue;
            console.log(href, info);

            new ExternalLink(el, info);
        }
    }
}


function hover_link(evt, link)
{
}


function main()
{
    let external_links = new ExternalLinks();
}

document.addEventListener("DOMContentLoaded", evt => { main(); });

})(jQuery);
