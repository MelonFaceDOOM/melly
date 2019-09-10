import re 
def format_quote(tag, string):
    start_pattern = "\[quote(, *name=([A-z0-9!%^&*]+)){0,1}(, *time=([0-9 :.-]+)){0,1}\]"

    # find start_tag and extract arguments if present
    match = re.match(start_pattern, string)
    start_tag = match.group()
    name_field=" username='{}'".format(match.groups()[1]) if match.groups()[1] else ""
    time_field=" time='{}'".format(match.groups()[3]) if match.groups()[3] else ""

    end_tag_pos = string.find("[/quote]")
    value = string[len(start_tag):end_tag_pos]

    formatted = "<blockquote{}{}>{}</blockquote>".format(name_field, time_field, value)
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
        "start": "\[quote(, *name=[A-z0-9!%^&*]+){0,1}(, *time=[0-9 :.-]+){0,1}\]",
        "end":  "[/quote]",
        "output_template": "",
        "format_func": format_quote
    },
    
    {
        "name": "spoiler",
        "start": "\[spoiler\]",
        "end": "[/spoiler]",
        "output_template": """<div class="panel-group">
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4 class="panel-title">
        <a data-toggle="collapse" href="#collapse1">Collapsible panel</a>
      </h4>
    </div>
    <div id="collapse1" class="panel-collapse collapse">
      <div class="panel-body">Panel Body</div>
    </div>
  </div>
</div>""",
        "format_func": simple_replace
    }
]

