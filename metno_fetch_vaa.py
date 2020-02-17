#!/usr/bin/env python3

# Copyright (C) 2014, 2020 MET Norway (met.no)
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

import datetime, os, subprocess, urllib.request, urllib.parse, html.parser

import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
import webbrowser

__version__ = "0.9.12"

checked_dict = {False: QtCore.Qt.Unchecked, True: QtCore.Qt.Checked}

class Settings(QtCore.QSettings):

    """Convenience class to help read values from settings files as Python datatypes.
    """

    def __init__(self, organisation, product):

        QtCore.QSettings.__init__(self, organisation, product)

    def value(self, key, default = QtCore.QVariant()):

        """
        Reads the value from the settings file that corresponds to the given key,
        with the type defined by the default value. If the key is not defined in the
        settings file then the default value is returned instead.
        """
        return QtCore.QSettings.value(self, key, default, type=type(default))


class Parser(html.parser.HTMLParser):

    def __init__(self):

        html.parser.HTMLParser.__init__(self)
        self.href = ""
        self.text = ""
        self.table_row = []
        self.tags = []
        self.anchors = []

    def feed(self, data):

        self.anchors = []
        html.parser.HTMLParser.feed(self, data)

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
    defaultFlags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable


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

        html = urllib.request.urlopen(self.url).read()
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
                item = QtWidgets.QListWidgetItem("%s (%s)" % (date, volcano))
                item.setFlags(self.defaultFlags)
                # The name to use for the locally stored file needs to be
                # in a suitable format so that Diana can read it as part of
                # a collection.
                item.filename = "toulouse." + info[-2] + ".html"
                item.url = urllib.parse.urljoin(self.url, href)
                item.vag = self.get_vag_url(p,info)
                item.content = None
                item.setCheckState(checked_dict[False])
                if self.hasExistingFile(output_dir, item.filename):
                    item.setText(item.text() + " " + QtWidgets.QApplication.translate("Fetcher", "(converted)"))
                vaaList.addItem(item)

                count += 1
                if count == self.number_to_fetch:
                    break

    def get_vag_url(self,parser,info):

            datestring = ".".join(info[-3:-2])
            volcano = info[2].replace("_", " ")
            for href, text, table_text in parser.anchors:
                if volcano in href and datestring in href and href.endswith("png"):
                    if "(VAG)" in text:
                       vag_url = urllib.parse.urljoin(self.url, href)
                       return vag_url
            return None




