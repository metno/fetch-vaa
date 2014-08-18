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

import commands, datetime, HTMLParser, os, subprocess, sys, urllib2, urlparse

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class Settings(QSettings):

    """Convenience class to help read values from settings files as Python datatypes.
    """

    def __init__(self, organisation, product):

        QSettings.__init__(self, organisation, product)
    
    def value(self, key, default = QVariant()):
    
        """Reads the value from the settings file that corresponds to the given key,
        with the type defined by the default value. If the key is not defined in the
        settings file then the default value is returned instead.
        """
        value = QSettings.value(self, key, default)
        if type(default) == int:
            return value.toInt()[0]
        elif type(default) == bool:
            return value.toBool()
        elif type(default) == float:
            return value.toFloat()[0]
        elif type(default) == str:
            return str(value.toString())
        elif type(default) == unicode:
            return unicode(value.toString())
        elif type(default) == list:
            if type(default[0]) == int:
                return map(lambda v: v.toInt()[0], value.toList())
        else:
            return value
        
        raise ValueError, "Unknown value type for key '%s': %s" % (key, type(default))


class Parser(HTMLParser.HTMLParser):

    def __init__(self):
    
        HTMLParser.HTMLParser.__init__(self)
        self.href = ""
        self.text = ""
        self.table_row = []
        self.tags = []
    
    def feed(self, data):

        self.anchors = []
        HTMLParser.HTMLParser.feed(self, data)
    
    def handle_starttag(self, tag, attrs):
    
        self.tags.append(tag)
        
        if tag == "a":
            d = dict(attrs)
            try:
                self.href = d["href"]
            except KeyError:
                pass
        elif tag == "tr":
            self.table_row = []
        
        self.text = ""

    def handle_data(self, data):
    
        self.text += data
    
    def handle_endtag(self, tag):

        if tag == "a":
            self.anchors.append((self.href, self.text, self.table_row))
            self.href = ""
        elif tag == "td":
            self.table_row.append(self.text)
        
        # Discard any non-matching end tags.
        while self.tags:
            if self.tags.pop() == tag:
                break


class Fetcher:

    def hasExistingFile(self, output_dir, href):

        file_name = href.split("/")[-1]
         
        vaa_file = os.path.join(output_dir, file_name)
        if vaa_file.endswith(".html"):
            kml_file = file_name.replace(".html", ".kml")
        else:
            kml_file = file_name + ".kml"
        
        return os.path.exists(os.path.join(output_dir, kml_file))


class ToulouseFetcher(Fetcher):

    url = "http://www.meteo.fr/vaac/evaa.html"
    number_to_fetch = 10

    def fetch(self, vaaList, output_dir):
    
        "Reads the messages available from the URL for the current VAA centre."

        html = urllib2.urlopen(self.url).read()
        p = Parser()
        p.feed(html)
        p.close()
        
        count = 0

        for href, text, table_text in p.anchors:

            if text.endswith("UTC"):
            
                # Stop processing if we have already downloaded and converted this file.
                if self.hasExistingFile(output_dir, href):
                    break

                # The date is encoded in the URL for the advisory.
                info = href.split(".")
                date = datetime.datetime.strptime(info[-2], "%Y%m%d%H%M").strftime("%Y-%m-%d %H:%M")
                volcano = info[2].replace("_", " ")
                item = QListWidgetItem("%s (%s)" % (date, volcano))
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item.href = href
                item.url = urlparse.urljoin(self.url, href)
                vaaList.addItem(item)

                count += 1
                if count == self.number_to_fetch:
                    break


