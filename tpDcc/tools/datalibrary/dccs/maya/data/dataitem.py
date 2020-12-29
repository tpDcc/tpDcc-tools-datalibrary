#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library data item implementation for Maya
"""

from __future__ import print_function, division, absolute_import

import logging

from Qt.QtWidgets import QAction
from Qt.QtGui import QCursor

from tpDcc.managers import resources
from tpDcc.tools.datalibrary.data import base

LOGGER = logging.getLogger('tpDcc-tools-datalibrary')


class MayaDataItemView(base.BaseDataItemView):
    def __init__(self, *args, **kwargs):
        super(MayaDataItemView, self).__init__(*args, **kwargs)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def context_menu(self, menu, items=None):
        """
        Returns the context menu for the item
        :return: QMenu
        """

        super(MayaDataItemView, self).context_menu(menu, items=items)

        clean_student_license_function = self.item.functionality().get('clean_student_license')
        if clean_student_license_function:
            clean_student_license_action = QAction(resources.icon('student'), 'Clean Student License', menu)
            menu.addAction(clean_student_license_action)
            clean_student_license_action.triggered.connect(lambda: clean_student_license_function())

        menu.addSeparator()
        create_selection_sets_menu = self._create_selection_sets_menu(menu, enable_select_content=False)
        menu.insertMenu(self._select_content_action, create_selection_sets_menu)

    def select_content(self, namespaces=None, **kwargs):
        """
        Select the contents of this item in the current DCC scene
        :param namespaces: list(str) or None
        :param kwargs: dict
        """

        namespaces = namespaces or self.namespaces()
        kwargs = kwargs or self._selection_modifiers()
        msg = 'Select content: Item.selectContent(namespaces={}, kwargs={})'.format(namespaces, kwargs)
        LOGGER.debug(msg)

        try:
            self.transfer_object().select(namespaces=namespaces, **kwargs)
        except Exception as exc:
            self.show_error_dialog('Item Error', str(exc))
            raise

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def namespaces(self):
        """
        Returns the namespaces for this item depending on the namespace option
        :return: list(str) or None
        """

        return list()

        # return self.current_load_value('namespaces')

    def namespace_option(self):
        """
        Returns the namespace option for this item
        :return: NamespaceOption or None
        """

        return self.current_load_value('namespaceOption')

    def show_selection_sets_menu(self, **kwargs):
        """
        Shows the selection sets menu for this item at the current cursor position
        :param kwargs: dict
        :return: QAction
        """

        menu = self._create_selection_sets_menu(**kwargs)
        position = QCursor.pos()

        return menu.exec_(position)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _create_selection_sets_menu(self, parent=None, enable_select_content=True):
        """
        Internal function that crates a new instance of the selection sets menu
        :param parent: QWidget
        :param enable_select_content:, bool
        :return: QMenu
        """

        # Import here to avoid cycles in Python 2
        from tpDcc.tools.datalibrary.dccs.maya.menus import sets

        parent = parent or self.library_window()
        namespaces = self.namespaces()
        menu = sets.SetsMenu(
            item=self, parent=parent, namespaces=namespaces, enable_select_content=enable_select_content)

        return menu
