import zim.formats

# REQUIRE: pyyaml
import yaml

# Extract the YAML attributes from a page

def loadYamlAttributes( page ):
    zimLines = page.dump(zim.formats.get_format('wiki'))
    yamltext = []
    inYaml = False
    for line in zimLines:
        if inYaml:
            if line.rstrip() in ( "---", "..." ):
                break
            yamltext.append( line )
        else:
            if line.rstrip() == "---":
                inYaml = True

    if len(yamltext) > 0:
        return yaml.safe_load( "".join(yamltext) )

    return {}
