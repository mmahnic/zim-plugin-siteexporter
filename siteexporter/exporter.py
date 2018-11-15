import os, sys, re
import shutil
import subprocess as subp
import datetime
import dateutil.parser as dateparser
import zim.formats

# REQUIRE: pyyaml
import yaml

from news import NewsPageProcessor

import logging
# ldebug = logging.debug
# linfo = logging.info
lwarn = logging.warning
lerror = logging.error

pandoccmd = "pandoc"
exportPath = "/tmp/site"
mkdExtension = "markdown"
htmlExtension = "html"


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
        self.meta_title = self.title
        self.menuText = None
        self.pageType = "page"
        self.isDraft = False
        self.published = True
        self.createDate = None
        self.expireDate = None
        self.publishDate = None
        self.template = None # "default.html"
        self.style = None # "default.css"
        self.extraAttrs = {}

        self._loadYamlAttributes()


    def _loadYamlAttributes( self ):
        zimLines = self.zimPage.dump(zim.formats.get_format('wiki'))
        yamltext = []
        inYaml = False
        for line in zimLines:
            if inYaml:
                if line.rstrip() in ( "---", "..." ):
                    break
                yamltext.append( line )
            else:
                if line.rstrip() == "---":
                    inYaml = True

        if len(yamltext) > 0:
            self.setAttributes( yaml.safe_load( "".join(yamltext) ) )


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

    def setAttributes( self, attrs ):
        if type(attrs) != type({}):
            lwarn( "Attributes are not a dictionary. Page: '{}'".format( self.id ) )
            attrs = {}

        self.attrs = attrs

        if "title" in attrs:
            self.title = attrs["title"]

        if "meta_title" in attrs:
            self.title = attrs["meta_title"]

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

        # lwarn( "{}: pub {}, weig {}, type {}".format( self.id, self.published, self.weight, self.pageType ))
        # lwarn( "{}".format( dir(self.page) ) )

    def addExtraAttrs( self, attrDict ):
        for k,v in attrDict.items():
            self.extraAttrs[k] = v

    # Called just before the extra attributes will be written to the output
    def completeExtraAttrs( self, configPage ):
        # Add a title if it does not exist in the attributes
        if "title" not in self.attrs and "title" not in self.extraAttrs:
            self.extraAttrs["title"] = self.title

        # Use settings from the configuration to build the page meta title
        if "meta_title" not in self.extraAttrs:
            if self.meta_title is not None:
                meta = self.meta_title
            elif self.title is not None:
                meta = self.title
            else:
                meta = ""

            hasConfig = configPage is not None
            meta_prefix = configPage.attrs["titlePrefix"] \
                    if (hasConfig and "titlePrefix" in configPage.attrs) else ""
            meta_suffix = configPage.attrs["titleSuffix"] \
                    if (hasConfig and "titleSuffix" in configPage.attrs) else ""
            self.extraAttrs["meta_title"] = "{}{}{}".format( meta_prefix, meta, meta_suffix )

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


class IndexEntry:
    def __init__( self, page ):
        self.page = page
        self.parent = None
        self.entries = []

    def level( self ): return self.page.level
    def weight( self ): return self.page.weight
    def menuText( self ): return self.page.menuText


