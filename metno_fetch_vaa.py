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

import commands, datetime, HTMLParser, os, subprocess, urllib2, urlparse

import PyQt4.QtCore as QtCore
from PyQt4.QtGui import *

__version__ = "0.9.7"

checked_dict = {False: QtCore.Qt.Unchecked, True: QtCore.Qt.Checked}

class Settings(QtCore.QSettings):

    """Convenience class to help read values from settings files as Python datatypes.
    """

    def __init__(self, organisation, product):

       QtCore.QSettings.__init__(self, organisation, product)
    
    def value(self, key, default = QtCore.QVariant()):
    
        """Reads the value from the settings file that corresponds to the given key,
        with the type defined by the default value. If the key is not defined in the
        settings file then the default value is returned instead.
        """
        value = QtCore.QSettings.value(self, key, default)
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

    showBusy = True
    showInMenu = True
    defaultFlags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable

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
    returns_html = True

    def fetch(self, vaaList, output_dir):
    
        "Reads the messages available from the URL for the current VAA centre."

        html = urllib2.urlopen(self.url).read()
        p = Parser()
        p.feed(html)
        p.close()
        
        count = 0

        for href, text, table_text in p.anchors:

            if text.endswith("UTC"):
            
                # The date is encoded in the URL for the advisory.
                info = href.split(".")
                date = datetime.datetime.strptime(info[-2], "%Y%m%d%H%M").strftime("%Y-%m-%d %H:%M")
                volcano = info[2].replace("_", " ")
                item = QListWidgetItem("%s (%s)" % (date, volcano))
                item.setFlags(self.defaultFlags)
                # The name to use for the locally stored file needs to be
                # in a suitable format so that Diana can read it as part of
                # a collection.
                item.filename = "toulouse." + info[-2] + ".html"
                item.url = urlparse.urljoin(self.url, href)
                item.content = None
                item.setCheckState(checked_dict[False])
                if self.hasExistingFile(output_dir, item.filename):
                    item.setText(item.text() + " " + QApplication.translate("Fetcher", "(converted)"))
                vaaList.addItem(item)

                count += 1
                if count == self.number_to_fetch:
                    break


