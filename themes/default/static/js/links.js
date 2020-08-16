(function($) {
"use strict";

class ExternalLink
{
    constructor(el, info, sequence)
    {
        this.el = el;
        this.info = info;
        this.sequence = sequence;
        this.open_timeout = null;
        this.close_timeout = null;
        this.decorate();
    }

    decorate()
    {
        const id = `dropdown-${this.sequence}`;

        // Main dropdown container
        this.dropdown = document.createElement("span");
        this.dropdown.className = "dropdown";

        // Dropdown menu opener icon next to the link
        this.icon = document.createElement("button");
        this.icon.className = "fa fa-external-link btn btn-link p-0 pl-1 align-baseline";
        this.icon.setAttribute("id", id);
        this.icon.setAttribute("data-toggle", "dropdown");
        this.icon.setAttribute("aria-haspopup", "true");
        this.icon.setAttribute("aria-expanded", "false");
        this.dropdown.append(this.icon);

        // Dropdown contents
        let contents = this.render_info(id);
        this.dropdown.append(contents);

        this.el.after(this.dropdown);

        // Show details on hover
        this.el.addEventListener("mouseenter", evt => { this.delayed_open(); });
        this.el.addEventListener("mouseleave", evt => { this.cancel_delayed_open(); this.delayed_close(); });
        contents.addEventListener("mouseenter", evt => { this.cancel_delayed_close(); });
    }

    render_info(opener_name)
    {
        let contents = document.createElement("div");
        contents.className = "dropdown-menu dropdown-menu-right";
        contents.setAttribute("aria-labelledby", "dropdown1");

        if (this.info.title)
        {
            let a = document.createElement("a");
            a.className = "text-dark";
            a.setAttribute("href", this.info.url);
            a.append(document.createTextNode(this.info.title));

            let header = document.createElement("h6");
            header.className = "dropdown-header";
            header.append(a);

            contents.append(header);
        }

        if (this.info["abstract"])
        {
            let p = document.createElement("p");
            p.className = "pl-4 pr-4 mb-0 small font-italic";

            let a = document.createElement("a");
            a.className = "text-dark";
            a.setAttribute("href", this.info.url);
            a.append(this.info["abstract"]);

            p.append(a);
            contents.append(p);
        }

        if (this.info.tags || this.info.archive || this.info.related)
        {
            let pills = document.createElement("div");
            pills.className = "pl-4 pr-4 text-right";

            if (this.info.tags)
            {
                for (const taginfo of this.info.tags)
                {
                    let tag = document.createElement("a");
                    tag.className = "badge badge-pill badge-info ml-1";
                    tag.setAttribute("data-role", "tag");
                    tag.setAttribute("href", taginfo.url);
                    tag.append(taginfo.tag);
                    pills.append(tag);
                }
            }

            if (this.info.archive)
            {
                let link = document.createElement("a");
                link.className = "badge badge-pill badge-primary ml-1";
                link.setAttribute("data-role", "archive");
                link.setAttribute("href", this.info.archive);
                link.append("archive")
                pills.append(link);
            }

            if (this.info.related)
            {
                for (const rel of this.info.related)
                {
                    let a = document.createElement("a");
                    a.className = "badge badge-pill badge-primary ml-1";
                    a.setAttribute("data-role", "related");
                    a.setAttribute("href", rel.url);
                    a.append(rel.title);
                    pills.append(a);
                }
            }

            contents.append(pills);
        }

        return contents;
    }

    delayed_open()
    {
        this.open_timeout = setTimeout(() => { this.open() }, 600);
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
        this.close_timeout = setTimeout(() => { this.close() }, 600);
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
        // console.log("Link data:", this.links)

        // Store <a> elements into a static array, otherwise we cannot create
        // more <a> records without having them dynamically inserted in the
        // loop
        let elements = [];
        for (let el of document.getElementsByTagName("a"))
            elements.push(el);

        let sequence = 1;
        for (let el of elements)
        {
            const href = el.getAttribute("href");
            const info = this.links[href];
            if (info === undefined)
                continue;

            new ExternalLink(el, info, sequence++);
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
