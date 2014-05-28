#!/usr/bin/env python

# Copyright (C) 2014 MET Norway (met.no)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import commands, datetime, glob, os, sys
from xml.etree import ElementTree

template = """# Created by %(program)s on %(date time)s

output = PNG

colour = COLOUR
buffersize = %(width)ix%(height)i
# papersize = A4
orientation = PORTRAIT
filename = %(output file)s
setupfile = %(setup file)s

MULTIPLE.PLOTS = %(rows)i,%(columns)i,5,5"""

plot_template = """
settime = %(plot time)s
PLOTCELL = %(row)i,%(column)i

PLOT
MAP backcolour=white map=Gshhs-Auto contour=on cont.colour=black cont.linewidth=1 cont.linetype=solid cont.zorder=1 land=on land.colour=flesh land.zorder=0 lon=off lat=off frame=off
AREA name=Europa
LABEL text="Date: %%Y-%%m-%%d %%H:%%M:%%S" valign=top fcolour=220:220:220:160 fontsize=12
#LABEL data
DRAWING file=%(kml file)s
ENDPLOT
"""

def create_input_files(setup_file, directory):

    for path in glob.glob(os.path.join(directory, "*.kml")):
    
        path = os.path.abspath(path)
        stem, suffix = os.path.splitext(path)
        input_file = stem + os.extsep + "input"
        output_file = stem + os.extsep + "png"
        
        tree = ElementTree.parse(path)
        root = tree.getroot()
        times = map(lambda element: element.text, root.findall(".//{http://www.opengis.net/kml/2.2}begin"))
        
        rows = (len(times) + 1)/2
        columns = min(len(times), 2)

        width = 400 * columns
        height = 400 * rows
        
        details = {
            "program": sys.argv[0],
            "date time": datetime.datetime.now().isoformat(" "),
            "width": width,
            "height": height,
            "output file": output_file,
            "setup file": setup_file,
            "rows": rows,
            "columns": columns
            }
        
        f = open(input_file, "w")
        f.write(template % details)
        
        row = 0
        column = 0
        
        for time in times:
        
            details = {
                "plot time": time,
                "row": row,
                "column": column,
                "kml file": path
                }
            f.write(plot_template % details)
            column = (column + 1) % 2
            if column == 0:
                row += 1
        
        f.close()

def run_bdiana(bdiana, directory):

    for input_file in glob.glob(os.path.join(directory, "*.input")):

        if os.system(commands.mkarg(bdiana) + " -i " + commands.mkarg(input_file)) != 0:
            break


if __name__ == "__main__":

    if len(sys.argv) != 4:
        sys.stderr.write("Usage: %s <bdiana executable> <setup file> <directory containing KML files>\n" % sys.argv[0])
        sys.exit(1)
    
    bdiana = sys.argv[1]
    setup_file = sys.argv[2]
    directory = sys.argv[3]

    create_input_files(setup_file, directory)
    run_bdiana(bdiana, directory)
    sys.exit()

