# vim: set fileencoding=utf-8 sw=4 sts=4 ts=8 et :vim
# Zim Plugin - Site Exporter
# Copyright (C) 2018 Marko Mahnič
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import os
import datetime

ARCHIVETYPE = "news.archive"
INDEXTYPE = "news.index"

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
            if self.isInArchive( p ) or self.isIndexPage( p ):
                continue

            pubDate = p.getPublishDate()

            descr = {
                    "id": p.id,
                    "title": p.title,
                    "link": makeRelative(p.htmlFilename),
                    "brief": self.getBriefDescription( p )
                    }
            # TODO: The date should be translatable. Use a strptime format.
            if pubDate is not None:
                descr["date"] = "{}.{}.{}".format( pubDate.day, pubDate.month, pubDate.year )

            childAttrs.append( descr )

        page.addExtraAttrs( { "news-activeitems": childAttrs } )


    def isInArchive( self, page ):
        if page.pageType == ARCHIVETYPE:
            return True

        parents = [ self.findPage(id) for id in page.getParentIds() ]

        return any( [ p.pageType == ARCHIVETYPE for p in parents if p is not None ] )


    def isIndexPage( self, page ):
        return page.pageType == INDEXTYPE


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

