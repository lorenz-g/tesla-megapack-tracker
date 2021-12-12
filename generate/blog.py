import os
import datetime as dt

import jinja2
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
import markdown

from generate.utils import generate_link


BOOTSTRAPIFY_DEFAULT = {
    "table": ["table", "table-responsive", "table-sm"],
    "img": ["img-fluid", "border", "shadow"],
}


def replace_in_with(searchterm, soup, attributes):
    for item in soup.select(searchterm):
        attribute_set = set(item.attrs.get("class", []) + attributes)
        item.attrs["class"] = list(attribute_set)


def bootstrapify_markdown_html(html):
    """
    Original problem was that there was no easy way to add class="table" to a table
    https://github.com/Python-Markdown/markdown/issues/312

    Then came across this and copied some functions here:
    https://github.com/ingwinlu/pelican-bootstrapify/blob/master/bootstrapify.py

    """
    soup = BeautifulSoup(html, "html.parser")

    for selector, classes in BOOTSTRAPIFY_DEFAULT.items():
        replace_in_with(selector, soup, classes)
    return soup.decode()


# @blog.route("/<int:year>/<int:month>/<int:day>/<name>.html")
# def blog_post(year, month, day, name):

#     # TODO: on mobile, when opening a blot post, sth is overflowing and one can move the page sidewards a bit
#     # which is not good. Answer: it was a long link in an indented bullet list
#     static_folder = "%d-%02d-%02d" % (year, month, day)
#     blog_url = "blog/%s-%s" % (static_folder, name)

#     try:
#         blog_markdown = render_template(blog_url + ".md")
#     except jinja2.exceptions.TemplateNotFound:
#         abort(404)
#     md = markdown.Markdown(extensions=["tables", "meta"])

#     blog_html = md.convert(blog_markdown)
#     blog_html = bootstrapify_markdown_html(blog_html)

#     md.Meta["static_folder"] = [static_folder]
#     md.Meta["blog_url"] = [request.path]
#     md.Meta["thumb_path"] = [
#         "/static/blog/%s/%s"
#         % (md.Meta["static_folder"][0].strip("/"), md.Meta["thumb"][0].lstrip("/"))
#     ]

#     return render_template("blog/blog_post.html", blog_html=blog_html, meta=md.Meta)



def gen_blog():
    markdown_entries_path = "misc"
    blog_entries_names = [
        # the latest one at the top
        # enable it once it is done
        "2021-11-20-big-battery-articles.md",
        "2021-11-19-big-battery-info-sources.md",
        "2021-08-30-changelog.md",
    ]

    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    output_dir = 'docs'
    
    
    extra = {
        "now": dt.datetime.utcnow(),
        "blog_entries": []
    }
    
    for b in blog_entries_names:
        p = os.path.join(markdown_entries_path, b)

        md = markdown.Markdown(extensions=["meta"])
        with open(p) as f:
            blog_html = md.convert(f.read())
            blog_html = bootstrapify_markdown_html(blog_html)

        # this populates the md.Meta
        md.Meta["static_folder"] = ["./blog/" + b[0:10] + "/"]
        md.Meta["url"] = ["blog/" + b.replace(".md", ".html")]
        md.Meta["github_url"] = "https://github.com/lorenz-g/tesla-megapack-tracker/blob/main/misc/" + b
        extra["blog_entries"].append(md.Meta)

        # generate the individual blog post
        template_name = "blog-post.jinja.html"
        template = env.get_template(template_name)

        output = template.render(extra=extra, blog_html=blog_html, meta=md.Meta, g_l=generate_link)

        # generate individual /blog/xx.html sites
        with open(os.path.join(output_dir, "blog", b.replace(".md", ".html")), 'w') as f:
            f.write(output)

    # generate the /blog.html site
    template_name = "blog.jinja.html"
    template = env.get_template(template_name)
    output = template.render(extra=extra, g_l=generate_link)

    with open(os.path.join(output_dir, template_name.replace(".jinja", "")), 'w') as f:
        f.write(output)

    
    # TODO: edit on github button
    


if __name__ == "__main__":
    # todo this just for testing 
    pr_len = {
        "tesla": -1,
        "all": -1,
    }
    gen_blog(pr_len)