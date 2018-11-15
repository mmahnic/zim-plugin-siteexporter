# -*- coding: utf-8 -*-

from zim.plugins import PluginClass, WindowExtension, extends
from zim.actions import action
from zim.applications import Application

from .exporter import SiteExporter, pandoccmd

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
        exporter = SiteExporter()
        exporter.export(self.window.ui.notebook)
        pass