class SiteExporter:
    def __init__(self):
        self.mkdPages = None
        self.configPage = None
        self.layout = None
        self.configPageId = "00:00.config"
        self.zimNotebookDir = None


    # from zim.export
    def build_notebook_exporter(self, dir, template, **opts):
        '''Returns an L{Exporter} that is suitable for exporting a whole
        notebook to a folder with one file per page.
        '''
        from zim.fs import Dir, File
        from zim.templates import get_template
        from zim.formats import get_format
        from zim.export.layouts import MultiFileLayout
        from zim.export.exporters.files import MultiFileExporter

        dir = Dir(dir)
        format = "markdown"

        template = get_template(format, template)
        ext = mkdExtension # get_format(format).info['extension']
        layout = MultiFileLayout(dir, ext)
        return MultiFileExporter(layout, template, format, **opts)


    def export(self, notebook):
        self.zimNotebookDir = notebook.layout.root
        exporter = self.build_notebook_exporter( exportPath, "Default" )
        from zim.export.selections import AllPages
        pages = AllPages(notebook)

        self.mkdPages = [ MarkdownPage( p ) for p in pages if p.exists() ]
        self.findPageParents( self.mkdPages )
        config = self.getConfigPage()

        # The iterator returns the page BEFORE it is exported :/
	for p in exporter.export_iter(pages):
            lwarn( "Exporting: {}: {}".format( type(p), p ) )

	for page in self.mkdPages:
            lwarn( "Process: {}".format( page ) )
            self.processExportedPage( page )

	for page in self.mkdPages:
            processor = self.getPageProcessor( page )
            if processor is not None:
                newfiles = []
                processor.digest( page, self.mkdPages, newfiles )

        index = self.createPageIndex( self.mkdPages )

        for page in self.mkdPages:
            if page.isPublished():
                self.addPageIndex( page, index )
                self.addPageStyle( page )

        for page in self.mkdPages:
            if page.isPublished():
                page.completeExtraAttrs( config )
                self._writeExtraAttrs( page )

        templates = set([])
        for page in self.mkdPages:
            templates.add(self.getPageTemplate(page))

        for templateFn in templates:
            self.preprocessTemplate(templateFn)

        self.makeHtml( self.mkdPages )
        self.copyFilesToPubDir()


    def layoutPath(self):
        if self.layout is None:
            config = self.getConfigPage()
            if "layout" in config.attrs:
                self.layout = config.attrs["layout"]

        if self.layout is None:
            raise Exception( "No layout is defined in the config page '{}'.".format( self.configPageId ) )

        return os.path.join( exportPath, *self.layout.split(":") )


    def getConfigPage( self ):
        if self.configPage is None:
            self.configPage = self.getPage( self.configPageId )

        if self.configPage is None:
            raise Exception( "Config page '{}' not found.".format( self.configPageId ) )

        return self.configPage


    def getPage( self, pageId ):
        for p in self.mkdPages:
            if p.id == pageId:
                return p

        return None


    # copy the parent realtions from Page to MarkdownPage
    def findPageParents( self, mkdFiles ):
        for f in mkdFiles:
            if f.zimPage.parent is None or f.zimPage.parent == f.zimPage:
                continue
            for pf in mkdFiles:
                if pf.zimPage == f.zimPage.parent:
                    f.parent = pf
                    break


    # Layout file: template, css, ...
    def _discoverLayoutFile( self, page, ext ):
        base = self.layoutPath()

        # Layout file for a specific page
        name = ".".join( page.path ) + "." + ext
        fn = os.path.join( base, name )
        if os.path.exists( fn ):
            return fn

        # Layout file for a specific page type
        pageType = page.pageType
        fn = os.path.join( base, "({}).{}".format( pageType, ext ) )
        if os.path.exists( fn ):
            return fn

        # Default layout file
        fn = os.path.join( base, "default.{}".format( ext ) )
        if os.path.exists( fn ):
            return fn

        return None


    def getPageTemplate( self, page ):
        if page.template is None:
            page.template = self._discoverLayoutFile( page, "html5" )
            if page.template is None:
                pate.template = "default.html5"
        return page.template


    def getPageStyleFile( self, page ):
        if page.style is None:
            page.style = self._discoverLayoutFile( page, "css" )
            if page.style is None:
                pate.style = "default.css"
        return page.style


    # Process [@ ... @] instructions in the template. TODO: move to a class
    def preprocessTemplate( self, templateFilename ):
        if not os.path.exists( templateFilename ):
            return
        with open( templateFilename ) as f:
            lines = f.readlines()

        rxinclude = re.compile( r"^\s*\[@\s*include\s+([^@\]]+)@\]\s*$" )
        res = []

        for line in lines:
            mo = rxinclude.match( line )
            if mo is None:
                res.append( line )
            else:
                fn = os.path.join( os.path.dirname( templateFilename ), mo.group(1).strip() )
                if not os.path.exists( fn ):
                    res.append( line )
                    res.append( "FAILED: no {}\n".format( fn ) )
                else:
                    with open( fn ) as f:
                        res.extend( f.readlines() )

        with open( templateFilename, "w" ) as f:
            f.write( "".join( res ) )


    def getPageProcessor( self, page ):
        if page.pageType == "news":
            return NewsPageProcessor()

        return None


    def processExportedPage( self, page ):
        with open( page.fullFilename() ) as f:
            mkdLines = f.readlines()

        if len(mkdLines) == 0:
            return

        if mkdLines[0].startswith( "#" ):
            mkdLines = mkdLines[1:]

        mkdLines = self.fixExportedLinks( mkdLines )

        with open( page.fullFilename(), "w" ) as fout:
            fout.write( "".join( mkdLines ) )


    def fixExportedLinks( self, mkdLines ):
        rxlink = re.compile( r"(\]\([^)]+)\." + mkdExtension + "\)" )
        for i,line in enumerate(mkdLines):
            mo = rxlink.search( line )
            if mo != None:
                b, e = mo.end(1), mo.end(0)
                mkdLines[i] = line[:b] + "." + htmlExtension + ")" + line[e:]

        return mkdLines


    def createPageIndex( self, mkdFiles ):
        entries = [ IndexEntry(page) for page in mkdFiles if page.hasMenuEntry() ]
        entries.sort( key=lambda p: (p.level(), p.weight(), p.menuText()) )

        # Find parent relations by page id
        for e in entries:
            for l in range(e.level()):
                pid = e.page.parentId( l+1 )
                if len(pid) == 0:
                    break
                for p in entries:
                    if p.page.id == pid:
                        e.parent = p
                        p.entries.append( e )
                        break
                if e.parent is not None:
                    break

        index = IndexEntry( None )
        index.entries = [ e for e in entries if e.parent is None ]

        return index


    def _renderYamlIndex( self, page, index ):
        curDir = os.path.dirname( page.htmlFilename )
        def makeRelative( path ):
            return os.path.relpath( path, curDir )

        navindex = []
        def dumpEntries( entries, level ):
            index = []
            for e in entries:
                ie = {
                        "id": e.page.id,
                        "display": e.page.menuText,
                        "link": makeRelative(e.page.htmlFilename)
                        }
                if len(e.entries) > 0:
                    ie["items"] = dumpEntries( e.entries, level+1 )

                index.append( ie )

            return index

        return { "navindex": dumpEntries( index.entries, 0 ) }


    # Find a point for inserting generated code, eg. the index.
    # Currently this is just after the yaml block if it starts in the first 10 lines.
    def _findYamlInsertionPoint( self, mkdLines ):
        for i,line in enumerate(mkdLines):
            if i > 10:
                break
            if line.rstrip() != "---":
                continue
            j = i+1
            while j < len(mkdLines):
                line = mkdLines[j].rstrip()
                if line == "---" or line == "...":
                    return j
                j += 1
            break

        mkdLines.insert( 0, [ "---\n", "---\n", "\n" ])
        return 1

    def _writeExtraAttrs( self, page ):
        if len(page.extraAttrs) == 0:
            return

        with open( page.fullFilename() ) as f:
            mkdLines = f.readlines()

        yamlPos = self._findYamlInsertionPoint( mkdLines )
        with open( page.fullFilename(), "w" ) as fout:
            fout.write( "".join( mkdLines[:yamlPos] ) )
            fout.write( yaml.dump( page.extraAttrs ) )
            fout.write( "".join( mkdLines[yamlPos:] ) )


    def addPageIndex( self, page, index ):
        if index is None or len(index.entries) == 0:
            return

        page.addExtraAttrs( self._renderYamlIndex(page, index) )


    def addPageStyle( self, page ):
        style = self.getPageStyleFile( page )
        if style is None:
            return

        curDir = os.path.dirname( page.fullHtmlFilename() )
        def makeRelative( path ):
            return os.path.relpath( path, curDir )

        page.addExtraAttrs( { "main-css": makeRelative( style ) } )


    def makeHtml( self, mkdFiles ):
        command = [ pandoccmd, "-f", "markdown+raw_html", "-t", "html5" ]
        command += [ "--standalone" ]
        command += [ "--section-divs" ]

        for page in mkdFiles:
            if not page.isPublished():
                continue

            template = self.getPageTemplate( page )
            mkdpath = page.fullFilename()
            outpath = page.fullHtmlFilename()
            filenames = ["-o",  outpath, mkdpath ]
            cmd = command + [ "--template", template ] + filenames
            lwarn( " ".join(cmd) )
            subp.call(cmd)


    def copyFilesToPubDir( self ):
        config = self.getConfigPage()
        pubdir = config.attrs["pubdir"] if "pubdir" in config.attrs else None
        if pubdir is None:
            raise Exception( "pubdir is not set on page {}", self.configPageId )

        if not os.path.isabs( pubdir ):
            pubdir = os.path.normpath( os.path.join( self.zimNotebookDir.encodedpath, pubdir ) )

        if not os.path.exists( pubdir ):
            os.makedirs( pubdir )

        def getHtmlLinks( fn ):
            html = open( fn ).read()
            rxLink =  re.compile( r'''(src|href)="([^"]+)"''' )
            return set([ mo.group(2) for mo in rxLink.finditer( html ) ])

        def getCssLinks( fn ):
            css = open( fn ).read()
            rxLink =  re.compile( r'''url\s*\(\s*["']?([^'")]+)["']?\s*\)''' )
            return set([ mo.group(1) for mo in rxLink.finditer( css ) ])

        def recurseCssLinks( link, basedir, resources ):
            cssfn = os.path.normpath( os.path.join( basedir, link ) )
            cssdir = os.path.dirname( cssfn )
            cssurls = getCssLinks( cssfn )
            for url in cssurls:
                ressrc = os.path.normpath( os.path.join( cssdir, url ) )
                if os.path.exists( ressrc ) and not ressrc in resources:
                    resources.add( os.path.relpath( ressrc, exportPath ) )
                    if url.endswith( ".css" ):
                        recurseCssLinks( url, cssdir, resources )

        # Discover pages and resources to copy
        pages = set()
        resources = set()
        for page in self.mkdPages:
            if not page.isPublished():
                continue

            pages.add( os.path.relpath( page.fullHtmlFilename(), exportPath ) )

            links = getHtmlLinks( page.fullHtmlFilename() )
            for link in links:
                if link.endswith( ".html" ):
                    continue
                htmldir = os.path.dirname( page.fullHtmlFilename() )
                ressrc = os.path.normpath( os.path.join( htmldir, link ) )
                if not os.path.exists( ressrc ):
                    continue

                resources.add( os.path.relpath( ressrc, exportPath ) )

                if link.endswith( ".css" ):
                    recurseCssLinks( link, htmldir, resources )

        filesToCopy = pages.union(resources)

        # Remove destination files that are not in pages + resources
        for root, dirs, files in os.walk( pubdir ):
            for fn in files:
                destfn = os.path.join( root, fn )
                relfn = os.path.relpath( destfn, pubdir )
                if not relfn in filesToCopy:
                    os.remove( destfn )

        # Copy the discovered pages and resources
        for res in filesToCopy:
            ressrc = os.path.join( exportPath, res )
            resdst = os.path.join( pubdir, res )
            if not os.path.exists( os.path.dirname( resdst ) ):
                os.makedirs( os.path.dirname( resdst ) )
            shutil.copyfile( ressrc, resdst )

