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

class ResourceFinder:
    def __init__( self, config, exportPath ):
        self.config = config
        self.exportPath = exportPath
        self.layout = None

    def layoutPath( self ):
        if self.layout is None:
            config = self.config
            self.layout = config.getValue( "layout" )

        if self.layout is None:
            raise Exception( "Value 'layout' is not defined on the config page '{}'.".format( self.config.name ) )

        return os.path.join( self.exportPath, *self.layout.split(":") )

    # Layout file: template, css, ...
    def _discoverLayoutFile( self, page, ext ):
        base = self.layoutPath()

        # Layout file for a specific page
        if page.templateBasename is not None:
            fn = os.path.join( base, "{}.{}".format( page.templateBasename, ext ) )
            if os.path.exists( fn ):
                return fn

        # Layout file for a specific page type
        pageType = page.getPageType()
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


    def getResourceFile( self, filename ):
        if filename is None:
            return None

        base = self.layoutPath()

        fn = os.path.join( base, filename )
        if os.path.exists( fn ):
            return fn

        return None
