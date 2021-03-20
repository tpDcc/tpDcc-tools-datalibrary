#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc-tools-datalibrary server implementation for Maya
"""

from __future__ import print_function, division, absolute_import

import os

import maya.cmds

from tpDcc.core import server
from tpDcc.libs.python import path as path_utils

from tpDcc.libs.datalibrary.core import datalib


class DataLibraryServer(server.DccServer, object):

    PORT = 28231

    def __init__(self, *args, **kwargs):
        super(DataLibraryServer, self).__init__(*args, **kwargs)

        self._data_library = None

    def load_data_items(self, data, reply):

        from tpDcc.libs import datalibrary

        paths_to_load = list()

        dcc_items_path = os.path.join(datalibrary.__path__[0], 'dccs', self.dcc.get_name(), 'data')
        if os.path.isdir(dcc_items_path):
            paths_to_load.append(dcc_items_path)

        reply['result'] = paths_to_load
        reply['success'] = True

    def list_namespaces(self, data, reply):

        exclude_list = ['UI', 'shared']

        namespaces = maya.cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True)
        namespaces = list(set(namespaces) - set(exclude_list))
        namespaces = sorted(namespaces)

        reply['result'] = namespaces
        reply['success'] = True

    def list_nodes(self, data, reply):

        node_name = data.get('node_name', None)
        node_type = data.get('node_type', None)
        full_path = data.get('full_path', True)

        nodes = None
        if not node_name and not node_type:
            nodes = maya.cmds.ls(long=full_path)
        else:
            if node_name and node_type:
                nodes = maya.cmds.ls(node_name, type=node_type, long=full_path)
            elif node_name and not node_type:
                nodes = maya.cmds.ls(node_name, long=full_path)
            elif not node_name and node_type:
                nodes = maya.cmds.ls(type=node_type, long=full_path)

        reply['result'] = nodes or list()
        reply['success'] = True

    def set_focus(self, data, reply):

        ui_name = data.get('ui_name', None)
        try:
            maya.cmds.setFocus(ui_name)
        except Exception:
            pass

        reply['success'] = True

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

    def export_data(self, data, reply):
        library_path = data['library_path']
        data_path = data['data_path']
        values = data['values']

        if not library_path or not os.path.isfile(library_path):
            reply['success'] = False
            reply['message'] = 'Impossible to export data "{}" because library path "{}" does not exist!'.format(
                data_path, library_path)
            return

        data_lib = self._get_data_library(library_path)
        data_item = data_lib.get(data_path, only_extension=True)
        if not data_item:
            reply['success'] = False
            reply['message'] = 'Impossible to retrieve data "{}" from data library: "{}"!'.format(data_path, data_lib)
            return

        export_function = data_item.functionality().get('save')
        if not export_function:
            reply['success'] = False
            reply['message'] = 'Export functionality is not available for data: "{}"'.format(data_item)
            return

        result = export_function(**values)

        reply['success'] = True
        reply['result'] = result

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

    def import_data(self, data, reply):
        library_path = data['library_path']
        data_path = data['data_path']

        if not library_path or not os.path.isfile(library_path):
            reply['success'] = False
            reply['message'] = 'Impossible to import data "{}" because library path "{}" does not exist!'.format(
                data_path, library_path)
            return

        if not os.path.isfile(data_path):
            reply['success'] = False
            reply['message'] = 'Impossible to import data "{}" because it does not exist!'.format(data_path)
            return

        data_lib = self._get_data_library(library_path)
        data_item = data_lib.get(data_path)
        if not data_item:
            reply['success'] = False
            reply['message'] = 'Impossible to retrieve data "{}" from data library: "{}"!'.format(data_path, data_lib)
            return

        import_function = data_item.functionality().get('import_data')
        if not import_function:
            reply['success'] = False
            reply['message'] = 'Import functionality is not available for data: "{}"'.format(data_item)
            return

        import_function()

        reply['success'] = True

    def reference_data(self, data, reply):
        library_path = data['library_path']
        data_path = data['data_path']

        if not library_path or not os.path.isfile(library_path):
            reply['success'] = False
            reply['message'] = 'Impossible to reference data "{}" because library path "{}" does not exist!'.format(
                data_path, library_path)
            return

        if not os.path.isfile(data_path):
            reply['success'] = False
            reply['message'] = 'Impossible to reference data "{}" because it does not exist!'.format(data_path)
            return

        data_lib = self._get_data_library(library_path)
        data_item = data_lib.get(data_path)
        if not data_item:
            reply['success'] = False
            reply['message'] = 'Impossible to retrieve data "{}" from data library: "{}"!'.format(data_path, data_lib)
            return

        reference_function = data_item.functionality().get('reference_data')
        if not reference_function:
            reply['success'] = False
            reply['message'] = 'Reference functionality is not available for data: "{}"'.format(data_item)
            return

        reference_function()

        reply['success'] = True

    def _get_data_library(self, library_path):
        if self._data_library and path_utils.clean_path(
                self._data_library.identifier) == path_utils.clean_path(library_path):
            return self._data_library

        self._data_library = datalib.DataLibrary.load(library_path)

        return self._data_library
