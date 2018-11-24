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

        rxinclude = re.compile( r"^\s*\[@\s*include\s+([^@\]]+)@\]\s*$" )
        res = []

        for line in lines:
            mo = rxinclude.match( line )
            if mo is None:
                res.append( line )
            else:
                fn = os.path.join( os.path.dirname( templateFilename ), mo.group(1).strip() )
                if not os.path.exists( fn ):
                    res.append( line )
                    res.append( "FAILED: no {}\n".format( fn ) )
                else:
                    with open( fn ) as f:
                        res.extend( f.readlines() )

        rxtranslate = re.compile( r"\[@\s*tr\s+([-_a-zA-Z0-9]+)(\s+[^@\]]+)\s*@\]" )
        lines = res
        res = []

        for line in lines:
            # TODO: replace all matches
            mo = rxtranslate.search( line )
            if mo is None:
                res.append( line )
            else:
                var = mo.group(1)
                default = mo.group(2).strip()
                self.addTranslatedVariable( var, default )
                res.append( "{}$sx.tr.{}${}".format( line[:mo.start()], var, line[mo.end():] ) )

        with open( templateFilename, "w" ) as f:
            f.write( "".join( res ) )


    def addTranslatedVariable( self, var, default ):
        if not var in self.translatedVars:
            self.translatedVars[var] = default
