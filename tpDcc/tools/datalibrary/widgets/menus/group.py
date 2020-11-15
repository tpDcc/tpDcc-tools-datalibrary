#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains data library group by menu widget implementation
"""

from __future__ import print_function, division, absolute_import

from functools import partial

from Qt.QtWidgets import QMenu
from Qt.QtGui import QCursor

from tpDcc.libs.qt.widgets import action


class GroupByMenu(QMenu, object):
    def __init__(self, *args, **kwargs):
        super(GroupByMenu, self).__init__(*args, **kwargs)

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

        group_by = self.library().group_by()
        if group_by:
            current_field = group_by[0].split(':')[0]
            current_order = 'dsc' if 'dsc' in group_by[0]else 'asc'
        else:
            current_field = ''
            current_order = ''

        separator_action = action.SeparatorAction('Group By', self)
        self.addAction(separator_action)

        none_action = self.addAction('None')
        none_action.setCheckable(True)
        none_callback = partial(self.set_group_by, None, None)
        none_action.triggered.connect(none_callback)
        if not current_field:
            none_action.setChecked(True)

        fields = self.library().fields()
        for field in fields:
            if not field.get('groupable'):
                continue
            name = field.get('name')
            field_action = self.addAction(name.title())
            field_action.setCheckable(True)
            field_action.setChecked(bool(current_field == name))
            field_callback = partial(self.set_group_by, name, current_order)
            field_action.triggered.connect(field_callback)

        group_order_action = action.SeparatorAction('Group Order', self)
        self.addAction(group_order_action)

        ascending_action = self.addAction('Ascending')
        ascending_action.setCheckable(True)
        ascending_action.setChecked(bool(current_order == 'asc'))
        ascending_callback = partial(self.set_group_by, current_field, 'asc')
        ascending_action.triggered.connect(ascending_callback)

        descending_action = self.addAction('Descending')
        descending_action.setCheckable(True)
        descending_action.setChecked(bool(current_order == 'dsc'))
        descending_callback = partial(self.set_group_by, current_field, 'dsc')
        descending_action.triggered.connect(descending_callback)

        point = point or QCursor.pos()

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

    def set_group_by(self, group_name, group_order):
        """
        Sets the group by value for the library
        :param group_name: str
        :param group_order: str
        """

        if group_name:
            value = [group_name + ':' + group_order]
        else:
            value = None

        self.library().set_group_by(value)
        self.library().search()
