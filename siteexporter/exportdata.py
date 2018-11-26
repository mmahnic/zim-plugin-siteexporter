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
from config import getActiveConfiguration
from translation import Translations
from processorfactory import PageTypeProcessorFactory, ProcessorRegistry
import datetime

class ExporterData:
    def __init__( self, notebook ):
        self.notebook = notebook
        self.config = getActiveConfiguration( notebook )
        self.trans = Translations( self.config )
        self.now = datetime.datetime.now()
        self.pageTypeProcFactory = PageTypeProcessorFactory()
        ProcessorRegistry.registerPageTypes( self.pageTypeProcFactory )

