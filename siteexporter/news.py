import os
import datetime

ARCHIVETYPE = "news.archive"

class NewsPageProcessor:
    def __init__(self):
        self.pages = None
        pass

    def digest( self, page, pages, newPages ):
        self.pages = pages
        today = datetime.datetime.now()
        childs = [ p for p in pages
            if p.isPublished() and p.isDescendantOf( page ) ]
        if len(childs) == 0:
            return

        childs.sort( key=lambda p: p.getCreationDate(), reverse=True )

        curDir = os.path.dirname( page.htmlFilename )
        def makeRelative( path ):
            return os.path.relpath( path, curDir )

        childAttrs = []
        for p in childs:
            if p.isExpired( today ):
                continue
            if self.isInArchive( p ):
                continue

            pubDate = p.getPublishDate()
            if pubDate is not None and pubDate > today.date():
                continue

            descr = {
                    "id": p.id,
                    "title": p.title,
                    "link": makeRelative(p.htmlFilename),
                    "brief": self.getBriefDescription( p )
                    }
            if pubDate is not None:
                descr["date"] = "{}.{}.{}".format( pubDate.day, pubDate.month, pubDate.year )

            childAttrs.append( descr )

        page.addExtraAttrs( { "news_activeitems": childAttrs } )


    def isInArchive( self, page ):
        if page.pageType == ARCHIVETYPE:
            return True

        parents = [ self.findPage(id) for id in page.getParentIds() ]

        return any( [ p.pageType == ARCHIVETYPE for p in parents if p is not None ] )


    def findPage( self, pageId ):
        for p in self.pages:
            if p.id == pageId:
                return p


    def getBriefDescription( self, page ):
        mkdLines = page.getMarkdown()

        brief = []
        inYaml = False
        moreFound = False
        for line in mkdLines:
            if inYaml:
                if line.rstrip() in ( "---", "..." ):
                    inYaml = False
            else:
                if line.rstrip() == "---":
                    inYaml = True
                    continue
                l = line.strip()
                if l.startswith( "#" ) or l.startswith( "```" ) or l.startswith("~~~"):
                    break
                if l == "<!--more-->":
                    moreFound = True
                    break
                brief.append( line )

        if moreFound:
            return "".join(brief).strip()

        lens = [len(l.strip()) for l in brief]
        cumlens = [sum(lens[:i]) for i in range(len(lens))]
        goodLens = [l for l in cumlens if l < 300]
        return "".join( brief[:len(goodLens)] ).strip()

