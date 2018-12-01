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
    def __init__(self, pageProcessorFactory):
        self.pageProcessorFactory = pageProcessorFactory

    def _processorTypeName( self, page ):
        return self.pageProcessorFactory.getProcessorName( page.getPageType() )

    def isInArchive( self, page ):
        if self._processorTypeName(page) == NewsArchivePageProcessor.__name__:
            return True

        parents = page.getAncestors()
        return any( [ self._processorTypeName(p) == NewsArchivePageProcessor.__name__
            for p in parents if p is not None ] )

    def isIndexPage( self, page ):
        return self._processorTypeName(page) == NewsIndexPageProcessor.__name__

    def isNewsRootPage( self, page ):
        return self._processorTypeName(page) == NewsPageProcessor.__name__

class NewsIndexBuilder:
    """
    Build the index of index pages under a root news page.

    The index is composed of all "news.index" and "news" pages under the
    news-root page.  If another descendant of type "news" is found, its children
    are not added to this index.
    """

    class IndexEntry:
        def __init__( self, page ):
            self.page = page
            self.parent = None
            self.children = []

    def __init__(self, newsRootPage, pageInfoFinder):
        self.root = newsRootPage
        self.pageInfo = pageInfoFinder
        self.index = None

    def getIndexForPage( page ):
        if self.index is None:
            self.index = self._buildIndex()
        return None

    def _buildIndex( self ):
        def makeEntries( page, parentEntry ):
            for child in page.children:
                entry = None
                if self.pageInfo.isIndexPage( child ) or self.pageInfo.isNewsRootPage( child ):
                    entry = NewsIndexBuilder.IndexEntry( child )
                    entry.parent = parentEntry
                    parentEntry.children.append( entry )
                if not self.pageInfo.isNewsRootPage( child ):
                    makeEntries( child, parentEntry if entry is None else entry )

        rootEntry = NewsIndexBuilder.IndexEntry( self.root )
        makeEntries( self.root, rootEntry )
        return rootEntry


# Create a list of published and not expired descendants.
class NewsPageProcessor( Processor ):
    def digest( self, page, pages, newPages ):
        pageInfo = PageInfoFinder( page.exportData.pageTypeProcFactory )
        childs = [ p for p in page.getDescendants() if p.isPublished() ]
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


# Create a list of children items that are not themselves index pages.
#
# NOTE: Moving items between index pages will change their address and may
# break links from other sites.  It would be better if index pages were
# auto-generated from the publishDate.
class NewsIndexPageProcessor( Processor ):
    def digest( self, page, pages, newPages ):
        pageInfo = PageInfoFinder( page.exportData.pageTypeProcFactory )
        childs = [ p for p in page.children
            if not pageInfo.isIndexPage(p) and p.isPublished() ]
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


# NOTE: This processor may not be necessary
class NewsArchivePageProcessor:
    pass


class Register(ProcessorRegistry):
    def registerPageTypes(self, pageTypeProcFactory):
        pageTypeProcFactory.registerPageType( "news", NewsPageProcessor.__name__ )
        pageTypeProcFactory.registerPageType( "news.index", NewsIndexPageProcessor.__name__ )
        pageTypeProcFactory.registerPageType( "news.archive", NewsArchivePageProcessor.__name__ )
        pageTypeProcFactory.registerPageType( "blog", NewsPageProcessor.__name__ )
        pageTypeProcFactory.registerPageType( "blog.index", NewsIndexPageProcessor.__name__ )
        pageTypeProcFactory.registerPageType( "blog.archive", NewsArchivePageProcessor.__name__ )

