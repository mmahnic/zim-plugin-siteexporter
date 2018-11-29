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


# Instances of derived classes will be created by the ProcessorFactory.
class Processor(object):
    pass


# Instances of derived classes will be created and called to register the
# processors for the (default) supported page types.
class ProcessorRegistry(object):
    @staticmethod
    def registerPageTypes( pageTypeProcFactory ):
        for p in ProcessorRegistry.__subclasses__():
            return p.__call__().registerPageTypes( pageTypeProcFactory )


class ProcessorFactory:
    @staticmethod
    def getProcessor( klassName ):
        for p in Processor.__subclasses__():
            if p.__name__ == klassName:
                return p.__call__()

        return None


class PageTypeProcessorFactory:
    def __init__(self):
        self.pageProcessor = {}

    def getProcessor( self, pageType ):
        if pageType in self.pageProcessor:
            return ProcessorFactory.getProcessor( self.pageProcessor[ pageType ] )

        return None


    def getProcessorName( self, pageType ):
        if pageType in self.pageProcessor:
            return self.pageProcessor[ pageType ]

        return None


    # Registering processors by class name will allow us to define new types of pages in the
    # configuration pages or use different processors for known page types.
    def registerPageType( self, pageType, processorKlassName ):
        self.pageProcessor[pageType] = processorKlassName

