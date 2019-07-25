import re
from flask import url_for

def format_quote(tag, string):

    # find start_tag and extract arguments if present
    match = re.match(tag.start, string)
    start_tag = match.group()
    name = match.groups()[1] if match.groups()[1] else ""
    time = " - {}".format(match.groups()[3]) if match.groups()[3] else ""
    citation = name + time
    if match.groups()[5]:
        url = url_for("main.post", post_id=match.groups()[5])
        citation = "<a href={}>{}</a>".format(url, citation)

    end_tag_pos = string.find("[/quote]")
    value = string[len(start_tag):end_tag_pos]

    formatted = '<blockquote><footer class="blockquote-footer"><cite>{}</cite></footer><p class="mb-0">{}' \
                '</p></blockquote>'.format(citation, value)
    return formatted

def simple_replace(tag, string):
    start_tag = re.match(tag.start, string).group()
    end_tag_pos = string.find(tag.end)
    value = string[len(start_tag):end_tag_pos]
    formatted = tag.output_template.format(value=value)
    return formatted

# TODO: since ALL tags must start/end with [] and [/], brackets and the forward slash should just be removed from this dict
# TODO: and hardcoded elsewhere
# Note that start tags are matched by regex (since they can contain arguments), and end tags are matched by exact text
tags = [
    {
        "name": "bold",
        "start": "\[b\]",
        "end": "[/b]",
        "output_template": "<strong>{value}</strong>",
        "format_func": simple_replace
    },

    {
        "name": "italics",
        "start": "\[i\]",
        "end": "[/i]",
        "output_template": "<em>{value}</em>",
        "format_func": simple_replace
    },

    {
        "name": "url",
        "start": "\[url\]",
        "end": "[/url]",
        "output_template": "<a href={value}>{value}</a>",
        "format_func": simple_replace
    },

    {
        "name": "quote",
        "start": "\[quote(, *name=([A-z0-9!%^&*]+)){0,1}(, *time=([0-9 :.-]+)){0,1}(, *post_id=([0-9]+)){0,1}\]",
        "end":  "[/quote]",
        "output_template": "",
        "format_func": format_quote
    }
]