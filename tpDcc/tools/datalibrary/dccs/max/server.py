#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc-tools-datalibrary server implementation for 3ds Max
"""

from __future__ import print_function, division, absolute_import

from tpDcc.core import server


class DataLibraryServer(server.DccServer, object):

    PORT = 28231
