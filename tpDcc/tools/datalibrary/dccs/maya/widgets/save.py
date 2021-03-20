#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains save widget for data items implementation for Maya
"""

from __future__ import print_function, division, absolute_import

from Qt.QtGui import QCursor

from tpDcc.managers import resources
from tpDcc.libs.qt.widgets import buttons

from tpDcc.tools.datalibrary.widgets import save
from tpDcc.tools.datalibrary.dccs.maya.menus import sets


class MayaSaveWidget(save.BaseSaveWidget):
    def __init__(self, item_view, *args, **kwargs):
        super(MayaSaveWidget, self).__init__(item_view=item_view, *args, **kwargs)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def ui(self):
        super(MayaSaveWidget, self).ui()

        self._selection_set_button = buttons.BaseButton(parent=self)
        self._selection_set_button.setIcon(resources.icon('group_objects'))
        self._preview_buttons_layout.insertWidget(2, self._selection_set_button)

    def setup_signals(self):
        super(MayaSaveWidget, self).setup_signals()

        self._selection_set_button.clicked.connect(self._on_show_selection_sets_menu)

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_show_selection_sets_menu(self):
        """
        Internal callback function that shows the selection sets menu for the current folder path
        """

        path = self.folder_path()
        position = QCursor.pos()
        library_window = self.library_window()

        menu = sets.SetsMenu.from_path(path, library_window=library_window)
        menu.exec_(position)
