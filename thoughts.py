import web
import markdown
import bleach
from smartencoding import smart_unicode

import os, collections

def hyphenify(str):
    return str.replace("-", " ")
    
def dehyphenify(str):
    return str.replace(" ", "-")

#Basic config

base_path = "./"
thoughts_path = base_path + "thoughts/"
templates_path = base_path + "templates/"

template_globals = {"socials": [], "dehyphenify": dehyphenify}

urls = (
    '/', 'HomeServer',
    '/taglist', 'TagListServer',
    '/archive', 'ArchiveServer',
    '/tag/(.*)', 'TagServer',
    '/(.*)', 'ThoughtServer',
)

#App setup

def notfound():
    return renderpage.notfound()

app = web.application(urls, globals(), autoreload=False)
app.notfound = notfound

application = app.wsgifunc()

#Template renderers

render = web.template.render(templates_path, globals=template_globals)
renderpage = web.template.render(templates_path, globals=template_globals, base="index")

#Markdown

md_extensions = ["markdown.extensions.codehilite",
                 "markdown.extensions.def_list",
                 "markdown.extensions.footnotes",
                 "markdown.extensions.meta"]
markdowner = markdown.Markdown(md_extensions,
                               extension_configs={"markdown.extensions.codehilite": {"css_class": "code"}},
                               output_format="html5")


#Bleacher

tags = ["span", "br", "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
        "a", "blockquote", "pre", "code",
        "li", "ol", "ul", "dl", "dt", "dd",
        "strong", "em", "sup", "hr", "acronym", "abbr"]
attrs = {"*": ["class"],
         "a": ["href", "title"],
         "acronym": ["title"],
         "abbr": ["title"]}
bleacher = lambda str: bleach.clean(str, tags, attrs)

#

def has_suffix(str, suffix):
    return str[-len(suffix):] == suffix

def thoughts_all():
    for filename in os.listdir(thoughts_path):
        if    has_suffix(filename, ".md") \
           or has_suffix(filename, ".markdown"):
            yield thought_get(filename)

def thoughts_by_tag(tag):
    return filter(lambda thought: tag in thought.tags, thoughts_all())

def thought_get(name):
    filenames = [thoughts_path + name,
                 thoughts_path + name + ".md",
                 thoughts_path + name + ".markdown"]

    for filename in filenames:
        try:
            with open(filename) as file:
                return Thought(name, file)

        except IOError:
            pass

    return None

class Thought:
    def __init__(self, name, file):
        def through_none(f):
            return lambda x: None if x is None else f(x)
            
        def attr_apply(obj, attr, f):
            setattr(obj, key, f(getattr(obj, key)))
        
        self.title = None
        self.summary = None
        self.tags = []
        #Remove extension
        self.name = name[:name.rfind(".")]
        
        join_keys = set(["title", "summary"])
        markdown_keys = set(["summary"])
        bleach_keys = markdown_keys | set(["contents"])
        metadata_keys = (set(["tags"]) | join_keys | bleach_keys) - set("contents")
        
        #Process the text
        encoded = smart_unicode(file.read())
        self.contents = markdowner.reset().convert(encoded)
        
        #Import the relevant keys from the metadata into self
        for key in metadata_keys:
            if key in markdowner.Meta:
                value = markdowner.Meta[key]
                
                if key in join_keys:
                    value = "\n".join(value)
                
                setattr(self, key, value)
        
        for key in markdown_keys:
            mark = lambda x: markdowner.reset().convert(x)
            attr_apply(self, key, through_none(mark))
        
        #Bleach keys used as HTML
        for key in bleach_keys:
            attr_apply(self, key, through_none(bleacher))
    
def tags_all():
    tags = collections.defaultdict(lambda: 0)
    
    for thought in thoughts_all():
        for tag in thought.tags:
            tags[tag] += 1
    
    return tags
    
class Social:
    def __init__(self, label, link):
        self.label = label
        self.link = link
    
class HomeServer:
    def GET(self):
        thoughts = [render.inlinethought(thought) for thought in thoughts_all()]
        return renderpage.home(thoughts)

class ThoughtServer:
    def GET(self, name):
        thought = thought_get(name)

        if thought is None:
            return web.notfound()

        return renderpage.thought(thought)
        
class TagServer:
    def GET(self, tag):
        thoughts = thoughts_by_tag(tag)
        
        if "-" in tag:
            tag = hyphenify(tag)
            thoughts += thoughts_by_tag(tag)
        
        thoughts = [render.inlinethought(thought) for thought in thoughts]
        return renderpage.tag(tag, thoughts)

class TagListServer:
    def GET(self):
        return renderpage.taglist(tags_all())
        
class ArchiveServer:
    def GET(self):
        return renderpage.archive(thoughts_all())

template_globals["socials"] += [Social("github", "http://www.github.com/Fedjmike"),
                                Social("twitter", "http://www.twitter.com/Fedjmike")]

if __name__ == "__main__":
    app.run()
