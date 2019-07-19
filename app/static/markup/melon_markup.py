import json
import os

class FormatTag():
    def __init__(self, name, start, end, output_template):
        self.name = name
        self.start = start
        self.end = end
        self.output_template = output_template
        self.openings = []
        self.net_change = len(self.output_template.format(value="")) - len(self.start) - len(self.end)

    def close(self, unformatted, end_pos):
        if self.openings:
            pre_text = unformatted[:self.openings[-1]]
            post_text = unformatted[end_pos + len(self.end):]
            open_tag_end_pos = self.openings[-1] + len(self.start)
            interior = unformatted[open_tag_end_pos:end_pos]
            formatted = self.output_template.format(value=interior)
            self.openings = self.openings[:-1]
            return pre_text + formatted + post_text
        else:
            return unformatted


def create_tags():
    tags = []
    
    dir_path = os.path.dirname(os.path.realpath(__file__))
    
    with open(os.path.join(dir_path, "tags.txt"),"r") as f:
        
        json_tags = json.loads(f.read())
        for t in json_tags:
            tags.append(FormatTag(name=t['name'], start=t['start'], end=t['end'], output_template=t['output_template']))
    return tags


def parse(s):
    # the FormatTag class keeps track of information for each tag type, while variables within this function
    # are responsible for keeping track of inter-tag information and adjusting the tag values based on what happens
    # as the string is parsed
    
    replace = {
        u'<':u'&lt;',
        u'>':u'&gt;',
        u'&':u'&amp;',
        u'\n':u'<br/>'
    }
    
    for key in replace.keys():
        s = s.replace(key, replace[key])

    tags = create_tags()
    
    pos = 0
    while True:
        for tag in tags:
            # mark location of all start tags as they are identified
            if s[pos:].startswith(tag.start):
                tag.openings.append(pos)
                pos += len(tag.start) # skip to the end of the start tag
                break
            
            # replace start and end tag if both have been found
            elif s[pos:].startswith(tag.end):
                if tag.openings:
                    tag_opening_pos = tag.openings[-1]
                    s = tag.close(s, pos)

                    # find if any tags are between the start and close of the tag that was just closed
                    inbetween_tags = False
                    for _tag in tags:
                        for i, _tag_opening_pos in enumerate(_tag.openings):
                            if _tag_opening_pos > tag_opening_pos and _tag_opening_pos < pos:
                                inbetween_tags = True
                                del _tag.openings[i] # delete in-between tags as their position value is no longer valid
                    
                    if inbetween_tags:
                    # restart the parser at that the start location of the tag that was closed 
                        pos = tag_opening_pos
                        break
                    
                    # if there were no tags between, adjust the frame and parsing past the ending of this tag pairing
                    pos += len(tag.end) + tag.net_change
                    break
                else:
                    # if there is an end tag with no opening tag, skip past it.
                    pos += len (tag.end)
        else:
            pos += 1

        if pos > len(s):
            return s
        #print(s[:pos], pos)