class AnchorageFetcher(Fetcher):

    url = "http://vaac.arh.noaa.gov/list_vaas.php"
    number_to_fetch = 10
    returns_html = True

    def fetch(self, vaaList, output_dir):

        "Reads the messages available from the URL for the current VAA centre."

        html = urrlib3.urlopen(self.url).read()
        p = Parser()
        p.feed(html)
        p.close()

        count = 0

        for href, text, table_text in p.anchors:

            if text == "X" and href.split("/")[-2] == "VAA":

                # The date is encoded in the associated table text.
                date = datetime.datetime.strptime(table_text[0], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                volcano = table_text[1].replace("_", " ")
                item = QtWidgets.QListWidgetItem("%s (%s)" % (date, volcano))
                item.setFlags(self.defaultFlags)
                item.filename = href
                item.url = urllib.parse.urljoin(self.url, href)
                item.vag=None
                item.content = None
                item.setCheckState(checked_dict[False])
                if self.hasExistingFile(output_dir, href):
                    item.setText(item.text() + " " + QtWidgets.QApplication.translate("Fetcher", "(converted)"))
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
        """
        Reads the messages available from the URL for the current VAA centre.
        """

        req = urllib.request.Request(self.url, headers={'User-Agent' : "Magic Browser"})
        print("Open ", self.url)
        # FIXME: VAAC uses utf-8 at the moment. If this changes this needs to be updated
        html = urllib.request.urlopen(req).read().decode('utf-8')
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
                message_url = urllib.parse.urljoin(self.url, href)
                if message_url in urls:
                    continue

                urls.add(message_url)

                volcano, date, text = self.read_message(message_url)
                item = QtWidgets.QListWidgetItem("%s (%s)" % (date, volcano))
                item.setFlags(self.defaultFlags)
                item.filename = "london." + date.strftime("%Y%m%d%H%M")
                item.url = message_url
                item.content = text
                item.setCheckState(checked_dict[False])
                item.vag = self.get_vag_url(p,table_text)
                if self.hasExistingFile(output_dir, item.filename):
                    item.setText(item.text() + " " + QtWidgets.QApplication.translate("Fetcher", "(converted)"))
                vaaList.addItem(item)

                count += 1
                if count == self.number_to_fetch:
                    break

    def read_message(self, url):

        req = urllib.request.Request(url, headers={'User-Agent' : "Magic Browser"})
        # FIXME: VAAC uses utf-8 at the moment - need to update if that changes
        html = urllib.request.urlopen(req).read().decode('utf-8')

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


    def get_vag_url(self,parser,table_text_to_find):

          for href, text, table_text in parser.anchors:
                if table_text==table_text_to_find:
                    if text == "VAG" and href.endswith(".png"):
                        vag_url = urllib.parse.urljoin(self.url, href)
                        return vag_url

          return None

class LocalFileFetcher(Fetcher):

    returns_html = False
    showBusy = False
    showInMenu = False

    def fetch(self, vaaList, output_dir):

        fileName = QtWidgets.QFileDialog.getOpenFileName(None, QtWidgets.QApplication.translate("LocalFileFetcher", "Open VAA File"))

        if fileName.isEmpty():
            return

        fileName = unicode(fileName)

        vaaList.clear()
        item = QtWidgets.QListWidgetItem(fileName)
        item.setFlags(self.defaultFlags)
        item.filename = os.path.split(fileName)[1]
        item.url = urllib.parse.urljoin("file://", fileName)
        item.vag=None
        item.content = None
        item.setCheckState(checked_dict[False])
        vaaList.addItem(item)


class TestFetcher(Fetcher):

    url = "https://github.com/metno/fetch-vaa/raw/master/files/london-201511101500.vaa.txt"
    number_to_fetch = 1
    returns_html = True

    def fetch(self, vaaList, output_dir):

        "Reads the messages available from the URL for the current VAA centre."

        text = urrlib3.urlopen(self.url).read()

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

        item = QtWidgets.QListWidgetItem("%s (%s)" % (date.strftime("%Y-%m-%d %H:%M:%S"), volcano))
        item.setFlags(self.defaultFlags)
        # Use a different name for the path instead of the path of the page on the site.
        item.filename = "test." + date.strftime("%Y%m%d%H%M")
        # Store the original location.
        item.url = self.url
        item.vag=None
        # We have already obtained the content.
        item.content = text
        item.setCheckState(checked_dict[False])
        if self.hasExistingFile(output_dir, item.filename):
            item.setText(item.text() + " " + QtWidgets.QApplication.translate("Fetcher", "(converted)"))
        vaaList.addItem(item)


class EditDialog(QtWidgets.QDialog):

    def __init__(self, content, parent = None):

        QtWidgets.QDialog.__init__(self, parent)

        self.textEdit = QtWidgets.QPlainTextEdit()
        self.textEdit.setPlainText(content)

        buttonBox = QtWidgets.QDialogButtonBox()
        buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.textEdit)
        layout.addWidget(buttonBox)

        self.setWindowTitle(self.tr("Edit Message"))


