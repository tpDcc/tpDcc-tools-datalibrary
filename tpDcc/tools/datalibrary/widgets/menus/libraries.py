#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains data library libraries widget implementation
"""

from __future__ import print_function, division, absolute_import

from functools import partial

from Qt.QtWidgets import QMenu, QAction

from tpDcc.managers import resources
# from tpDcc.libs.datalibrary.core import utils


class LibrariesMenu(QMenu, object):
    def __init__(self, settings_path=None, library_window=None):
        super(LibrariesMenu, self).__init__(library_window)

        self._library_window = library_window
        self._settings_path = settings_path
        self.setTitle('Libraries')
        self.setIcon(resources.icon('books'))

        self.refresh()

    def settings_path(self):
        return self._settings_path

    def set_settings_path(self, settings_path):
        self._settings_path = settings_path
        self.refresh()

    def refresh(self):
        self.clear()

        # libraries = utils.read_settings(self._settings_path)
        # default = utils.default_library(self._settings_path)
        #
        # for name in libraries:
        #     library = libraries[name]
        #     path = library.get('path', '')
        #     kwargs = library.get('kwargs', dict())
        #     enabled = True
        #     if self._library_window:
        #         enabled = name != self._library_window.name()
        #     text = name
        #     if name == default and name.lower() != 'default':
        #         text = name + ' (default)'
        #
        #     action = QAction(text, self)
        #     action.setEnabled(enabled)
        #     action_callback = partial(self._on_show_library, name, path, **kwargs)
        #     action.triggered.connect(action_callback)
        #     self.addAction(action)

    def _on_show_library(self, name, path, **kwargs):
        """
        Internal callback function that shows the library window which has given name and path
        :param name: str
        :param path: str
        :param kwargs: dict
        """

        raise NotImplementedError()
