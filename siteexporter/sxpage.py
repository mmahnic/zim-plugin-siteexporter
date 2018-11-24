import os
import datetime
import dateutil.parser as dateparser

from pageattributes import loadYamlAttributes

mkdExtension = "markdown"
htmlExtension = "html"
exportPath = "/tmp/site" # TODO: depends on the system, may be configured by the user, may include notebook name

class MarkdownPage:
    def __init__( self, zimPage ):
        """@p filename is relative to exportPath."""
        self.zimPage = zimPage
        self.path = zimPage.parts # a list of parts that compose the path
        self.filename = "{}.{}".format( "/".join(self.path), mkdExtension )
        self.htmlFilename = "{}.{}".format("/".join(self.path), htmlExtension)
        self.attrs = {}
        self.parent = None

        self.id = ":".join(self.path)
        self.level = len(self.path)
        self.weight = 999999
        self.title = self.zimPage.get_title()
        self.lang = None
        self.metaTitle = self.title
        self.menuText = None
        self.pageType = "page"
        self.isDraft = False
        self.published = True
        self.createDate = None
        self.expireDate = None
        self.publishDate = None
        self.template = None
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

    def getParentIds( self ):
        if len(self.path) < 2:
            return []
        return [ self.parentId(i) for i in range(1, len(self.path)) ]

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
            self.pageType = attrs["type"]

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

    def isPublished( self ):
        return self.published and not self.isDraft and (self.parent is None or self.parent.isPublished())

    def isExpired( self, dateTime ):
        if self.expireDate is None:
            return False
        return dateTime.toordinal() >= self.expireDate

    def getCreationDate( self ):
        if self.createDate is not None:
            return datetime.date.fromordinal(self.createDate)

        def makeDate( dt ):
            return datetime.date.fromordinal( dt.toordinal() )

        if "Creation-Date" in self.zimPage._meta:
            return makeDate(dateparser.parse(self.zimPage._meta["Creation-Date"]))

        return makdDate(self.zimPage.ctime())


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