class AnchorageFetcher(Fetcher):

    url = "http://vaac.arh.noaa.gov/list_vaas.php"
    number_to_fetch = 10
    returns_html = True

    def fetch(self, vaaList, output_dir):
    
        "Reads the messages available from the URL for the current VAA centre."

        html = urllib2.urlopen(self.url).read()
        p = Parser()
        p.feed(html)
        p.close()
        
        count = 0

        for href, text, table_text in p.anchors:

            if text == "X" and href.split("/")[-2] == "VAA":
            
                # The date is encoded in the associated table text.
                date = datetime.datetime.strptime(table_text[0], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                volcano = table_text[1].replace("_", " ")
                item = QListWidgetItem("%s (%s)" % (date, volcano))
                item.setFlags(self.defaultFlags)
                item.filename = href
                item.url = urlparse.urljoin(self.url, href)
                item.content = None
                item.setCheckState(checked_dict[False])
                if self.hasExistingFile(output_dir, href):
                    item.setText(item.text() + " " + QApplication.translate("Fetcher", "(converted)"))
                vaaList.addItem(item)

                count += 1
                if count == self.number_to_fetch:
                    break


class LondonFetcher(Fetcher):

    # Scrape the London VAAC page on the Met Office website.
    url = "http://www.metoffice.gov.uk/aviation/vaac/vaacuk.html"
    # A listing of the files can be obtained from this address:
    # http://www.metoffice.gov.uk/aviation/vaac/data/?C=M;O=D
    number_to_fetch = 10
    returns_html = False

    def fetch(self, vaaList, output_dir):
    
        "Reads the messages available from the URL for the current VAA centre."

        html = urllib2.urlopen(self.url).read()
        p = Parser()
        p.feed(html)
        p.close()
        
        count = 0
        # Some message appear more than once in the table, so filter out duplicates.
        urls = set()

        for href, text, table_text in p.anchors:

            if text == "VAA" and href.endswith(".html"):
            
                # The date is encoded in the associated table text.
                # Unfortunately, it is localised, so we use the date from the
                # message itself.
                message_url = urlparse.urljoin(self.url, href)
                if message_url in urls:
                    continue

                urls.add(message_url)

                volcano, date, text = self.read_message(message_url)
                item = QListWidgetItem("%s (%s)" % (date, volcano))
                item.setFlags(self.defaultFlags)
                item.filename = "london." + date.strftime("%Y%m%d%H%M")
                item.url = message_url
                item.content = text
                item.setCheckState(checked_dict[False])
                if self.hasExistingFile(output_dir, item.filename):
                    item.setText(item.text() + " " + QApplication.translate("Fetcher", "(converted)"))
                vaaList.addItem(item)

                count += 1
                if count == self.number_to_fetch:
                    break

    def read_message(self, url):
    
        html = urllib2.urlopen(url).read()

        # The London VAAC currently shows advisories in HTML pages.
        # We just extract what we can find.
        at = html.find("VA ADVISORY")
        if at == -1:
            return
        
        start = html.rfind("<p>", 0, at)
        if start == -1:
            return
        
        start = html.find("<br>", start)
        lines = html[start:].split("\n")
        
        text = ""
        date = datetime.datetime.now()
        volcano = "Unknown"

        for line in lines:

            line = line.strip()
            if not line or line == "<br>":
                continue
            
            text += line + "\n"
            if line.startswith("DTG:"):
                # The date is encoded in the advisory.
                date_text = line[4:].lstrip()
                date = datetime.datetime.strptime(date_text, "%Y%m%d/%H%MZ")
            
            if line.startswith("VOLCANO:"):
                # The volcano is encoded in the advisory.
                volcano = line[8:].lstrip()

            if line == "=":
                break
        
        return volcano, date, text


class LocalFileFetcher(Fetcher):

    returns_html = False
    showBusy = False
    showInMenu = False

    def fetch(self, vaaList, output_dir):
    
        fileName = QFileDialog.getOpenFileName(None, QApplication.translate("LocalFileFetcher", "Open VAA File"))
        
        if fileName.isEmpty():
            return
        
        fileName = unicode(fileName)
        
        vaaList.clear()
        item = QListWidgetItem(fileName)
        item.setFlags(self.defaultFlags)
        item.filename = os.path.split(fileName)[1]
        item.url = urlparse.urljoin("file://", fileName)
        item.content = None
        item.setCheckState(checked_dict[False])
        vaaList.addItem(item)


class TestFetcher(Fetcher):

    url = "https://github.com/metno/fetch-vaa/raw/master/files/london-201511101500.vaa.txt"
    number_to_fetch = 1
    returns_html = True
    
    def fetch(self, vaaList, output_dir):
    
        "Reads the messages available from the URL for the current VAA centre."

        text = urllib2.urlopen(self.url).read()
        
        date = datetime.datetime.now()
        volcano = "Unknown"

        lines = text.split("\n")
        for line in lines:

            if line.startswith("DTG:"):
                # The date is encoded in the advisory.
                date_text = line[4:].lstrip()
                date = datetime.datetime.strptime(date_text, "%Y%m%d/%H%MZ")
        
            if line.startswith("VOLCANO:"):
                # The volcano is encoded in the advisory.
                volcano = line[8:].lstrip()
        
        item = QListWidgetItem("%s (%s)" % (date.strftime("%Y-%m-%d %H:%M:%S"), volcano))
        item.setFlags(self.defaultFlags)
        # Use a different name for the path instead of the path of the page on the site.
        item.filename = "test." + date.strftime("%Y%m%d%H%M")
        # Store the original location.
        item.url = self.url
        # We have already obtained the content.
        item.content = text
        item.setCheckState(checked_dict[False])
        if self.hasExistingFile(output_dir, item.filename):
            item.setText(item.text() + " " + QApplication.translate("Fetcher", "(converted)"))
        vaaList.addItem(item)


class EditDialog(QDialog):

    def __init__(self, content, parent = None):

        QDialog.__init__(self, parent)

        self.textEdit = QPlainTextEdit()
        self.textEdit.setPlainText(content)
        
        buttonBox = QDialogButtonBox()
        buttonBox.addButton(QDialogButtonBox.Ok)
        buttonBox.addButton(QDialogButtonBox.Cancel)
        
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.textEdit)
        layout.addWidget(buttonBox)

        self.setWindowTitle(self.tr("Edit Message"))


