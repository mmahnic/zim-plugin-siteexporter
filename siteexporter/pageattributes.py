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
