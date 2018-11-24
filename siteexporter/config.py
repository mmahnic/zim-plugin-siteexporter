from zim.notebook.page import Path
from pageattributes import loadYamlAttributes
from translation import Translations
import locale

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

    def getDefaultLanguage( self ):
        if self.hasValue( "lang" ):
            return self.getValue( "lang" )
        return locale.getdefaultlocale()[0][:2]

    def getTranslation( self, lang, var, default ):
        if self.translations is None:
            self.translations = Translations( self )

        return self.translations.getTranslation( lang, var, default )


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
