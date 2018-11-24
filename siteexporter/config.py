from zim.notebook.page import Path
from pageattributes import loadYamlAttributes
import locale

import logging
lwarn = logging.warning
lerror = logging.error

# The id of the root config page. Different configurations are stored under
# this page. The "active" property of the base config page defines the actual
# config page to use.
configPageId = "00:00.config"
rootConfigPage = None

class Configuration:
    def __init__(self, zimPage, notebook):
        self.notebook = notebook
        self.translations = None
        self.zimPage = zimPage
        self.attrs = loadYamlAttributes( zimPage )
        self.parent = None
        if zimPage.parent is not None:
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

    def getDefaultLanguage( self ):
        if self.hasValue( "lang" ):
            return self.getValue( "lang" )
        return locale.getdefaultlocale()[0][:2]

    # TODO: Move translation management into a separate class
    def getTranslation( self, lang, var, default ):
        if self.translations is None:
            self.translations = {}
        if not lang in self.translations:
            self.translations[lang] = self._loadTranslations( lang )
        if var in self.translations[lang]:
            return self.translations[lang][var]
        return default

    def _loadTranslations( self, lang ):
        tr = self._loadConfigTranslations( lang )
        if self.hasValue( "layout" ):
            zimLayoutPage = self.notebook.get_page( Path(self.getValue("layout")) )
            if zimLayoutPage is not None and zimLayoutPage.exists():
                trLayout = self._loadLayoutTranslations( zimLayoutPage, lang )
                for k,v in trLayout.items():
                    tr[k] = v

        return tr

    def _loadConfigTranslations( self, lang ):
        # Get parent config translations
        if self.parent is not None:
            tr = self.parent._loadConfigTranslations( lang )
        else:
            tr = {}

        # Merge translations with parent translations
        langPageId = "{}:lang-{}".format( self.zimPage.name, lang )
        zimLangPage = self.notebook.get_page( Path(langPageId) )
        if zimLangPage is not None and zimLangPage.exists():
            attrs = loadYamlAttributes( zimLangPage )
            for k,v in attrs.items():
                tr[k] = v
            lwarn( "Found page: {}".format( langPageId ) )
        else:
            lwarn( "No such page: {}".format( langPageId ) )

        return tr

    def _loadLayoutTranslations( self, page, lang ):
        # Get parent layout translations
        if page.name != "00" and page.parent is not None:
            tr = self._loadLayoutTranslations( page.parent, lang )
        else:
            tr = {}

        langPageId = "{}:lang-{}".format( page.name, lang )
        zimLangPage = self.notebook.get_page( Path(langPageId) )
        if zimLangPage is not None and zimLangPage.exists():
            attrs = loadYamlAttributes( zimLangPage )
            for k,v in attrs.items():
                tr[k] = v
            lwarn( "Found page: {}".format( langPageId ) )
        else:
            lwarn( "No such page: {}".format( langPageId ) )

        return tr


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
