# -*- coding: utf-8 -*-

from zim.plugins import PluginClass, WindowExtension, extends
from zim.actions import action

from .exporter import SiteExporter

class SiteExporterPlugin( PluginClass ):
    plugin_info = {
        'name': _('Site Exporter'),
        'description': _('''\
        This plugin allows you to export a notebook and call an external
        program to process it further.'''),
        'author': 'Marko Mahnič',
        'help': '',
        }


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
