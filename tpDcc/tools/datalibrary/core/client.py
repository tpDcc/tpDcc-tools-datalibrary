#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc-tools-datalibrary client implementation
"""

import os

from tpDcc.core import client
from tpDcc.libs.python import path as path_utils
import tpDcc.libs.datalibrary


class DataLibraryClient(client.DccClient, object):

    PORT = 28231

    # =================================================================================================================
    # OVERRIDES
    # =================================================================================================================

    def _get_paths_to_update(self):
        paths_to_update = super(DataLibraryClient, self)._get_paths_to_update()

        paths_to_update['tpDcc.libs.datalibrary'] = path_utils.clean_path(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(tpDcc.libs.datalibrary.__file__)))))

        return paths_to_update

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def load_data_items(self):
        cmd = {
            'cmd': 'load_data_items'
        }

        reply_dict = self.send(cmd)

        if not self.is_valid_reply(reply_dict):
            return list()

        return reply_dict['result']

    def list_namespaces(self):
        """
        Returns a list of all available namespaces
        :return: list(str)
        """

        cmd = {
            'cmd': 'list_namespaces'
        }

        reply_dict = self.send(cmd)

        if not self.is_valid_reply(reply_dict):
            return list()

        return reply_dict['result']

    def list_nodes(self, node_name=None, node_type=None, full_path=True):
        """
        Returns list of nodes with given types. If no type, all scene nodes will be listed
        :param node_name:
        :param node_type:
        :param full_path:
        :return: list(str)
        """

        cmd = {
            'cmd': 'list_nodes',
            'node_name': node_name,
            'node_type': node_type,
            'full_path': full_path
        }

        reply_dict = self.send(cmd)

        if not self.is_valid_reply(reply_dict):
            return list()

        return reply_dict['result']

    def set_focus(self, ui_name):
        """
        Sets the focus in the given UI element
        :param ui_name: str
        """

        cmd = {
            'cmd': 'set_focus',
            'ui_name': ui_name
        }

        reply_dict = self.send(cmd)

        if not self.is_valid_reply(reply_dict):
            return False

        return reply_dict['success']

    def save_dcc_file(self, file_path):
        """
        Stores current DCC scene in given file path
        :param file_path: str
        """

        cmd = {
            'cmd': 'save_dcc_file',
            'file_path': file_path
        }

        reply_dict = self.send(cmd)

        return reply_dict['success'], reply_dict.get('msg', '')

    def import_dcc_file(self, file_path):
        """
        Imports given DCC scene file into current DCC scene
        :param file_path: str
        """

        cmd = {
            'cmd': 'import_dcc_file',
            'file_path': file_path
        }

        reply_dict = self.send(cmd)

        if not self.is_valid_reply(reply_dict):
            return False

        return reply_dict['success']
