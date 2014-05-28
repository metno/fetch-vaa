#!/usr/bin/env python

from distutils.core import setup

setup(
    name="metno-fetch-vaa",
    description="Tool for fetching Volcanic Ash Advisory messages from a Web site.",
    author="David Boddie",
    author_email="david.boddie@met.no",
    url="http://www.met.no/",
    version="0.1.0",
    scripts=["metno-fetch-vaa.py"]
    )