class Window(QMainWindow):

    def __init__(self, fetchers):

        QMainWindow.__init__(self)

        self.fetchers = fetchers
        self.settings = Settings("met.no", "metno-fetch-vaa")
        
        self.output_dir = self.settings.value("work directory",
                          os.path.join(os.getenv("HOME"), ".vaac"))
        self.workLog = ""
        
        contentWidget = QWidget()
        layout = QGridLayout(contentWidget)
        
        fileMenu = self.menuBar().addMenu(self.tr("&File"))
        fileMenu.addAction(self.tr("&New File..."), self.newFile,
            QKeySequence.New)
        openFileAction = fileMenu.addAction(self.tr("&Open File..."), self.fetchAdvisories,
            QKeySequence.Open)
        openFileAction.name = u"Local file"

        fileMenu.addSeparator()

        # Create a list of available VAA centres in the menu.
        names = self.fetchers.keys()
        names.sort()

        for name in names:
            if self.fetchers[name].showInMenu:
                action = fileMenu.addAction(name, self.fetchAdvisories)
                action.name = name
        
        fileMenu.addSeparator()
        fileMenu.addAction(self.tr("E&xit"), self.close, QKeySequence(QKeySequence.Quit))

        # Add a Help menu with about and documentation entries.
        helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        helpMenu.addAction(self.tr("&About..."), self.about)
        
        # Create a list of downloaded advisories.
        self.vaaList = QListWidget()
        layout.addWidget(self.vaaList, 0, 0)
        
        # Add a panel of buttons.
        buttonLayout = QHBoxLayout()

        self.editButton = QPushButton(self.tr("&Edit message"))
        self.editButton.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        buttonLayout.addWidget(self.editButton)
        buttonLayout.setAlignment(self.editButton, QtCore.Qt.AlignHCenter)

        self.convertButton = QPushButton(self.tr("&Convert messages"))
        self.convertButton.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        buttonLayout.addWidget(self.convertButton)
        buttonLayout.setAlignment(self.convertButton, QtCore.Qt.AlignHCenter)

        layout.addLayout(buttonLayout, 1, 0)
        
        # Ensure that the list widgets are given enough space.
        layout.setRowStretch(1, 1)

        # Add a log viewer.
        self.logViewer = QTextEdit()
        self.logViewer.setReadOnly(True)
        self.showHideLogButton = QPushButton(self.tr("&Hide log"))
        self.showHideLogButton.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        layout.addWidget(self.logViewer, 3, 0)
        layout.addWidget(self.showHideLogButton, 4, 0)
        self.showHideLogViewer(self.settings.value("window/log", False))

        # Make connections.
        self.vaaList.currentItemChanged.connect(self.showLog)
        self.vaaList.itemActivated.connect(self.showLog)
        self.vaaList.currentItemChanged.connect(self.updateButtons)
        self.vaaList.itemChanged.connect(self.updateButtons)
        self.vaaList.itemActivated.connect(self.updateButtons)
        self.editButton.clicked.connect(self.editMessage)
        self.convertButton.clicked.connect(self.convertAdvisories)
        self.showHideLogButton.clicked.connect(self.showHideLogViewer)
        
        self.updateButtons()

        self.setCentralWidget(contentWidget)
        self.setWindowTitle(self.tr("Fetch Volcanic Ash Advisories"))
        if self.settings.contains("window/geometry"):
            self.restoreGeometry(self.settings.value("window/geometry").toByteArray())
        else:
            self.resize(640, 480)


    def updateWorkLog(self, isOK, hasConverted, message):
        if isOK:
            color="green"
        else:
            color ="red"

        if hasConverted:
            header = "VAAC message converted"
        else:
            header="VAAC message not converted"

        import datetime
        mytime = datetime.datetime.now().isoformat()
        logEntry= "<i>%s</i> <b > : <font color='%s'> %s <br></font></b>" % (mytime, color,header)

        logEntry+= " %s <p>" % message

        self.logViewer.insertHtml(logEntry)



    def about(self):

        QMessageBox.about(self, self.tr("About this program"),
            self.tr("<qt>Fetches Volcanic Ash Advisory (VAA) messages from certain "
                    "Volcanic Ash Advisory Centres (VAAC) and converts them to "
                    "Keyhole Markup Language (KML) files for use with Diana and "
                    "Ted.<p><b>Version:</b> %1</qt>").arg(__version__))
    
    def newFile(self):
    
        # Ask for the name of the file.
        volcano, success = QInputDialog.getText(self, self.tr("New File"),
            self.tr("Volcano name:"))
        
        if success and volcano:
            volcano = unicode(volcano)
        else:
            volcano = u"Unknown"
        
        date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        fileName = os.path.join(self.output_dir, u"%s.%s" % (volcano, date))
        
        # Create the file.
        try:
            open(fileName, "w").write("")
        except IOError:
            QMessageBox.critical(self, self.tr("Error"),
                self.tr("Failed to create an empty file to use for a new message.\n"
                        'Please consult the documentation for support.'))
            return
        
        # Add an item to the list.
        item = QListWidgetItem(fileName)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.filename = fileName
        item.url = urlparse.urljoin("file://", fileName)
        item.content = None
        item.setCheckState(checked_dict[False])
        self.vaaList.addItem(item)

        self.updateButtons()
        self.vaaList.setCurrentItem(item)
        self.editButton.animateClick()

    def fetchAdvisories(self):
    
        self.vaaList.clear()
        name = self.sender().name
        fetcher = self.fetchers[name]
        
        # Create the output directory if it does not already exist.
        if not os.path.exists(self.output_dir):
            os.system("mkdir -p " + commands.mkarg(self.output_dir))
        
        if fetcher.showBusy:
            QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        
        fetcher.fetch(self.vaaList, self.output_dir)

        self.updateButtons()
        
        if fetcher.showBusy:
            QApplication.restoreOverrideCursor()
            
            if self.vaaList.count() == 0:
                QMessageBox.information(self, self.tr("Fetching from %1").arg(name),
                    self.tr("No new messages available from %1.").arg(name))

    def updateButtons(self):
    
        yet_to_convert = False

        for i in range(self.vaaList.count()):
            item = self.vaaList.item(i)
            if item.checkState() == checked_dict[True] and \
               not os.path.exists(os.path.join(self.output_dir, item.filename)):
               yet_to_convert = True
               break

        self.convertButton.setEnabled(yet_to_convert)
        editable = self.vaaList.count() > 0 and self.vaaList.currentRow() != -1
        self.editButton.setEnabled(editable)
    
    def convertAdvisories(self):
        QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        
        kml_files = []
        failed_files = []
        
        for i in range(self.vaaList.count()):
        
            item = self.vaaList.item(i)
            if  item.checkState() == checked_dict[False]:
                continue
            
            href = item.filename
            url = item.url
            
            file_name = href.split("/")[-1]
            
            vaa_file = os.path.join(self.output_dir, file_name)
            if vaa_file.endswith(".html"):
                kml_file = file_name.replace(".html", ".kml")
            else:
                kml_file = file_name + ".kml"
            
            kml_file = os.path.join(self.output_dir, kml_file)

            hasConverted=False
            isOK=True
            message = item.text()

            if os.path.exists(kml_file):
                QApplication.restoreOverrideCursor()
                reply = QMessageBox.question(self, 'VAAC conversion',
                "Converted file %s  already exists. Do you want to convert again?" % kml_file, QMessageBox.Yes |
                QMessageBox.No, QMessageBox.No)

                if reply == QMessageBox.No:
                    message += " not converted. File already available in " + kml_file
                    self.updateWorkLog(isOK,hasConverted,message)
                    continue

                QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)


            if not item.content:
                vaa_content = item.content = urllib2.urlopen(url).read()
            else:
                vaa_content = item.content

            # Wrap any non-HTML content in a <pre> element.
            if vaa_content.lstrip()[:1] != "<":
                vaa_content = "<pre>\n" + vaa_content + "\n</pre>\n"
            if not vaa_file.endswith(".html"):
                vaa_file += ".html"

            open(vaa_file, "w").write(vaa_content)
            
            QApplication.processEvents()

            # Convert the message in the HTML file to a KML file.
            s = subprocess.Popen(["/usr/bin/metno-vaa-kml", vaa_file],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)



            output=s.stdout.read()


            if s.wait() != 0:
                failed_files.append(vaa_file)
                item.setIcon(QApplication.style().standardIcon(QStyle.SP_MessageBoxWarning))
                message += " conversion failed %s." % output
            else:
                # Remove the HTML file.
                os.remove(vaa_file)
                kml_files.append(kml_file)
                item.setText(item.text() + " " + QApplication.translate("Fetcher", "(converted)"))
                message += " converted. File available in " + kml_file +" % s " % output
                hasConverted=True
                isOK=True

            self.updateWorkLog(hasConverted,isOK,message)
        
        # Update the log viewer if it is already shown.
        if self.logViewer.isVisible():
            self.showLog()

        self.updateButtons()
        
        QApplication.restoreOverrideCursor()
    
    def showLog(self):

            self.showHideLogViewer(True)

    
    # Use a decorator to avoid receiving the signal that includes a boolean value.
    @QtCore.pyqtSlot()
    def showHideLogViewer(self, show = None):
    
        if show is None:
            show = not self.logViewer.isVisible()
        
        self.logViewer.setShown(show)
        if show:
            self.showHideLogButton.setText(self.tr("&Hide log"))
        else:
            self.showHideLogButton.setText(self.tr("&Show log"))
    
    def editMessage(self):

        row = self.vaaList.currentRow()
        item = self.vaaList.item(row)

        if not item.content:
            item.content = urllib2.urlopen(item.url).read()
        
        oldContent = item.content

        editDialog = EditDialog(item.content[:], self)
        editDialog.restoreGeometry(self.settings.value("editdialog/geometry").toByteArray())

        if editDialog.exec_() == QDialog.Accepted:
            item.content = unicode(editDialog.textEdit.toPlainText())
            if oldContent != item.content:
                item.setCheckState(checked_dict[False])

        self.updateButtons()
    
    def closeEvent(self, event):

        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/log", self.logViewer.isVisible())
        self.settings.setValue("editdialog/geometry", self.saveGeometry())
        self.settings.sync()

