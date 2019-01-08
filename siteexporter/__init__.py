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

import logging
logger = logging.getLogger('zim.plugins.siteexporter')

from zim.plugins import PluginClass, WindowExtension, extends
from zim.actions import action
from zim.applications import Application

from zim.notebook import Notebook, Path, resolve_notebook, build_notebook
try:
    from zim.command import Command
    from zim.ipc import start_server_if_not_running, ServerProxy
    class ZimInterface:
        def __init__(self, notebookInfo):
            start_server_if_not_running()
            self.server = ServerProxy()
            self.ui = server.get_notebook(notebookInfo, False)
            self.notebook = self.ui.notebook

except:
    from zim.main.command import GtkCommand as Command
    from zim.main import ZIM_APPLICATION
    class ZimInterface:
        def __init__(self, notebookInfo):
            self.server = ZIM_APPLICATION
            self.notebook = build_notebook( notebookInfo )
            if self.notebook is None:
                logger.warn( "No notebook. Could not build one." )
            else:
                self.notebook = self.notebook[0]


from .exporter import SiteExporter, pandoccmd
from .exportdata import ExporterData

# This will register the news processors with the processor registry.
import news

try:
    import yaml
except:
    yaml = None

class SiteExporterPlugin( PluginClass ):
    plugin_info = {
        'name': _('Site Exporter'),
        'description': _('''\
This plugin will export a notebook as markdown and process the exported \
pages with pandoc.  Notebook pages can have YAML attributes and a \
different pandoc template can be selected to render each page based \
on the values of these attributes.'''),
        'author': 'Marko Mahnič',
        'help': '',
        }

    @classmethod
    def check_dependencies(klass):
        has_pandoc = Application(pandoccmd).tryexec()
        has_pyyaml = yaml is not None
        return all([has_pandoc, has_pyyaml]), [
                ("Pandoc", has_pandoc, True),
                ("pyyaml", has_pyyaml, True)
                ]


@extends('MainWindow')
class MainWindowExtension(WindowExtension):
    uimanager_xml = '''
        <ui>
        <menubar name='menubar'>
            <menu action='tools_menu'>
                <placeholder name='plugin_items'>
                    <menuitem action='exportSite'/>
                </placeholder>
            </menu>
        </menubar>
        </ui>
        '''

    @action(_('E_xport Site')) # T: menu item
    def exportSite(self):
        """Export Notebook"""
        exporter = SiteExporter(ExporterData(self.window.ui.notebook))
        exporter.export()
        pass


class SiteExporterCommand(Command):
    def run(self):
        # print(self.opts, self.args, dir(self))
        notebookInfo = resolve_notebook(self.args[0])
        zi = ZimInterface( notebookInfo )
        exporter = SiteExporter(ExporterData(zi.notebook))
        exporter.export()
