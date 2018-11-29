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
import os, re
import datetime

from processorfactory import Processor, ProcessorRegistry

ARCHIVETYPE = "news.archive"
INDEXTYPE = "news.index"

# @p page - the page for which we are generating the excerpt
# @p indexPage - the page where the excerpt page will be shown
def getPageExcerpt( page, indexPage ):
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

    if not moreFound:
        lens = [len(l.strip()) for l in brief]
        cumlens = [sum(lens[:i]) for i in range(len(lens))]
        goodLens = [l for l in cumlens if l < 300]
        brief =  brief[:len(goodLens)]

    return "".join(fixExcerptLinks(brief, page, indexPage)).strip()


def fixExcerptLinks( excerpt, page, indexPage ):
    rxsName = r"[^]]*"
    rxsLocal = r"\.[^)]+"
    rxLink = re.compile( r'\[({0})\]\(\s*({1})\s*\)'.format(rxsName, rxsLocal) )
    pageDir = os.path.dirname( page.htmlFilename )
    indexDir = os.path.dirname( indexPage.htmlFilename )

    def makeAbsoluteLink( mo ):
        name = mo.group(1)
        link = mo.group(2)
        absLink = os.path.normpath( os.path.join( pageDir, link ) )
        indexLink = os.path.relpath( absLink, indexDir )
        return "[{0}]({1})".format( name, indexLink )

    return [ rxLink.sub( makeAbsoluteLink, l ) for l in excerpt ]


class PageInfoFinder:
    def __init__(self, pages):
        self.pages = pages

    def isInArchive( self, page ):
        if page.getPageType() == ARCHIVETYPE:
            return True

        parents = [ self.findPage(id) for id in page.getParentIds() ]

        return any( [ p.getPageType() == ARCHIVETYPE for p in parents if p is not None ] )


    def isIndexPage( self, page ):
        return page.getPageType() == INDEXTYPE


    def findPage( self, pageId ):
        for p in self.pages:
            if p.id == pageId:
                return p



class NewsPageProcessor( Processor ):
    def digest( self, page, pages, newPages ):
        pageInfo = PageInfoFinder( pages )
        childs = [ p for p in pages
            if p.isPublished() and p.isDescendantOf( page ) ]
        if len(childs) == 0:
            return

        childs.sort( key=lambda p: p.getCreationDate(), reverse=True )

        curDir = os.path.dirname( page.htmlFilename )
        def makeRelative( path ):
            return os.path.relpath( path, curDir )

        childAttrs = []
        for child in childs:
            if child.isExpired():
                continue
            if pageInfo.isIndexPage( child ) or pageInfo.isInArchive( child ):
                continue

            pubDate = child.getPublishDate()

            descr = {
                    "id": child.id,
                    "title": child.title,
                    "link": makeRelative(child.htmlFilename),
                    "brief": getPageExcerpt( child, page )
                    }
            # TODO: The date should be translatable. Use a strptime format.
            if pubDate is not None:
                descr["date"] = "{}.{}.{}".format( pubDate.day, pubDate.month, pubDate.year )

            childAttrs.append( descr )

        page.addExtraAttrs( { "news-activeitems": childAttrs } )


class NewsIndexPageProcessor( Processor ):
    def digest( self, page, pages, newPages ):
        pageInfo = PageInfoFinder( pages )
        childs = [ p for p in pages
            if not pageInfo.isIndexPage(p) and p.isPublished() and p.isChildOf( page ) ]
        if len(childs) == 0:
            return

        childs.sort( key=lambda p: p.getCreationDate(), reverse=True )

        curDir = os.path.dirname( page.htmlFilename )
        def makeRelative( path ):
            return os.path.relpath( path, curDir )

        childAttrs = []
        for child in childs:
            pubDate = child.getPublishDate()

            descr = {
                    "id": child.id,
                    "title": child.title,
                    "link": makeRelative(child.htmlFilename),
                    "brief": getPageExcerpt( child, page )
                    }
            # TODO: The date should be translatable. Use a strptime format.
            if pubDate is not None:
                descr["date"] = "{}.{}.{}".format( pubDate.day, pubDate.month, pubDate.year )

            childAttrs.append( descr )

        page.addExtraAttrs( { "news-indexitems": childAttrs } )


class Register(ProcessorRegistry):
    def registerPageTypes(self, pageTypeProcFactory):
        pageTypeProcFactory.registerPageType( "news", NewsPageProcessor.__name__ )
        pageTypeProcFactory.registerPageType( "news.index", NewsIndexPageProcessor.__name__ )
        pageTypeProcFactory.registerPageType( "blog", NewsPageProcessor.__name__ )
        pageTypeProcFactory.registerPageType( "blog.index", NewsIndexPageProcessor.__name__ )

