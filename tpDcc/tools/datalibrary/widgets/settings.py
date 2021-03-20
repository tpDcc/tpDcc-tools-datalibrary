#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains widgets related with data functionality
"""

from __future__ import print_function, division, absolute_import

from tpDcc.managers import resources
from tpDcc.libs.qt.core import preferences
from tpDcc.libs.qt.widgets import label, layouts, combobox


class DataRepositoryWidget(preferences.CategoryWidgetBase, object):

    CATEGORY = 'Repository'

    def __init__(self, parent=None):
        super(DataRepositoryWidget, self).__init__(parent=parent)

        self._fill_version_types_combo()

    def ui(self):
        super(DataRepositoryWidget, self).ui()

        version_control_layout = layouts.HorizontalLayout()
        version_control_label = label.BaseLabel('Version Control', parent=None)
        self._version_type_combo = combobox.BaseComboBox(parent=self)
        version_control_layout.addWidget(version_control_label)
        version_control_layout.addWidget(self._version_type_combo)

        self.main_layout.addLayout(version_control_layout)
        self.main_layout.addStretch()

    def init_defaults(self, settings):
        if not settings:
            return

        settings.set('version_control', 0, setting_group='Version')

    def show_widget(self, settings):
        if not settings:
            return

        version_control = settings.get('version_control', default_value=0, setting_group='Version')

        self._version_type_combo.setCurrentIndex(int(version_control))

    def serialize(self, settings):
        if not settings:
            return

        settings.set('version_control', self._version_type_combo.currentIndex(), setting_group='Version')

    def _fill_version_types_combo(self):
        """
        Internal callback function that fills with the different types of supported version controls
        """

        self._version_type_combo.clear()
        for version_type in ['none', 'git']:
            self._version_type_combo.addItem(resources.icon(version_type), version_type)
