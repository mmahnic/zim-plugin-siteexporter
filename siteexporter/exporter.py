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
import os, sys, re
import shutil
import subprocess as subp

import zim.formats

# REQUIRE: pyyaml
import yaml

from news import NewsPageProcessor, NewsIndexPageProcessor
from templates import TemplateProcessor
import sxpage

import logging
lwarn = logging.warning
lerror = logging.error

pandoccmd = "pandoc"
exportPath = sxpage.exportPath

class IndexEntry:
    def __init__( self, page ):
        self.page = page
        self.parent = None
        self.entries = []

    def level( self ): return self.page.level
    def weight( self ): return self.page.weight
    def menuText( self ): return self.page.menuText


class SiteExporter:
    def __init__(self, exportData):
        self.exportData = exportData
        self.mkdPages = None
        self.config = exportData.config
        self.zimNotebookDir = exportData.notebook.layout.root
        self.layout = None
        self.homepage = None
        self.templateProc = TemplateProcessor()


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
        ext = sxpage.mkdExtension
        layout = MultiFileLayout(dir, ext)
        return MultiFileExporter(layout, template, format, **opts)


    def export(self):
        exporter = self.build_notebook_exporter( exportPath, "Default" )
        from zim.export.selections import AllPages
        pages = AllPages(self.exportData.notebook)

        self.mkdPages = [ sxpage.MarkdownPage( p, self.exportData ) for p in pages if p.exists() ]
        self.findPageParents( self.mkdPages )

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

        templates = set([])
        for page in self.mkdPages:
            templates.add(self.getPageTemplate(page))

        for templateFn in templates:
            self.templateProc.processTemplate(templateFn)

        for page in self.mkdPages:
            if page.isPublished():
                page.completeExtraAttrs( self.exportData, self.templateProc.translatedVars )
                self._writeExtraAttrs( page )

        self.makeHtml( self.mkdPages )
        self.copyFilesToPubDir()


    def layoutPath(self):
        if self.layout is None:
            config = self.config
            self.layout = config.getValue( "layout" )

        if self.layout is None:
            raise Exception( "Value 'layout' is defined on the config page '{}'.".format( config.name ) )

        return os.path.join( exportPath, *self.layout.split(":") )


    def getConfig( self ):
        return self.config


    def getPage( self, pageId ):
        for p in self.mkdPages:
            if p.id == pageId:
                return p

        return None


    def getHomepage( self ):
        if self.homepage is None:
            config = self.getConfig()
            if config is not None and config.hasValue( "home" ):
                self.homepage = self.getPage( config.getValue( "home" ) )
        return self.homepage

    # copy the parent realtions from Page to MarkdownPage
    def findPageParents( self, mkdFiles ):
        for f in mkdFiles:
            if f.zimPage.parent is None or f.zimPage.parent == f.zimPage:
                continue
            for pf in mkdFiles:
                if pf.zimPage == f.zimPage.parent:
                    f.parent = pf
                    break

    def getPageLanguage( self, page ):
        lang = page.getPageLanguage()
        if lang is not None:
            return lang
        return self.config.getDefaultLanguage()

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
        fn = os.path.join( base, "@{}@.{}".format( pageType, ext ) )
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


    def getPageProcessor( self, page ):
        if page.pageType == "news":
            return NewsPageProcessor()
        if page.pageType == "news.index":
            return NewsIndexPageProcessor()
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
        rxlink = re.compile( r"(\]\([^)]+)\." + sxpage.mkdExtension + "\)" )
        for i,line in enumerate(mkdLines):
            mo = rxlink.search( line )
            if mo != None:
                b, e = mo.end(1), mo.end(0)
                mkdLines[i] = line[:b] + "." + sxpage.htmlExtension + ")" + line[e:]

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

        index = { "navindex" : dumpEntries( index.entries, 0 ) }

        # Add a link to homepage to the top-level index
        homepage = self.getHomepage()
        if homepage is not None and homepage.isPublished():
            index[ "home" ] = makeRelative( homepage.htmlFilename )

        return index


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

        mkdLines[0:0] = [ "---\n", "---\n", "\n" ]
        return 1

    def _writeExtraAttrs( self, page ):
        if len(page.extraAttrs) == 0:
            return

        with open( page.fullFilename() ) as f:
            mkdLines = f.readlines()

        yamlPos = self._findYamlInsertionPoint( mkdLines )
        with open( page.fullFilename(), "w" ) as fout:
            fout.write( "".join( mkdLines[:yamlPos] ) )
            fout.write( yaml.dump( { "sx": page.extraAttrs } ) )
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
        config = self.config
        hasConfig = config is not None
        pubdir = config.getValue( "pubdir" ) if hasConfig else None
        if pubdir is None:
            raise Exception( "Value 'pubdir' is not set on the config page '{}'".format( config.configPageId ) )

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

