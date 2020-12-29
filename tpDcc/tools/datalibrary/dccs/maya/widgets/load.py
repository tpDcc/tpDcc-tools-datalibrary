#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains load widget for data items implementation for Maya
"""

from __future__ import print_function, division, absolute_import

from Qt.QtWidgets import QFrame

from tpDcc.managers import resources
from tpDcc.libs.qt.widgets import layouts, buttons

from tpDcc.tools.datalibrary.widgets import load


class MayaLoadWidget(load.BaseLoadWidget):
    def __init__(self, item_view, *args, **kwargs):
        super(MayaLoadWidget, self).__init__(item_view=item_view, *args, **kwargs)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def ui(self):
        super(MayaLoadWidget, self).ui()

        self._selection_set_button = buttons.BaseButton(parent=self)
        self._selection_set_button.setIcon(resources.icon('group_objects'))

        self._export_btn = buttons.BaseButton('Export', parent=self)
        self._export_btn.setIcon(resources.icon('export'))
        self._import_btn = buttons.BaseButton('Import', parent=self)
        self._import_btn.setIcon(resources.icon('import'))
        self._reference_btn = buttons.BaseButton('Reference', parent=self)
        self._reference_btn.setIcon(resources.icon('reference'))

        for btn in [self._export_btn, self._import_btn, self._reference_btn]:
            btn.setToolTip(btn.text())

        extra_buttons_frame = QFrame(self)
        extra_buttons_layout = layouts.HorizontalLayout(spacing=2, margins=(0, 0, 0, 0))
        extra_buttons_frame.setLayout(extra_buttons_layout)
        extra_buttons_layout.addWidget(self._export_btn)
        extra_buttons_layout.addWidget(self._import_btn)
        extra_buttons_layout.addWidget(self._reference_btn)

        self._preview_buttons_frame.layout().insertWidget(2, self._selection_set_button)
        self.main_layout.addWidget(extra_buttons_frame)

    def setup_signals(self):
        super(MayaLoadWidget, self).setup_signals()

        self._selection_set_button.clicked.connect(self._on_show_selection_sets_menu)

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_show_selection_sets_menu(self):
        """
        Internal callback function that shows selection sets menu
        """

        item = self.item()
        item.show_selection_sets_menu()