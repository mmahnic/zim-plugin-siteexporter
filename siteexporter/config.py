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
from zim.notebook.page import Path
from pageattributes import loadYamlAttributes

# The id of the root config page. Different configurations are stored under
# this page. The "active" property of the base config page defines the actual
# config page to use.
configPageId = "00:00.config"
rootConfigPage = None

class Configuration:
    def __init__(self, zimPage, notebook):
        self.notebook = notebook
        self.zimPage = zimPage
        self.attrs = loadYamlAttributes( zimPage )
        self.parent = None
        if self != rootConfigPage and zimPage.parent is not None:
            parent = notebook.get_page( zimPage.parent )
            if parent is not None:
                self.parent = Configuration( parent, notebook )

    @property
    def name( self ):
        return self.zimPage.name

    def hasValue( self, name ):
        if name in self.attrs:
            return True
        return False if self.parent is None else self.parent.hasValue( name )

    def getValue( self, name, default=None ):
        if name in self.attrs:
            return self.attrs[name]
        elif self.parent is not None:
            return self.parent.getValue( name, default )
        else:
            return default


def getActiveConfiguration( notebook ):
    global rootConfigPage, configPageId
    if rootConfigPage is None:
        rootConfigPage = notebook.get_page( Path(configPageId) )

    if rootConfigPage is None or not rootConfigPage.exists():
        raise Exception( "Root Config Page '{}' not found.".format( configPageId ) )

    globalAttrs = loadYamlAttributes( rootConfigPage )
    if "active" in globalAttrs:
        activeId = "{}:{}".format( configPageId, globalAttrs["active"] )
        activeConfigPage = notebook.get_page( Path( activeId ) )
        if activeConfigPage is None or not activeConfigPage.exists():
            raise Exception( "Active Config Page '{}' not found.".format( activeId ) )

        return Configuration( activeConfigPage, notebook )

    return Configuration( rootConfigPage, notebook )
