#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc-tools-datalibrary server implementation for 3ds Max
"""

from __future__ import print_function, division, absolute_import

import os

from tpDcc.core import server
from tpDcc.libs.python import path as path_utils

from tpDcc.libs.datalibrary.core import datalib


class DataLibraryServer(server.DccServer, object):

    PORT = 28231

    def __init__(self, *args, **kwargs):
        super(DataLibraryServer, self).__init__(*args, **kwargs)

        self._data_library = None

    def save_data(self, data, reply):
        library_path = data['library_path']
        data_path = data['data_path']
        values = data['values']

        if not library_path or not os.path.isfile(library_path):
            reply['success'] = False
            reply['msg'] = 'Impossible to save data "{}" because library path "{}" does not exist!'.format(
                data_path, library_path)
            return

        data_lib = self._get_data_library(library_path)
        data_item = data_lib.get(data_path, only_extension=True)
        if not data_item:
            reply['success'] = False
            reply['msg'] = 'Impossible to retrieve data "{}" from data library: "{}"!'.format(data_path, data_lib)
            return

        save_function = data_item.functionality().get('save')
        if not save_function:
            reply['success'] = False
            reply['msg'] = 'Save functionality is not available for data: "{}"'.format(data_item)
            return

        result = save_function(**values)

        reply['success'] = True
        reply['result'] = result

    def _get_data_library(self, library_path):
        if self._data_library and path_utils.clean_path(
                self._data_library.identifier) == path_utils.clean_path(library_path):
            return self._data_library

        self._data_library = datalib.DataLibrary.load(library_path)

        return self._data_library

    def load_data(self, data, reply):
        library_path = data['library_path']
        data_path = data['data_path']

        if not library_path or not os.path.isfile(library_path):
            reply['success'] = False
            reply['message'] = 'Impossible to load data "{}" because library path "{}" does not exist!'.format(
                data_path, library_path)
            return

        if not os.path.isfile(data_path):
            reply['success'] = False
            reply['message'] = 'Impossible to load data "{}" because it does not exist!'.format(data_path)
            return

        data_lib = self._get_data_library(library_path)
        data_item = data_lib.get(data_path)
        if not data_item:
            reply['success'] = False
            reply['message'] = 'Impossible to retrieve data "{}" from data library: "{}"!'.format(data_path, data_lib)
            return

        load_function = data_item.functionality().get('load')
        if not load_function:
            reply['success'] = False
            reply['message'] = 'Load functionality is not available for data: "{}"'.format(data_item)
            return

        load_function()

        reply['success'] = True
