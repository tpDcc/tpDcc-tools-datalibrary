#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library item widget implementation
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt, QRect, QSize
from Qt.QtWidgets import QTreeWidgetItem
from Qt.QtGui import QFontMetrics, QColor, QPen, QBrush

from tpDcc.tools.datalibrary.core import consts
from tpDcc.tools.datalibrary.core.views import item


class GroupDataItemView(item.ItemView, object):
    """
    Class that defines group of items
    """

    NAME = 'Group View'

    DEFAULT_FONT_SIZE = consts.GROUP_ITEM_DEFAULT_FONT_SIZE
    PADDING_LEFT = consts.GROUP_ITEM_PADDING_LEFT
    PADDING_RIGHT = consts.GROUP_ITEM_PADDING_RIGHT
    HEIGHT = consts.GROUP_ITEM_HEIGHT

    def __init__(self, *args):
        super(GroupDataItemView, self).__init__(data_item=None, *args)

        self._children = list()

        self._font = self.font(0)
        self._font.setBold(True)

        self._data = dict()

        self.setFont(0, self._font)
        self.setFont(1, self._font)
        self.set_drag_enabled(False)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def textAlignment(self, column):
        """
        Overrides base LibraryItem textAlignment function
        :param column: int
        """

        return QTreeWidgetItem.textAlignment(self, column)

    def sizeHint(self, column=0):
        """
        Overrides base sizeHint textAlignment function
        Returns the size hint of the item
        :param column: int
        :return: QSize
        """

        padding = self.PADDING_RIGHT * self.dpi()
        width = self.viewer().width() - padding
        return QSize(width, self.HEIGHT * self.dpi())

    def visualRect(self, option):
        """
        Overrides base sizeHint visualRect function
        Returns the visual rect for the item
        :param option: QStyleOptionViewItem
        :return: QRect
        """
        rect = QRect(option.rect)
        rect.setX(self.PADDING_LEFT * self.dpi())
        rect.setWidth(self.sizeHint().width())
        return rect

    def backgroundColor(self):
        """
        Overrides base sizeHint backgroundColor function
        Return the background color for the item.
        :rtype: QtWidgets.QtColor
        """
        return QColor(0, 0, 0, 0)

    def icon(*args):
        """
        Overrides base sizeHint icon function
        Override so icon is not displayed
        :param args:
        :return:
        """
        return None

    def is_label_over_item(self):
        """
        Override function to ignore this feature for group items
        :return: bool
        """

        return False

    def is_label_under_item(self):
        """
        Override function to ignore this feature for group items
        :return: bool
        """

        return False

    def paint_row(self, painter, option, index):
        """
        Overrides base paint_row icon function
        Paint performs low-level painting for the item
        :param painter: QPainter
        :param option: QStyleOptionViewItem
        :param index: QModelIndex
        """

        self.set_rect(QRect(option.rect()))
        painter.save()
        try:
            self.paint_background(painter, option, index)
            if self.is_text_visible():
                self._paint_text(painter, option, 1)
            # self.paint_icon(painter, option, index)
        finally:
            painter.restore()

    def paint_background(self, painter, option, index):
        """
        Overrides base paint_background icon function
        Draw the background for the item
        :param painter: QPainter
        :param option: QStyleOptionViewItem
        :param index: QModelIndex
        """

        super(GroupDataItemView, self).paint_background(painter, option, index)

        painter.setPen(QPen(Qt.NoPen))
        visual_rect = self.visualRect(option)
        text = self.name()
        metrics = QFontMetrics(self._font)
        text_width = metrics.width(text)
        padding = (25 * self.dpi())
        visual_rect.setX(text_width + padding)
        visual_rect.setY(visual_rect.y() + (visual_rect.height() / 2))
        visual_rect.setHeight(2 * self.dpi())
        visual_rect.setWidth(visual_rect.width() - padding)

        color = QColor(self.text_color().red(), self.text_color().green(), self.text_color().blue(), 10)
        painter.setBrush(QBrush(color))
        painter.drawRect(visual_rect)

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def name(self):
        return self._data.get('name')

    def set_name(self, name):
        self._data['name'] = name

    def children(self):
        """
        Returns the children for the group
        :return: list(LibraryItem)
        """

        return self._children

    def set_children(self, children):
        """
        Sets the children for the group
        :param children: list(LibraryItem)
        """

        self._children = children

    def children_hidden(self):
        """
        Returns whether children are hidden or not
        :return: bool
        """

        for child in self.children():
            if not child.isHidden():
                return False

        return True

    def update_children(self):
        """
        Updates the visibility if all children are hidden
        :return:
        """

        self.setHidden(bool(self.children_hidden()))

    def is_text_visible(self):
        """
        Returns whether the text is visible or not
        :return: bool
        """

        return True

    def text_selected_color(self):
        """
        Returns the selected text color for the item
        :return: QColor
        """

        return self.viewer().text_color()

    def background_hover_color(self):
        """
        Return the background color when the mouse is over the item.
        :rtype: QtWidgets.QtColor
        """
        return QColor(0, 0, 0, 0)

    def background_selected_color(self):
        """
        Return the background color when the item is selected.
        :rtype: QtWidgets.QtColor
        """
        return QColor(0, 0, 0, 0)
