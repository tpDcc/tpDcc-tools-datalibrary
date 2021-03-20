#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains data library sort by menu widget implementation
"""

from __future__ import print_function, division, absolute_import

from functools import partial

from Qt.QtWidgets import QMenu
from Qt.QtGui import QCursor

from tpDcc.libs.qt.widgets import action


class SortByMenu(QMenu, object):
    def __init__(self, *args, **kwargs):
        super(SortByMenu, self).__init__(*args, **kwargs)

        self._library = None

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def show(self, point=None):
        """
        Overrides base QMenu show function
        :param point: QPoint
        """

        self.clear()

        sort_by = self.library().sort_by()
        if sort_by:
            current_field = self.library().sort_by()[0].split(':')[0]
            current_order = 'dsc' if 'dsc' in self.library().sort_by()[0] else 'asc'
        else:
            current_field = ''
            current_order = ''

        separator_action = action.SeparatorAction('Sort By', self)
        self.addAction(separator_action)

        fields = self.library().fields()
        for field in fields:
            if not field.get('sortable'):
                continue
            name = field.get('name')
            field_action = self.addAction(name.title())
            field_action.setCheckable(True)
            field_action.setChecked(bool(current_field == name))
            field_callback = partial(self.set_sort_by, name, current_order)
            field_action.triggered.connect(field_callback)

        separator_action = action.SeparatorAction('Sort Order', self)
        self.addAction(separator_action)

        ascending_action = self.addAction('Ascending')
        ascending_action.setCheckable(True)
        ascending_action.setChecked(bool(current_order == 'asc'))
        ascending_callback = partial(self.set_sort_by, current_field, 'asc')
        ascending_action.triggered.connect(ascending_callback)

        descending_action = self.addAction('Descending')
        descending_action.setCheckable(True)
        descending_action.setChecked(bool(current_order == 'dsc'))
        descending_callback = partial(self.set_sort_by, current_field, 'dsc')
        descending_action.triggered.connect(descending_callback)

        poinrt = point or QCursor.pos()

        self.exec_(point)

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def library(self):
        """
        Returns the library model for the menu
        :return: Library
        """

        return self._library

    def set_library(self, library):
        """
        Set the library model for the menu
        :param library: Library
        """

        self._library = library

    def set_sort_by(self, sort_name, sort_order):
        """
        Sets the sort by value for the library
        :param sort_name: str
        :param sort_order: str
        """

        if sort_name == 'Custom Order':
            sort_order = 'asc'

        value = sort_name + ':' + sort_order
        self.library().set_sort_by([value])
        self.library().search()
