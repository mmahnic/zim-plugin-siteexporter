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
import dateutil.parser as dateparser

from pageattributes import loadYamlAttributes

import logging
lwarn = logging.warning
lerror = logging.error

mkdExtension = "markdown"
htmlExtension = "html"
exportPath = "/tmp/site" # TODO: depends on the system, may be configured by the user, may include notebook name

class MarkdownPage:
    def __init__( self, zimPage, exportData ):
        """@p filename is relative to exportPath."""
        self.zimPage = zimPage
        self.exportData = exportData
        self.path = zimPage.parts # a list of parts that compose the path
        self.filename = "{}.{}".format( "/".join(self.path), mkdExtension )
        self.htmlFilename = "{}.{}".format("/".join(self.path), htmlExtension)
        self.attrs = {}
        self.parent = None
        self.children = []

        self.id = ":".join(self.path)
        self.level = len(self.path)
        self.weight = 999999
        self.title = self.zimPage.get_title()
        self.lang = None
        self.metaTitle = self.title
        self.menuText = None
        self._pageType = None
        self._childType = None
        self.isDraft = False
        self.published = True
        self.createDate = None
        self.expireDate = None
        self.publishDate = None
        self.unpublishDate = None
        self.template = None
        self.templateBasename = None # template attribute
        self.style = None
        self.extraAttrs = {}

        self.setAttributes( loadYamlAttributes( zimPage ) )


    def fullFilename(self):
        return os.path.join(exportPath, self.filename)

    def fullHtmlFilename(self):
        return os.path.join(exportPath, self.htmlFilename)

    def parentId( self, levels=1 ):
        return ":".join( self.path[:-levels] )

    def isDescendantOf( self, page ):
        if len(self.path) <= len(page.path):
            return False
        for a,b in zip(self.path, page.path):
            if a != b:
                return False
        return True

    def isChildOf( self, page ):
        return self.parent is not None and self.parent == page

    def getParentIds( self ):
        if len(self.path) < 2:
            return []
        return [ self.parentId(i) for i in range(1, len(self.path)) ]

    def getDescendants( self ):
        return sum([ [c] + c.getDescendants() for c in self.children ], [])

    def getAncestors( self ):
        if self.parent is None:
            return []
        return [self.parent] + self.parent.getAncestors()

    def getPageLanguage( self ):
        if self.lang is not None:
            return self.lang
        if self.parent is not None:
            return self.parent.getPageLanguage()
        return None

    def setAttributes( self, attrs ):
        if type(attrs) != type({}):
            lwarn( "Attributes are not a dictionary. Page: '{}'".format( self.id ) )
            attrs = {}

        self.attrs = attrs

        if "title" in attrs:
            self.title = attrs["title"]

        if "lang" in attrs:
            self.lang = attrs["lang"]

        if "metaTitle" in attrs:
            self.metaTitle = attrs["metaTitle"]

        if "menu" in attrs:
            self.menuText = attrs["menu"]

        # The order of the item in the menu
        if "weight" in attrs:
            self.weight = attrs["weight"]

        # The type of the processor for the page. Default is "page"
        if "type" in attrs:
            self._pageType = attrs["type"]

        if "template" in attrs:
            self.templateBasename = attrs["template"]

        if "childType" in attrs:
            self._childType = attrs["childType"]

        # Published: published, not isDraft
        if "publish" in attrs:
            self.published = attrs["publish"]
        if "draft" in attrs:
            self.isDraft = attrs["draft"]

        # Expired pages go to archive.
        # The excerpt is shown on index page if: publishDate < today < expireDate
        if "createDate" in attrs:
            self.createDate = attrs["createDate"].toordinal()
        if "expireDate" in attrs:
            self.expireDate = attrs["expireDate"].toordinal()
        if "publishDate" in attrs:
            self.publishDate = attrs["publishDate"].toordinal()
        if "unpublishDate" in attrs:
            self.unpublishDate = attrs["unpublishDate"].toordinal()


    def addExtraAttrs( self, attrDict ):
        for k,v in attrDict.items():
            self.extraAttrs[k] = v

    # Called just before the extra attributes will be written to the output
    def completeExtraAttrs( self, exportData, translatedVars ):
        # Add a title if it does not exist in the attributes
        if "title" not in self.extraAttrs:
            self.extraAttrs["title"] = self.title

        # Use settings from the configuration to build the page meta title
        if "meta-title" not in self.extraAttrs:
            if self.metaTitle is not None:
                meta = self.metaTitle
            elif self.title is not None:
                meta = self.title
            else:
                meta = ""

            config = exportData.config
            hasConfig = config is not None
            meta_prefix = config.getValue( "titlePrefix", "" ) if hasConfig else ""
            meta_suffix = config.getValue( "titleSuffix", "" ) if hasConfig else ""
            self.extraAttrs["meta-title"] = "{}{}{}".format( meta_prefix, meta, meta_suffix )

        if len(translatedVars) > 0:
            trans = exportData.trans
            lang = self.getPageLanguage()
            if lang is None:
                lang = trans.getDefaultLanguage()
            tr = {}
            for var,default in translatedVars.items():
                tr[var] = trans.getTranslation( lang, var, default )
            self.extraAttrs["tr"] = tr


        # Copy original attributes to extra attributes if they are not defined in extra
        for k,v in self.attrs.items():
            if v is not None and not k in self.extraAttrs:
                self.extraAttrs[k] = v

    def getPageType( self ):
        if self._pageType is None:
            p = self.parent
            while p is not None:
                if p._childType is not None:
                    self._pageType = p._childType
                    break
                p = p.parent

            if self._pageType is None:
                self._pageType = "page"

        return self._pageType

    def isPublished( self, dateTime=None  ):
        if not self.zimPage.exists() or not self.published or self.isDraft:
            return False

        if dateTime is None:
            dateTime = self.exportData.now

        if dateTime.toordinal() < self.getPublishDate().toordinal():
            return False

        if self.unpublishDate is not None and dateTime.toordinal() >= self.unpublishDate:
            return False

        if self.parent is not None and not self.parent.isPublished():
            return False

        return True


    def isExpired( self, dateTime=None ):
        if self.expireDate is None:
            return False

        if dateTime is None:
            dateTime = self.exportData.now

        return dateTime.toordinal() >= self.expireDate


    def getCreationDate( self ):
        if self.createDate is not None:
            return datetime.date.fromordinal(self.createDate)

        def makeDate( dt ):
            if dt is None:
                return datetime.date.fromordinal( 1 )
            return datetime.date.fromordinal( dt.toordinal() )

        if self.zimPage._meta is not None and "Creation-Date" in self.zimPage._meta:
            return makeDate(dateparser.parse(self.zimPage._meta["Creation-Date"]))

        return makeDate(self.zimPage.ctime)


    def getPublishDate( self ):
        if self.publishDate is not None:
            return datetime.date.fromordinal(self.publishDate)

        return self.getCreationDate()


    def hasMenuEntry( self ):
        return self.menuText is not None and self.isPublished()

    def getMarkdown( self ):
        """Get the current intermediate markdown text from the exported file."""
        with open( self.fullFilename() ) as f:
            return f.readlines()
        return None


# copy the parent realtions from Page to MarkdownPage
def findPageParents( mkdFiles ):
    for f in mkdFiles:
        if f.zimPage.parent is None or f.zimPage.parent == f.zimPage:
            continue
        for pf in mkdFiles:
            if pf.zimPage == f.zimPage.parent:
                f.parent = pf
                pf.children.append( f )
                break
