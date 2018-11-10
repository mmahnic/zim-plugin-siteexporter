import os
import datetime

class NewsPageProcessor:
    def __init__(self):
        pass

    def digest( self, page, pages, newPages ):
        today = datetime.datetime.now()
        childs = [ p for p in pages
            if p.isPublished() and p.isChildOf( page ) ]
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
            descr = {
                    "id": p.id,
                    "title": p.title,
                    "link": makeRelative(p.htmlFilename),
                    "brief": self.getBriefDescription( p )
                    }
            if p.createTime is not None:
                t = p.createTime
                descr["date"] = "{}.{}.{}".format( t.day, t.month, t.year )
            childAttrs.append( descr )

        page.addExtraAttrs( { "news_activeitems": childAttrs } )


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

