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
import os, re

class TemplateProcessor:
    def __init__(self):
        # Variables that need translations in Pandoc templates
        self.translatedVars = {}

    def processTemplate( self, templateFilename ):
        if not os.path.exists( templateFilename ):
            return
        with open( templateFilename ) as f:
            lines = f.readlines()

        lines = self.includeTemplateChunks( lines, os.path.dirname( templateFilename ) )
        lines = self.prepareTranslatedVariables( lines )

        with open( templateFilename, "w" ) as f:
            f.write( "".join( lines ) )


    def includeTemplateChunks( self, lines, baseDir ):
        rxinclude = re.compile( r"^\s*\[@\s*include\s+([^@\]]+)@\]\s*$" )
        res = []

        for line in lines:
            mo = rxinclude.match( line )
            if mo is None:
                res.append( line )
            else:
                fn = os.path.join( baseDir, mo.group(1).strip() )
                if not os.path.exists( fn ):
                    res.append( line )
                    res.append( "FAILED: no {}\n".format( fn ) )
                else:
                    with open( fn ) as f:
                        res.extend( f.readlines() )
        return res


    # Rewrite [@ tr var default @] --> $sx.tr.var$ and register the variables in translatedVars.
    def prepareTranslatedVariables( self, lines ):
        rxtranslate = re.compile( r"\[@\s*tr\s+([-_a-zA-Z0-9]+)(\s+[^@\]]+)\s*@\]" )

        def markTranslation( mo ):
            var = mo.group(1)
            default = mo.group(2).strip()
            self.addTranslatedVariable( var, default )
            return  "$sx.tr.{}$".format( var )

        return [ rxtranslate.sub( markTranslation, line ) for line in lines ]


    def addTranslatedVariable( self, var, default ):
        if not var in self.translatedVars:
            self.translatedVars[var] = default
