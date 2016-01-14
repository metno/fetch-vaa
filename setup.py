#!/usr/bin/env python

from distutils.core import setup

setup(
    name="metno-fetch-vaa",
    description="Tool for fetching Volcanic Ash Advisory messages from a Web site.",
    author="David Boddie, Helen Korsmo",
    author_email="helen.korsmo@met.no",
    url="http://www.met.no/",
    version="0.9.7",
    py_modules=["metno_fetch_vaa", "selectVaac"],
    scripts=["fetch_vaac.py", "metno-fetch-vaa.py"],
    data_files=[("share/applications", ["share/applications/metno-fetch-vaa.desktop"]),
                ("share/pixmaps", ["share/pixmaps/metno-fetch-vaa.png"])]
    )