class Window(QtWidgets.QMainWindow):

    def __init__(self, fetchers):

        QtWidgets.QMainWindow.__init__(self)

        self.fetchers = fetchers
        self.settings = Settings("met.no", "metno-fetch-vaa")

        self.output_dir = self.settings.value("work directory",
                          os.path.join(os.getenv("HOME"), ".vaac"))
        self.workLog = ""

        contentWidget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(contentWidget)

        fileMenu = self.menuBar().addMenu(self.tr("&File"))
        fileMenu.addAction(self.tr("&New File..."), self.newFile,
            QtGui.QKeySequence.New)
        openFileAction = fileMenu.addAction(self.tr("&Open File..."), self.fetchAdvisories,
            QtGui.QKeySequence.Open)
        openFileAction.name = u"Local file"

        fileMenu.addSeparator()

        # Create a list of available VAA centres in the menu.
        names = self.fetchers.keys()
        #names.sort()

        for name in names:
            if self.fetchers[name].showInMenu:
                action = fileMenu.addAction(name, self.fetchAdvisories)
                action.name = name

        fileMenu.addSeparator()
        fileMenu.addAction(self.tr("E&xit"), self.close, QtGui.QKeySequence(QtGui.QKeySequence.Quit))

        # Add a Help menu with about and documentation entries.
        helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        helpMenu.addAction(self.tr("&About..."), self.about)
        helpMenu.addAction(self.tr("&User Documentation"),self.showdoc)

        # Create a list of downloaded advisories.
        self.vaaList = QtWidgets.QListWidget()
        layout.addWidget(self.vaaList, 0, 0)

        # Add a panel of buttons.
        buttonLayout = QtWidgets.QHBoxLayout()

        self.editButton = QtWidgets.QPushButton(self.tr("&Edit message"))
        self.editButton.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        self.editButton.setToolTip(self.tr("Edit text of the selected VAAC message"))
        buttonLayout.addWidget(self.editButton)
        buttonLayout.setAlignment(self.editButton, QtCore.Qt.AlignHCenter)

        self.vagButton = QtWidgets.QPushButton(self.tr("&Show VAG(graphics)"))
        self.vagButton.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        self.vagButton.setToolTip(self.tr("Show VAG graphics corresponding to selected VAAC message"))
        buttonLayout.addWidget(self.vagButton)
        buttonLayout.setAlignment(self.vagButton, QtCore.Qt.AlignHCenter)


        self.convertButton = QtWidgets.QPushButton(self.tr("&Convert messages"))
        self.convertButton.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        self.convertButton.setToolTip(self.tr("Convert one or more checked VAAC messages to kml-format, so they can be displayed in Diana"))
        buttonLayout.addWidget(self.convertButton)
        buttonLayout.setAlignment(self.convertButton, QtCore.Qt.AlignHCenter)

        layout.addLayout(buttonLayout, 1, 0)

        # Ensure that the list widgets are given enough space.
        layout.setRowStretch(1, 1)

        # Add a log viewer.
        self.logViewer = QtWidgets.QTextEdit()
        self.logViewer.setReadOnly(True)
        self.showHideLogButton = QtWidgets.QPushButton(self.tr("&Hide log"))
        self.showHideLogButton.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)

        layout.addWidget(self.logViewer, 3, 0)
        layout.addWidget(self.showHideLogButton, 4, 0)
        self.showHideLogViewer(self.settings.value("window/log", False))

        # Make connections.
        self.vaaList.currentItemChanged.connect(self.updateButtons)
        self.vaaList.itemChanged.connect(self.updateButtons)
        self.vaaList.itemActivated.connect(self.updateButtons)
        self.editButton.clicked.connect(self.editMessage)
        self.vagButton.clicked.connect(self.showVAG)
        self.convertButton.clicked.connect(self.convertAdvisories)
        self.showHideLogButton.clicked.connect(self.showHideLogViewer)

        self.updateButtons()

        self.setCentralWidget(contentWidget)
        self.setWindowTitle(self.tr("Fetch Volcanic Ash Advisories"))
        if self.settings.contains("window/geometry"):
            self.restoreGeometry(self.settings.value("window/geometry"))
        else:
            self.resize(640, 480)


    def updateWorkLog(self, isOK, hasConverted, message):
        if isOK:
            color = "green"
        else:
            color = "red"

        if hasConverted:
            header = "VAAC message converted"
        else:
            header = "VAAC message not converted"

        mytime = datetime.datetime.now().isoformat()
        logEntry = "<i>%s</i> <b > : <font color='%s'> %s <br></font></b>" % (mytime, color,header)

        logEntry += " %s <p>" % message

        self.logViewer.insertHtml(logEntry)



    def about(self):

        QtWidgets.QMessageBox.about(self, self.tr("About this program"),
            self.tr("<qt>Fetches Volcanic Ash Advisory (VAA) messages from certain "
                    "Volcanic Ash Advisory Centres (VAAC) and converts them to "
                    "Keyhole Markup Language (KML) files for use with Diana and "
                    "Ted.<p><b>Version:</b> %1</qt>").arg(__version__))

    def showdoc(self):
        url = 'https://dokit.met.no/fou/kl/prosjekter/eemep/eemep_userdoc#handling_a_vaac_message_in_diana_and_ted'
        # Open URL in a new tab, if a browser window is already open.
        webbrowser.open_new_tab(url)


    def showVAG(self):
        row = self.vaaList.currentRow()
        item = self.vaaList.item(row)
        url = item.vag
        if url is not None:
            webbrowser.open_new_tab(url)
        else:
            QtWidgets.QMessageBox.information(self, self.tr("Show VAG(Graphics"), self.tr("No graphics found for %s " % item.text()))

    def newFile(self):

        # Ask for the name of the file.
        volcano, success = QtWidgets.QInputDialog.getText(self, self.tr("New File"),
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
            QtWidgets.QMessageBox.critical(self, self.tr("Error"),
                self.tr("Failed to create an empty file to use for a new message.\n"
                        'Please consult the documentation for support.'))
            return

        # Add an item to the list.
        item = QtWidgets.QListWidgetItem(fileName)
        item.setFlags(Fetcher.defaultFlags)
        item.filename = fileName
        item.url = urllib.parse.urljoin("file://", fileName)
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
            os.makedirs(self.output_dir, exist_ok=True)

        if fetcher.showBusy:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        fetcher.fetch(self.vaaList, self.output_dir)

        self.updateButtons()

        if fetcher.showBusy:
            QtWidgets.QApplication.restoreOverrideCursor()

            if self.vaaList.count() == 0:
                QtWidgets.QMessageBox.information(self, self.tr("Fetching from %1").arg(name),
                    self.tr("No new messages available from %1.").arg(name))

    def updateButtons(self):

        yet_to_convert = False

        for i in range(self.vaaList.count()):
            item = self.vaaList.item(i)
            if item.checkState() == checked_dict[True]:
                yet_to_convert=True
                break


        self.convertButton.setEnabled(yet_to_convert)
        editable = self.vaaList.count() > 0 and self.vaaList.currentRow() != -1
        self.editButton.setEnabled(editable)
        self.vagButton.setEnabled(editable)

    def convertAdvisories(self):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

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

            hasConverted = False
            isOK = True
            message = item.text()

            if os.path.exists(kml_file):
                QtWidgets.QApplication.restoreOverrideCursor()
                reply = QtWidgets.QMessageBox.question(self, 'VAAC conversion',
                "Converted file %s  already exists. Do you want to convert again?" % kml_file, QtWidgets.QMessageBox.Yes |
                QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

                if reply == QtWidgets.QMessageBox.No:
                    message += " not converted. File already available in " + kml_file
                    self.updateWorkLog(isOK, hasConverted, message)
                    continue

                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)


            if not item.content:
                vaa_content = item.content = urrlib.urlopen(url).read()
            else:
                vaa_content = item.content

            # Wrap any non-HTML content in a <pre> element.
            if vaa_content.lstrip()[:1] != "<":
                vaa_content = "<pre>\n" + vaa_content + "\n</pre>\n"
            if not vaa_file.endswith(".html"):
                vaa_file += ".html"

            open(vaa_file, "w").write(vaa_content)

            QtWidgets.QApplication.processEvents()

            # Convert the message in the HTML file to a KML file.
            try:
                #FIXME: path here
                #sconvert = subprocess.Popen(["/usr/bin/metno-vaa-kml", vaa_file],
                sconvert = subprocess.Popen(["/home/andreb/projects/vaa-kml/metno-vaa-kml", vaa_file],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            except FileNotFoundError as e:
                failed_files.append(vaa_file)
                item.setIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning))
                message += " conversion failed %s." % str(e)
                isOK = False
                return



            output = sconvert.stdout.read()


            if sconvert.wait() != 0:
                failed_files.append(vaa_file)
                item.setIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning))
                message += " conversion failed %s." % output
                isOK = False
            else:
                # Remove the HTML file.
                os.remove(vaa_file)
                kml_files.append(kml_file)
                item.setText(item.text() + " " + QtWidgets.QApplication.translate("Fetcher", "(converted)"))
                message += " converted. File available in " + kml_file +" % s " % output
                hasConverted = True
                isOK = True

            self.updateWorkLog(isOK, hasConverted, message)

        # Update the log viewer if it is already shown.
        if self.logViewer.isVisible():
            self.showLog()

        self.updateButtons()

        QtWidgets.QApplication.restoreOverrideCursor()

    def showLog(self):
        self.showHideLogViewer(True)


    # Use a decorator to avoid receiving the signal that includes a boolean value.
    @QtCore.pyqtSlot()
    def showHideLogViewer(self, show = None):

        if show is None:
            show = not self.logViewer.isVisible()

        self.logViewer.setVisible(show)
        if show:
            self.showHideLogButton.setText(self.tr("&Hide log"))
        else:
            self.showHideLogButton.setText(self.tr("&Show log"))

    def editMessage(self):

        row = self.vaaList.currentRow()
        item = self.vaaList.item(row)

        if not item.content:
            item.content = urrlib.request.urlopen(item.url).read()

        oldContent = item.content

        editDialog = EditDialog(item.content[:], self)
        editDialog.restoreGeometry(self.settings.value("editdialog/geometry").toByteArray())

        if editDialog.exec_() == QtWidgets.QDialog.Accepted:
            item.content = unicode(editDialog.textEdit.toPlainText())
            if oldContent != item.content:
                item.setCheckState(checked_dict[False])

        self.updateButtons()

    def closeEvent(self, event):

        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/log", self.logViewer.isVisible())
        self.settings.setValue("editdialog/geometry", self.saveGeometry())
        self.settings.sync()
