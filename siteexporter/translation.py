from zim.notebook.page import Path
from pageattributes import loadYamlAttributes

import logging
lwarn = logging.warning
lerror = logging.error

class Translations:
    """Read translations from YAML attributes of lang-xx pages stored
       in current configuration an current layout tree."""
    # TODO: What is the best place to store translations?

    def __init__( self, config ):
        self.config = config
        self.translations = {}


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
