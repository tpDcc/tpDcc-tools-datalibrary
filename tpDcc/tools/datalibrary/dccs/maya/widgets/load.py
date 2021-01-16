#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains load widget for data items implementation for Maya
"""

from __future__ import print_function, division, absolute_import

import logging

from tpDcc.tools.datalibrary.widgets import load

LOGGER = logging.getLogger('tpDcc-tools-datalibrary')


class MayaLoadWidget(load.BaseLoadWidget):
    def __init__(self, client, item_view, *args, **kwargs):
        super(MayaLoadWidget, self).__init__(client=client, item_view=item_view, *args, **kwargs)

        item = self.item()
        if item:
            self._export_btn.setVisible(bool(item.functionality().get('export_data', False)))
            self._import_btn.setVisible(bool(item.functionality().get('import_data', False)))
            self._reference_btn.setVisible(bool(item.functionality().get('reference_data', False)))

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def ui(self):
        super(MayaLoadWidget, self).ui()

        # self._selection_set_button = buttons.BaseButton(parent=self)
        # self._selection_set_button.setIcon(resources.icon('group_objects'))

    def setup_signals(self):
        super(MayaLoadWidget, self).setup_signals()
        # self._selection_set_button.clicked.connect(self._on_show_selection_sets_menu)

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_show_selection_sets_menu(self):
        """
        Internal callback function that shows selection sets menu
        """

        item = self.item()
        item.show_selection_sets_menu()
