import os, sys, re
import subprocess as subp

# REQUIRE: pyyaml
import yaml

from news import NewsPageProcessor

import logging
# ldebug = logging.debug
# linfo = logging.info
lwarn = logging.warning
lerror = logging.error

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
        self.title = self.path[-1]
        self.menuText = None
        self.pageType = "page"
        self.published = True
        self.template = None # "default.html"
        self.style = None # "default.css"
        self.extraAttrs = {}


    def fullFilename(self):
        return os.path.join(exportPath, self.filename)

    def fullHtmlFilename(self):
        return os.path.join(exportPath, self.htmlFilename)

    def parentId( self, levels=1 ):
        return ":".join( self.path[:-levels] )

    def isChildOf( self, page ):
        if len(self.path) <= len(page.path):
            return False
        for a,b in zip(self.path, page.path):
            if a != b:
                return False
        return True

    def setAttributes( self, attrs ):
        if type(attrs) != type({}):
            lwarn( "Attributes are not a dictionary. Page: '{}'".format( self.id ) )
            attrs = {}

        self.attrs = attrs

        if "title" in attrs:
            self.title = attrs["title"]
        else:
            self.title = self.path[-1]

        if "menu" in attrs:
            self.menuText = attrs["menu"]
        else:
            self.menuText = None

        self.weight = attrs["weight"] if "weight" in attrs else 999999
        self.published = attrs["publish"] if "publish" in attrs else True
        self.pageType = attrs["type"] if "type" in attrs else "page"

        # lwarn( "{}: pub {}, weig {}, type {}".format( self.id, self.published, self.weight, self.pageType ))
        # lwarn( "{}".format( dir(self.page) ) )

    def addExtraAttrs( self, attrDict ):
        for k,v in attrDict.items():
            self.extraAttrs[k] = v

    def isPublished( self ):
        return self.published and (self.parent is None or self.parent.isPublished())

    def hasMenuEntry( self ):
        return self.menuText is not None and self.isPublished()


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
        # TODO: read from 00:00.config yaml
        # self.layout = "00:layout:simple"
        self.layout = "00:layout:w3css"
        pass

    def layoutPath(self):
        return os.path.join( exportPath, *self.layout.split(":") )

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
        exporter = self.build_notebook_exporter( exportPath, "Default" )
        from zim.export.selections import AllPages
        pages = AllPages(notebook)

        mkdFiles = []
        # The iterator returns the page BEFORE it is exported :/
	for p in exporter.export_iter(pages):
            lwarn( "{}: {}".format( type(p), p ) )
            try:
                page = MarkdownPage(p)
                lwarn( "Append: {}".format( p ) )
                mkdFiles.append( page )
            except:
                continue

        self.findPageParents( mkdFiles )

	for page in mkdFiles:
            lwarn( "Process: {}".format( page ) )
            self.processExportedPage( page )

	for page in mkdFiles:
            processor = self.getPageProcessor( page )
            if processor is not None:
                newfiles = []
                processor.digest( page, mkdFiles, newfiles )

        index = self.createPageIndex( mkdFiles )

        for page in mkdFiles:
            if page.isPublished():
                self.addPageIndex( page, index )
                self.addPageStyle( page )

        for page in mkdFiles:
            if page.isPublished():
                self._writeExtraAttrs( page )

        templates = set([])
        for page in mkdFiles:
            templates.add(self.getPageTemplate(page))

        for templateFn in templates:
            self.preprocessTemplate(templateFn)

        self.makeHtml( mkdFiles )


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

        self.loadPageAttributes( page, mkdLines )

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


    def loadPageAttributes( self, page, mkdLines ):
        yamltext = []
        inYaml = False
        for line in mkdLines:
            if inYaml:
                if line.rstrip() in ( "---", "..." ):
                    break
                if len(line.strip()) > 0:
                    yamltext.append( line )
            else:
                if line.rstrip() == "---":
                    inYaml = True
        if len(yamltext) > 0:
            page.setAttributes( yaml.safe_load( "".join(yamltext) ) )


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
                        "title": e.page.menuText,
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
        command = [ "pandoc", "-f", "markdown+raw_html", "-t", "html5" ]
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

