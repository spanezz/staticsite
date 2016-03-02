+++
# File where the post will be written
path = "blog/{{now.strftime("%Y")}}/{{slug}}.md"

# Date for the post. You can change the format to any you like, both with
# |datetime_format and with normal strftime, like {{now.strftime("%Y-%m-%d")}}
date = "{{now|datetime_format()}}"

# Default tags for the post
tags = []
+++
# {{title}}

