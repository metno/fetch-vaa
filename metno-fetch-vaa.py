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

import sys

from metno_fetch_vaa import LondonFetcher, ToulouseFetcher, LocalFileFetcher, \
                            TestFetcher, QApplication, Window

if __name__ == "__main__":

    app = QApplication(sys.argv)

    fetchers = {u"London VAAC": LondonFetcher(),
                u"Toulouse VAAC": ToulouseFetcher(),
               #u"Anchorage VAAC": AnchorageFetcher(),
                u"Local file": LocalFileFetcher(),
                u"Test VAAC": TestFetcher()}

    window = Window(fetchers)
    window.show()
    sys.exit(app.exec_())
