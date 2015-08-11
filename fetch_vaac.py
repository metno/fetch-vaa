#!/usr/bin/env python

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

from PyQt4 import QtCore, QtGui
import sys
import os
import urllib2
import subprocess
import selectVaac
import metno_fetch_vaa

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s



class MainDialog(QtGui.QDialog, selectVaac.Ui_Dialog):
    def __init__(self,fetchers,output_dir, parent=None):
        super(MainDialog,self).__init__(parent)
        self.setupUi(self)
        self.fetchers = fetchers
        self.output_dir = output_dir
        names = self.fetchers.keys()
        names.sort()
        vaacs=QtCore.QStringList(names)
        vaacs.insert(0,"Select VAAC")
        self.comboBox.insertItems(1,vaacs)
        self.comboBox.currentIndexChanged[QtCore.QString].connect(self.updateList)
        self.vaaList.currentItemChanged.connect(self.vaaListItemChanged)
        self.pushButton.clicked.connect(self.showVAACmessage)
        self.vaaList.doubleClicked.connect(self.showVAACmessage)

        self.showVAAC = QtGui.QTextBrowser()

        self.showVAAC.setGeometry(10,10,460,380)

    def updateList(self, vaac):
        self.vaaList.clear()
        self.fetchers[str(vaac)].fetch(self.vaaList,self.output_dir)

        for i in range(self.vaaList.count()):
            item = self.vaaList.item(i)
            item.setData(QtCore.Qt.CheckStateRole, QtCore.QVariant())
            item.setFlags(QtCore.Qt.ItemIsSelectable| QtCore.Qt.ItemIsEnabled )




    def accept(self):

        self.convertAdvisories()
        self.printVAACmessage()
        super(MainDialog,self).accept()

    def reject(self):
        self.printVAACmessage()


        super(MainDialog,self).reject()

    def printVAACmessage(self):
        if self.showVAAC.isVisible():
            row = self.vaaList.currentRow()
            item = self.vaaList.item(row)

            if not item.content:
                item.content = urllib2.urlopen(item.url).read()
            print item.text()
            print item.content
            geom = self.showVAAC.geometry()
            print "geom:", geom.x(), geom.y(), geom.width(), geom.height()
            self.showVAAC.close()



    def vaaListItemChanged(self):
        if self.showVAAC.isVisible():
            self.showVAACmessage()


    def showVAACmessage(self):
        row = self.vaaList.currentRow()
        item = self.vaaList.item(row)


        if not item.content:
            item.content = urllib2.urlopen(item.url).read()

        self.showVAAC.setText(item.content)
        self.showVAAC.setWindowTitle(item.text())
        self.showVAAC.show()

    def convertAdvisories(self):
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        kml_files = []
        failed_files = []
        self.workLog = {}

        row = self.vaaList.currentRow()
        item = self.vaaList.item(row)

        href = item.href
        url = item.url

        file_name = href.split("/")[-1]

        self.output_dir = os.path.abspath(self.output_dir)
        vaa_file = os.path.join(self.output_dir, file_name)
        if vaa_file.endswith(".html"):
            kml_file = file_name.replace(".html", ".kml")
        else:
            kml_file = file_name + ".kml"

        kml_file = os.path.join(self.output_dir, kml_file)
        message = item.text()
        if  os.path.exists(kml_file):
            message+=" already exists in " + kml_file
        else:

            if not item.content:
                vaa_content = item.content = urllib2.urlopen(url).read()
            else:
                vaa_content = item.content

            # Wrap any non-HTML content in a <pre> element.
            if not vaa_file.endswith(".html"):
                vaa_content = "<pre>\n" + vaa_content + "\n</pre>\n"
                vaa_file += ".html"

            open(vaa_file, "w").write(vaa_content)

            QtGui.QApplication.processEvents()


            # Convert the message in the HTML file to a KML file.
            s = subprocess.Popen(["/usr/bin/metno-vaa-kml", vaa_file],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            message = item.text()

            if s.wait() != 0:
                failed_files.append(vaa_file)
                item.setIcon(QApplication.style().standardIcon(QStyle.SP_MessageBoxWarning))
                message += " conversion failed."
            else:
                # Remove the HTML file.
                os.remove(vaa_file)
                kml_files.append(kml_file)
                item.setText(item.text() + " " + QtGui.QApplication.translate("Fetcher", "(converted)"))
                message += " converted. File available in " + kml_file

        print kml_file;

        QtGui.QApplication.restoreOverrideCursor()
        QtGui.QMessageBox.information(self, "VAAC conversion", message)

if __name__ == "__main__":


    if len(sys.argv) < 2:
        print "Usage: fetch_vaac.py <directory for files>"
        exit(1)

    output_dir = sys.argv[1]

    fetchers = {u"London VAAC": metno_fetch_vaa.LondonFetcher(), u"Toulouse VAAC": metno_fetch_vaa.ToulouseFetcher(), u"Test VAAC": metno_fetch_vaa.TestFetcher()}

    app= QtGui.QApplication(sys.argv)
    form = MainDialog(fetchers,output_dir)
    form.show()

    app.exec_()
