#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc-tools-datalibrary server implementation
"""

from __future__ import print_function, division, absolute_import

import os

import maya.cmds

from tpDcc.core import server


class DataLibraryServer(server.DccServer, object):

    PORT = 28231

    def _process_command(self, command_name, data_dict, reply_dict):
        if command_name == 'load_data_items':
            self.load_data_items(data_dict, reply_dict)
        elif command_name == 'list_namespaces':
            self.load_data_items(data_dict, reply_dict)
        elif command_name == 'list_nodes':
            self.list_nodes(data_dict, reply_dict)
        elif command_name == 'set_focus':
            self.set_focus(data_dict, reply_dict)
        elif command_name == 'save_dcc_file':
            self.save_dcc_file(data_dict, reply_dict)
        elif command_name == 'import_dcc_file':
            self.import_dcc_file(data_dict, reply_dict)
        else:
            super(DataLibraryServer, self)._process_command(command_name, data_dict, reply_dict)

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

        return namespaces

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

    def save_dcc_file(self, data, reply):

        file_path = data['file_path']

        maya_type = 'mayaBinary' if file_path.endswith('.mb') else 'mayaAscii'

        # selection = maya.cmds.ls(sl=True)
        # if selection:
        #     maya.cmds.file(
        #         file_path, type=maya_type, options='v=0;', preserveReferences=True, exportSelected=selection)
        # else:
        maya.cmds.file(rename=file_path)
        maya.cmds.file(type=maya_type, options='v=0;', preserveReferences=True, save=True)

        reply['success'] = True

    def import_dcc_file(self, data, reply):

        file_path = data['file_path']

        maya_type = 'mayaBinary' if file_path.endswith('.mb') else 'mayaAscii'

        maya.cmds.file(
            file_path, i=True, type=maya_type, options='v=0;', preserveReferences=True, mergeNamespacesOnClash=False)

        reply['success'] = True
