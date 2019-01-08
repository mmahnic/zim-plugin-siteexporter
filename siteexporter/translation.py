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
import locale

import logging
lwarn = logging.warning
lerror = logging.error

class Translations:
    """Read translations from YAML attributes of lang-xx pages stored
       in the current configuration and layout trees."""

    def __init__( self, config ):
        self.config = config
        self.translations = {}


    def getDefaultLanguage( self ):
        if self.config.hasValue( "lang" ):
            return self.config.getValue( "lang" )
        return locale.getdefaultlocale()[0][:2]


    def getTranslation( self, lang, var, default ):
        if not lang in self.translations:
            self.translations[lang] = self._loadTranslations( lang )
        if var in self.translations[lang]:
            return self.translations[lang][var]
        return default


    def _loadTranslations( self, lang ):
        config = self.config
        tr = self._loadTranslationsRec( config.zimPage, lang )
        if config.hasValue( "layout" ):
            zimLayoutPage = config.notebook.get_page( Path(config.getValue("layout")) )
            if zimLayoutPage is not None and zimLayoutPage.exists():
                trLayout = self._loadTranslationsRec( zimLayoutPage, lang )
                for k,v in trLayout.items():
                    tr[k] = v

        return tr

    def _loadTranslationsRec( self, page, lang ):
        # Ignore the root page
        if page.parent is None:
            return {}

        # Get parent layout translations
        tr = self._loadTranslationsRec( page.parent, lang )

        langPageId = "{}:lang-{}".format( page.name, lang )
        zimLangPage = self.config.notebook.get_page( Path(langPageId) )
        if zimLangPage is not None and zimLangPage.exists():
            attrs = loadYamlAttributes( zimLangPage )
            for k,v in attrs.items():
                tr[k] = v
            lwarn( "Found page: {}".format( langPageId ) )
        else:
            lwarn( "No such page: {}".format( langPageId ) )

        return tr
