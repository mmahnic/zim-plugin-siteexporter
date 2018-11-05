import os

class NewsPageProcessor:
    def __init__(self):
        pass

    def digest( self, page, pages, newPages ):
        childs = [ p for p in pages
            if p.isPublished() and p.isChildOf( page ) ]
        if len(childs) == 0:
            return

        curDir = os.path.dirname( page.htmlFilename )
        def makeRelative( path ):
            return os.path.relpath( path, curDir )

        childAttrs = []
        for p in childs:
            descr = {
                    "id": p.id,
                    "title": p.title,
                    "link": makeRelative(p.htmlFilename)
                    }
            childAttrs.append( descr )

        page.addExtraAttrs( { "news_activeitems": childAttrs } )

