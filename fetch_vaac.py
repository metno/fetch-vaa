#!/usr/bin/env python3

# Copyright (C) 2015 MET Norway (met.no)
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

""""
Download the contents of a VAAC message
and convert it to a kml-file.
"""""

from PyQt5 import QtCore
import PyQt5.QtWidgets as QtWidgets

import sys
import os
import urllib3
import subprocess
import selectVaac
import metno_fetch_vaa


class MainDialog(QtWidgets.QDialog, selectVaac.Ui_Dialog):
    """" gui for selecting a VAAC message to download """
    def __init__(self, fetchers, output_dir, parent=None):
        super(MainDialog, self).__init__(parent)
        self.setupUi(self)
        self.fetchers = fetchers
        self.output_dir = output_dir
        names = self.fetchers.keys()
        #names.sort()
        self.vaacs = list(names)
        self.vaacs.insert(0, "Select VAAC")
        self.comboBox.insertItems(1, self.vaacs)
        self.comboBox.currentIndexChanged.connect(self.update_list)
        self.vaaList.currentItemChanged.connect(self.vaa_listitem_changed)
        self.pushButton.clicked.connect(self.show_vaac_message)
        self.vaaList.doubleClicked.connect(self.show_vaac_message)

        self.show_vaac = QtWidgets.QTextBrowser()

        self.show_vaac.setGeometry(10, 10, 460, 380)

    def update_list(self, vaac):
        """ update the list of VAAC messages,
            when a new VAAC centre has been selected
        """

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.vaaList.clear()
        self.fetchers[self.vaacs[vaac]].fetch(self.vaaList, self.output_dir)
        for i in range(self.vaaList.count()):
            item = self.vaaList.item(i)
            item.setData(QtCore.Qt.CheckStateRole, QtCore.QVariant())
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        QtWidgets.QApplication.restoreOverrideCursor()

    def accept(self):
        """
            when OK is clicked, convert the advisory,
             print the VAAC message to stdout
        """
        self.convert_advisories()
        self.print_vaac_message()
        super(MainDialog, self).accept()


        
    def reject(self):
        """
            when Cancel is clicked, do not convert the advisory,
            print the VAAC message to stdout
        """
        self.print_vaac_message()

        super(MainDialog, self).reject()

    def print_vaac_message(self):
        """
            print the VAAC message contents
            as well as the geometry
            designed to be read by another process
        """
        if self.show_vaac.isVisible():
            row = self.vaaList.currentRow()
            item = self.vaaList.item(row)

            if not item.content:
                item.content = urllib3.urlopen(item.url).read()

            print(item.text)
            print(item.content)
            
            geom = self.show_vaac.geometry()
            print("geom:", geom.x(), geom.y(), geom.width(), geom.height())
            self.show_vaac.close()

    def vaa_listitem_changed(self):
        """ Display the new VAAC message,
            when we have selected it
            only if the show_vaac window is open
        """
        if self.show_vaac.isVisible():
            self.show_vaac_message()

    def show_vaac_message(self):
        """ download the VAAC message if not already done
            display it in the show_vaac window
        """
        row = self.vaaList.currentRow()
        item = self.vaaList.item(row)

        if not item.content:
            item.content = urllib2.urlopen(item.url).read()

        self.show_vaac.setText(item.content)
        self.show_vaac.setWindowTitle(item.text())
        self.show_vaac.show()

    def convert_advisories(self):
        """
            convert the selected advisory
        """
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        kml_files = []
        failed_files = []

        row = self.vaaList.currentRow()
        if row == -1:
            return

        item = self.vaaList.item(row)
        url = item.url
        file_name = item.filename

        self.output_dir = os.path.abspath(self.output_dir)
        vaa_file = os.path.join(self.output_dir, file_name)
        if vaa_file.endswith(".html"):
            kml_file = file_name.replace(".html", ".kml")
        else:
            kml_file = file_name + ".kml"

        kml_file = os.path.join(self.output_dir, kml_file)
        message = item.text()
        if os.path.exists(kml_file):
            message += " already exists in " + kml_file
        else:

            if not item.content:
                vaa_content = item.content = urllib3.urlopen(url).read()
            else:
                vaa_content = item.content

            # Wrap any non-HTML content in a <pre> element.
            if not vaa_file.endswith(".html"):
                vaa_content = "<pre>\n" + vaa_content + "\n</pre>\n"
                vaa_file += ".html"

            open(vaa_file, "w").write(vaa_content)

            QtWidgets.QApplication.processEvents()

            # Convert the message in the HTML file to a KML file.
            sconvert = subprocess.Popen(["/usr/bin/metno-vaa-kml", vaa_file],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)

            message = item.text()

            if sconvert.wait() != 0:
                failed_files.append(vaa_file)
                assert isinstance(QtGui.QApplication.style().
                                  standardIconobject, )
                item.setIcon(QtGui.QApplication.style().
                             standardIcon(QtGui.QStyle.SP_MessageBoxWarning))
                message += " conversion failed."
            else:
                # Remove the HTML file.
                os.remove(vaa_file)
                kml_files.append(kml_file)
                item.setText(item.text() + " " +
                             QtWidgets.QApplication.translate("Fetcher",
                                                          "(converted)"))
                message += " converted. File available in " + kml_file

        print(kml_file)

        QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QMessageBox.information(self, "VAAC conversion", message)





if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.stderr.write("Usage: fetch_vaac.py <directory for files>\n")
        sys.exit(1)

    vaac_output_dir = sys.argv[1]

    if not os.path.exists(vaac_output_dir):
        try:
            os.mkdir(vaac_output_dir)
        except OSError:
            sys.stderr.write("Failed to create output directory: '%s'\n"
                             % vaac_output_dir)
            sys.exit(1)

    vaac_fetchers = {u"London VAAC": metno_fetch_vaa.LondonFetcher(),
                     u"Toulouse VAAC": metno_fetch_vaa.ToulouseFetcher(),
                     u"Test VAAC": metno_fetch_vaa.TestFetcher()}

    app = QtWidgets.QApplication(sys.argv)
    form = MainDialog(vaac_fetchers, vaac_output_dir)
    form.setWindowFlags(form.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
    form.show()

    sys.exit(app.exec_())
