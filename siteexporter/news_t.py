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
import datetime
import unittest
import exportdata
from sxpage import MarkdownPage, findPageParents
from processorfactory import PageTypeProcessorFactory, ProcessorRegistry
import news

class TestNotebook:
    def __init__(self):
        self.pages = []

class TestZimPage:
    def __init__(self, slug, content):
        self.parent = None
        self._childs = []
        self.parts = [slug]
        self._meta = { "Creation-Date": "2018-10-11T12:13:14+02:00" }
        self.content = content

    def get_title(self):
        return "Title"

    def exists(self):
        return True

    def dump(self, format=None):
        return self.content

    def addChilds( self, childs ):
        for child in childs:
            child.parent = self
            if not child in self._childs:
                self._childs.append( child )
            child.parts = self.parts + child.parts[-1:]
            # Readd childs to fix paths
            child.addChilds( child._childs )

        return self

def createNewsStructure(notebook):
    def eols(lines):
        return [ l + "\n" for l in lines ]

    def newsPage(slug):
        content = eols( [ "---", "type: news", "menu: News", "childType: news.item", "---",
            "News Root Page: {}".format(slug) ] )
        page = TestZimPage( slug, content )
        notebook.pages.append(page)
        return page

    def indexPage(slug):
        content = eols( [ "---", "type: news.index", "---",
            "New Index Page: {}".format(slug) ] )
        page = TestZimPage( slug, content )
        notebook.pages.append(page)
        return page

    def itemPage(slug, createDate=datetime.datetime.now()):
        content = eols( [ "---", "createDate: {}".format(createDate.isoformat()), "---",
            "New Item Page: {}".format(slug) ] )
        page = TestZimPage( slug, content )
        notebook.pages.append(page)
        return page

    root = newsPage( "announcements" ).addChilds( [
        indexPage( "2017" ).addChilds( [
            itemPage( "2017-12-12" ),
            itemPage( "2017-12-13" ) ] ),
        indexPage( "2018" ).addChilds( [
            itemPage( "2018-12-12" ),
            itemPage( "2018-12-13" ),
            indexPage( "2018-07" ).addChilds( [
                itemPage( "2018-07-07" ),
                itemPage( "2018-07-08" ),
                ])
            ] ),
        indexPage( "2019" ).addChilds( [
            itemPage( "2019-12-12" ).addChilds( [
                indexPage( "2019-07-weird" ).addChilds( [
                    itemPage( "2019-07-07" ),
                    itemPage( "2019-07-08" ),
                    ])
                ] ),
            newsPage( "sub-announcements" ).addChilds( [
                indexPage( "2016-sub" ).addChilds( [
                    itemPage( "2016-12-12" ),
                    itemPage( "2016-12-13" ) ] ),
                ])
            ] )
        ] )

    return root


class TestNewsIndexBuilder(unittest.TestCase):
    def test_selfTest(self):
        notebook = TestNotebook()
        root = createNewsStructure( notebook )
        self.assertEqual( len(root._childs), 3 )
        self.assertEqual( len(root._childs[0]._childs), 2 )
        self.assertEqual( len(root._childs[1]._childs), 3 )
        self.assertEqual( len(root._childs[2]._childs), 2 )
        self.assertEqual( len(notebook.pages), 19 )

    def test_createNewsIndex(self):
        # -- GIVEN
        notebook = TestNotebook()
        zimRoot = createNewsStructure( notebook )
        mkdPages = [ MarkdownPage( p, None ) for p in notebook.pages if p.exists() ]
        root = [ p for p in mkdPages if p.zimPage == zimRoot ][0]
        findPageParents( mkdPages )

        procFactory = PageTypeProcessorFactory()
        ProcessorRegistry.registerPageTypes(procFactory)
        infoFinder = news.PageInfoFinder(procFactory)
        builder = news.NewsIndexBuilder(root, infoFinder)

        # -- WHEN
        rootIdx = builder._buildIndex()

        # -- THEN
        self.assertEqual( rootIdx.page.path, ["announcements"] )
        self.assertEqual( len(rootIdx.children), 3 )

        ch0 = rootIdx.children[0]
        self.assertEqual( ch0.page.path[-1], "2017" )
        self.assertEqual( len(ch0.children), 0 )

        ch1 = rootIdx.children[1]
        self.assertEqual( ch1.page.path[-1], "2018" )
        self.assertEqual( len(ch1.children), 1 )
        ch1_ch0 = ch1.children[0]
        self.assertEqual( ch1_ch0.page.path[-1], "2018-07" )

        ch2 = rootIdx.children[2]
        self.assertEqual( ch2.page.path[-1], "2019" )
        self.assertEqual( len(ch2.children), 2 )
        ch2_ch0 = ch2.children[0]
        self.assertEqual( ch2_ch0.page.path[-1], "2019-07-weird" )
        self.assertEqual( len(ch2_ch0.children), 0 )

        # Do not recurse into "sub-news".
        ch2_ch1 = ch2.children[1]
        self.assertEqual( ch2_ch1.page.path[-1], "sub-announcements" )
        self.assertEqual( len(ch2_ch1.children), 0 )

    def test_createNewsIndexDict(self):
        # -- GIVEN
        notebook = TestNotebook()
        zimRoot = createNewsStructure( notebook )
        mkdPages = [ MarkdownPage( p, None ) for p in notebook.pages if p.exists() ]
        root = [ p for p in mkdPages if p.zimPage == zimRoot ][0]
        findPageParents( mkdPages )

        procFactory = PageTypeProcessorFactory()
        ProcessorRegistry.registerPageTypes(procFactory)
        infoFinder = news.PageInfoFinder(procFactory)
        builder = news.NewsIndexBuilder(root, infoFinder)

        # -- WHEN
        index = builder.getIndexDictForPage( root )

        # -- THEN
        self.assertEqual( index["id"], "announcements" )
        self.assertEqual( len(index["items"]), 3 )

        ch0 = index["items"][0]
        self.assertEqual( ch0["id"], "announcements:2017" )

        ch1 = index["items"][1]
        self.assertEqual( ch1["id"], "announcements:2018" )
        self.assertEqual( len(ch1["items"]), 1)

        ch2 = index["items"][2]
        self.assertEqual( ch2["id"], "announcements:2019" )
        self.assertEqual( len(ch2["items"]), 2)

if __name__ == "__main__":
    unittest.main()
