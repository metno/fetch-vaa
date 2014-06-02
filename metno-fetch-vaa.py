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

import commands, HTMLParser, os, sys, urllib2, urlparse

default_url = "http://www.meteo.fr/vaac/evaa.html"

class Parser(HTMLParser.HTMLParser):

    def __init__(self):
    
        HTMLParser.HTMLParser.__init__(self)
        self.href = ""
        self.text = ""
    
    def feed(self, data):

        self.anchors = []
        HTMLParser.HTMLParser.feed(self, data)
    
    def handle_starttag(self, tag, attrs):
    
        if tag == "a":
            d = dict(attrs)
            try:
                self.href = d["href"]
            except KeyError:
                pass
            self.text = ""

    def handle_data(self, data):
    
        if self.href:
            self.text += data
    
    def handle_endtag(self, tag):

        if tag == "a":
            self.anchors.append((self.href, self.text))
            self.href = ""


if __name__ == "__main__":

    args = sys.argv[:]
    gui = "--gui" in args
    if gui:
        args.remove("--gui")
    
    if len(args) == 2:
        output_dir = args[1]
    elif len(args) == 1:
        output_dir = os.path.join(os.getenv("HOME"), ".diana", "work")
    else:
        sys.stderr.write("Usage: %s [--gui] [download directory]\n" % args[0])
        sys.exit(1)
    
    if not os.path.isdir(output_dir):
        text = "Download directory '%s' not found." % output_dir
        if gui:
            os.system('zenity --error --text="%s"' % text)
        else:
            sys.stderr.write(text + "\n")
        sys.exit(1)
    
    url = default_url
    
    html = urllib2.urlopen(url).read()
    p = Parser()
    p.feed(html)
    p.close()
    
    count = 0
    for href, text in p.anchors:
        if text.endswith("UTC"):
            vaa_url = urlparse.urljoin(url, href)
            file_name = href.split("/")[-1]

            # Process the file name to get the embedded time information.
            # This is currently unused.
            pieces = file_name.split(".")
            time_str = pieces[-2]
            
            vaa_file = os.path.join(output_dir, file_name)
            kml_file = os.path.join(output_dir, file_name.replace(".html", ".kml"))

            # Do not download the file if we already have it.
            if not os.path.exists(kml_file):
                vaa_html = urllib2.urlopen(vaa_url).read()
                open(vaa_file, "w").write(vaa_html)
            else:
                # If we already have the file then we should also have the
                # files that preceded it.
                break
            
            # Convert the message in the HTML file to a KML file.
            os.system("metno-vaa-kml " + commands.mkarg(vaa_file))

            # Remove the HTML file.
            os.remove(vaa_file)
            
            count += 1
            if count == 10:
                break
    
    if count == 0:
        text = "No new KML files retrieved."
    elif count == 1:
        text = "1 new KML file can be found in the '%s' directory." % output_dir
    else:
        text = "%i new KML files can be found in the '%s' directory." % (count, output_dir)
    
    if gui:
        os.system('zenity --info --text="%s"' % text)
    else:
        print text

    sys.exit()
