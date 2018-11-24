from config import getActiveConfiguration
from translation import Translations

class ExporterData:
    def __init__( self, notebook ):
        self.notebook = notebook
        self.config = getActiveConfiguration( notebook )
        self.trans = Translations( self.config )

