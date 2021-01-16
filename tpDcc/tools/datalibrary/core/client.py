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

    def save_data(self, library_path, data_path, values=None):
        """
        Saves given data in given library
        :param library_path: str
        :param data_path: str
        :param values: values, dict or None
        :return:
        """

        cmd = {
            'cmd': 'save_data',
            'library_path': library_path,
            'data_path': data_path,
            'values': values or dict()
        }

        reply_dict = self.send(cmd)

        return reply_dict['success'], reply_dict.get('msg', ''), reply_dict['result']

    def export_data(self, library_path, data_path, values=None):
        """
        Exports given data in given library
        :param library_path: str
        :param data_path: str
        :param values: values, dict or None
        :return:
        """

        cmd = {
            'cmd': 'export_data',
            'library_path': library_path,
            'data_path': data_path,
            'values': values or dict()
        }

        reply_dict = self.send(cmd)

        return reply_dict['success'], reply_dict.get('msg', ''), reply_dict['result']

    def load_data(self, library_path, data_path):
        """
        Loads given path in given library
        :param library_path: str
        :param data_path: str
        :return:
        """

        cmd = {
            'cmd': 'load_data',
            'library_path': library_path,
            'data_path': data_path
        }

        reply_dict = self.send(cmd)

        return reply_dict['success'], reply_dict.get('msg', '')

    def import_data(self, library_path, data_path):
        """
        Imports given path in given library
        :param library_path: str
        :param data_path: str
        :return:
        """

        cmd = {
            'cmd': 'import_data',
            'library_path': library_path,
            'data_path': data_path
        }

        reply_dict = self.send(cmd)

        return reply_dict['success'], reply_dict.get('msg', '')

    def reference_data(self, library_path, data_path):
        """
        References given path in given library
        :param library_path: str
        :param data_path: str
        :return:
        """

        cmd = {
            'cmd': 'reference_data',
            'library_path': library_path,
            'data_path': data_path
        }

        reply_dict = self.send(cmd)

        return reply_dict['success'], reply_dict.get('msg', '')
