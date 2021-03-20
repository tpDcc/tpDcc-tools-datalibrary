#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Maya sets menu implementation
"""

from __future__ import print_function, division, absolute_import

import os
from functools import partial

from Qt.QtWidgets import QMenu, QAction
from Qt.QtGui import QCursor

from tpDcc.managers import resources
from tpDcc.tools.datalibrary.core import utils
# from tpDcc.libs.datalibrary.dccs.maya.data import setsitem


class SetsMenu(QMenu):
    def __init__(self, item, parent=None, namespaces=None, enable_select_content=True):
        super(SetsMenu, self).__init__('Selection Sets', parent or item.library_window())

        self._item = item
        self._namespaces = namespaces
        self._enable_select_content = enable_select_content

        # icon = resources.icon(setsitem.SetsItem.ICON_NAME)
        # self.setIcon(icon)

        self.reload()

    # ============================================================================================================
    # CLASS METHODS
    # ============================================================================================================

    @classmethod
    def from_path(cls, path, parent=None, library_window=None, **kwargs):
        """
        Returns a new SetsMenu from the given path
        :param path: str
        :param parent: QMenu or None
        :param library_window: LibraryWindow or None
        :param kwargs: dict
        :return: QAction
        """

        item = setsitem.SetsItem(path, library_window=library_window)
        return cls(item, parent, enable_select_content=False, **kwargs)

    @classmethod
    def show_sets_menu(cls, path, **kwargs):
        """
        Shows selection set menu at the current cursor position
        :param path: str
        :param kwargs: dict
        """

        menu = cls.from_path(path, **kwargs)
        pos = QCursor.pos()

        return menu.exec_(pos)

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def item(self):
        """
        Returns current item
        :return: MayaDataItem
        """

        return self._item

    def namespaces(self):
        """
        Returns item namespaces
        :return: list(str)
        """

        return self._namespaces

    def select_content(self):
        """
        Select item objects
        """

        self.item().select_content(namespaces=self.namespaces())

    def selection_sets(self):
        """
        :return: list(SetsItem)
        """

        def _match(path):
            return path.endswith('.set')

        items = list()
        library_window = self.item().library_window()

        # path = self.item().path()
        # paths = utils.walkup(path, match=_match, depth=10)
        # paths = list(paths)
        # for path in paths:
        #     item = setsitem.SetsItem(path)
        #     item.set_library_window(library_window)
        #     items.append(item)

        return items

    def reload(self):
        """
        Reloads current menu data
        """

        self.clear()

        if self._enable_select_content:
            select_content_action = QAction(resources.icon('cursor'), 'Select content', self)
            select_content_action.triggered.connect(self.item().select_content)
            self.addAction(select_content_action)
            self.addSeparator()

        selection_sets = self.selection_sets()
        if not selection_sets:
            action = QAction('No selection sets found!', self)
            action.setEnabled(False)
            self.addAction(action)
            return

        for selection_set in selection_sets:
            dirname = os.path.basename(os.path.dirname(selection_set.path()))
            basename = os.path.basename(selection_set.path()).replace(selection_set.EXTENSION, '')
            nice_name = '{}: {}'.format(dirname, basename)
            selection_set_action = QAction(nice_name, self)
            selection_set_action_callback = partial(selection_set.load, namespaces=self.namespaces())
            selection_set_action.triggered.connect(selection_set_action_callback)
            self.addAction(selection_set_action)