class AnchorageFetcher(Fetcher):

    url = "http://vaac.arh.noaa.gov/list_vaas.php"
    number_to_fetch = 10

    def fetch(self, vaaList, output_dir):
    
        "Reads the messages available from the URL for the current VAA centre."

        html = urllib2.urlopen(self.url).read()
        p = Parser()
        p.feed(html)
        p.close()
        
        count = 0

        for href, text, table_text in p.anchors:

            if text == "X" and href.split("/")[-2] == "VAA":
            
                # Stop processing if we have already downloaded and converted this file.
                if self.hasExistingFile(output_dir, href):
                    break

                # The date is encoded in the associated table text.
                date = datetime.datetime.strptime(table_text[0], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                volcano = table_text[1].replace("_", " ")
                item = QListWidgetItem("%s (%s)" % (date, volcano))
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item.href = href
                item.url = urlparse.urljoin(self.url, href)
                vaaList.addItem(item)

                count += 1
                if count == self.number_to_fetch:
                    break


class Window(QMainWindow):

    def __init__(self, fetchers):

        QMainWindow.__init__(self)

        self.fetchers = fetchers
        self.settings = Settings("met.no", "metno-fetch-vaa")
        
        self.output_dir = self.settings.value("work directory",
                          os.path.join(os.getenv("HOME"), ".diana", "work"))
        self.workLog = []
        
        contentWidget = QWidget()
        layout = QGridLayout(contentWidget)
        
        # Create a list of available VAA centres.
        urlLabel = QLabel(self.tr("&Advisory Centres"))
        self.urlList = QListWidget()
        urlLabel.setBuddy(self.urlList)
        layout.addWidget(urlLabel, 0, 0)
        layout.addWidget(self.urlList, 1, 0)

        self.fetchButton = QPushButton(self.tr("&Fetch messages"))
        self.fetchButton.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        layout.addWidget(self.fetchButton, 2, 0)
        layout.setAlignment(self.fetchButton, Qt.AlignHCenter)

        # Create a list of downloaded advisories.
        vaaLabel = QLabel(self.tr("&Messages"))
        self.vaaList = QListWidget()
        vaaLabel.setBuddy(self.vaaList)
        layout.addWidget(vaaLabel, 0, 1)
        layout.addWidget(self.vaaList, 1, 1)
        
        self.convertButton = QPushButton(self.tr("&Convert messages"))
        self.convertButton.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        layout.addWidget(self.convertButton, 2, 1)
        layout.setAlignment(self.convertButton, Qt.AlignHCenter)
        
        # Ensure that the list widgets are given enough space.
        layout.setRowStretch(1, 1)

        # Add a log viewer.
        self.logViewerWidget = QWidget()
        logLayout = QVBoxLayout(self.logViewerWidget)

        self.logViewer = QPlainTextEdit()
        self.logViewer.setReadOnly(True)
        hideLogButton = QPushButton(self.tr("&Hide log"))
        hideLogButton.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        logLayout.addWidget(self.logViewer)
        logLayout.addWidget(hideLogButton)

        self.logViewerWidget.hide()
        layout.addWidget(self.logViewerWidget, 3, 0, 1, 3)

        # Make connections.
        self.urlList.itemSelectionChanged.connect(self.updateButtons)
        self.vaaList.itemSelectionChanged.connect(self.showLog)
        self.fetchButton.clicked.connect(self.fetchAdvisories)
        self.convertButton.clicked.connect(self.convertAdvisories)
        hideLogButton.clicked.connect(self.logViewerWidget.hide)
        
        # Fetch the list of VAA centres.
        self.fetchVAACList()
        
        self.updateButtons()

        self.setCentralWidget(contentWidget)
        self.setWindowTitle(self.tr("Fetch Volcanic Ash Advisories"))
        self.restoreGeometry(self.settings.value("window/geometry").toByteArray())
    
    def fetchVAACList(self):
    
        names = self.fetchers.keys()
        names.sort()

        for name in names:

            item = QListWidgetItem(name)
            item.name = name
            self.urlList.addItem(item)
    
    def fetchAdvisories(self):
    
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        self.vaaList.clear()
        item = self.urlList.currentItem()
        fetcher = self.fetchers[item.name]
        
        # Create the output directory if it does not already exist.
        if not os.path.exists(self.output_dir):
            os.system("mkdir -p " + commands.mkarg(self.output_dir))

        fetcher.fetch(self.vaaList, self.output_dir)
        self.updateButtons()
        
        QApplication.restoreOverrideCursor()
        
        if self.vaaList.count() == 0:
            QMessageBox.information(self, self.tr("Fetching from %1").arg(item.name),
                self.tr("No new messages available from %1.").arg(item.name))

    def updateButtons(self):
    
        self.fetchButton.setEnabled(self.urlList.currentItem() != None)
        self.convertButton.setEnabled(self.vaaList.count() > 0)
    
    def convertAdvisories(self):
    
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        kml_files = []
        failed_files = []
        self.workLog = []
        
        for i in range(self.vaaList.count()):
        
            item = self.vaaList.item(i)
            href = item.href
            url = item.url
            
            file_name = href.split("/")[-1]
            
            vaa_file = os.path.join(self.output_dir, file_name)
            if vaa_file.endswith(".html"):
                kml_file = file_name.replace(".html", ".kml")
            else:
                kml_file = file_name + ".kml"
            
            kml_file = os.path.join(self.output_dir, kml_file)
            vaa_content = urllib2.urlopen(url).read()

            # Wrap any non-HTML content in a <pre> element.
            if not vaa_file.endswith(".html"):
                vaa_content = "<pre>\n" + vaa_content + "\n</pre>\n"
                vaa_file += ".html"

            open(vaa_file, "w").write(vaa_content)
            
            # Convert the message in the HTML file to a KML file.
            s = subprocess.Popen(["/usr/bin/metno-vaa-kml", vaa_file],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if s.wait() != 0:
                failed_files.append(vaa_file)
            else:
                # Remove the HTML file.
                os.remove(vaa_file)
                kml_files.append(kml_file)
                item.setCheckState(Qt.Checked)

            self.workLog.append(s.stdout.read())
            QApplication.processEvents()
        
        QApplication.restoreOverrideCursor()
    
    def showLog(self):
    
        # Since this is called when the selection changes, and the selection
        # changes just before the list is cleared, we can't check for the
        # number of items in the list.
        if len(self.vaaList.selectedItems()) == 0:
            self.logViewerWidget.hide()
            return
        
        row = self.vaaList.currentRow()
        if 0 <= row < len(self.workLog):
        
            text = self.workLog[row]
            self.logViewer.setPlainText(text)
            self.logViewerWidget.show()

    def closeEvent(self, event):

        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.sync()


if __name__ == "__main__":

    app = QApplication(sys.argv)

    fetchers = {u"Toulouse VAAC": ToulouseFetcher(),
                u"Anchorage VAAC": AnchorageFetcher()}

    window = Window(fetchers)
    window.show()
    sys.exit(app.exec_())
