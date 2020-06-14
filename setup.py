#!/usr/bin/env python3

from distutils.core import setup
import metno_fetch_vaa

setup(
    name="metno-fetch-vaa",
    description="Tool for fetching Volcanic Ash Advisory messages from a Web site.",
    author="David Boddie, Helen Korsmo",
    author_email="helen.korsmo@met.no",
    url="http://www.met.no/",
    version=metno_fetch_vaa.__version__,
    py_modules=["metno_fetch_vaa", "selectVaac"],
    scripts=["fetch_vaac.py", "metno-fetch-vaa.py", "metno-vaa-kml"],
    data_files=[("share/applications", ["share/applications/metno-fetch-vaa.desktop"]),
                ("share/pixmaps", ["share/pixmaps/metno-fetch-vaa.png"]),
                ("share/metno-vaa-kml", ["share/metno-vaa-kml/volcano.tt", "share/metno-vaa-kml/volcano.grammar"])]
    )
