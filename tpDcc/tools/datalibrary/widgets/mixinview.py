#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains mixin implementation for library views
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt
from Qt.QtWidgets import QApplication, QAbstractItemView


class ViewerViewWidgetMixin(object):
    """
    Class that contains generic functionality for view widgets that
    work with QAbstractItemView
    """

    def __init__(self):
        self._hover_item = None
        self._mouse_press_button = None
        self._current_item = None
        self._current_selection = list()

    def selectionChanged(self, selected, deselected):
        """
        Triggered when the current item has been selected or deselected
        :param selected: QItemSelection
        :param deselected: QItemSelection
        """

        if hasattr(self, 'selectedItems'):
            selected_items_ = self.selectedItems()
        else:
            selected_items_ = self.selected_items()
        if self._current_selection != selected_items_:
            self._current_selection = selected_items_
            indexes1 = selected.indexes()
            selected_items = self.items_from_indexes(indexes1)
            indexes2 = deselected.indexes()
            deselected_items = self.items_from_indexes(indexes2)
            items = selected_items + deselected_items
            for item in items:
                item.selection_changed()

            QAbstractItemView.selectionChanged(self, selected, deselected)

    def wheelEvent(self, event):
        """
        Triggered on any wheel events for the current viewport
        :param event: QWheelEvent
        """

        if self.is_control_modifier():
            event.ignore()
        else:
            QAbstractItemView.wheelEvent(self, event)

        if hasattr(self, 'itemAt'):
            item = self.itemAt(event.pos())
        else:
            item = self.item_at(event.pos())
        self.item_update_event(item, event)

    def keyPressEvent(self, event):
        """
        Triggered when user key press events for the current viewport
        :param event: QKeyEvent
        """

        item = self.selected_item()
        if item:
            self.item_key_press_event(item, event)

        valid_keys = [Qt.Key_Up, Qt.Key_Left, Qt.Key_Down, Qt.Key_Right]
        if event.isAccepted() and event.key() in valid_keys:
            QAbstractItemView.keyPressEvent(event)

    def mousePressEvent(self, event):
        """
        Triggered on user mouse press events for the current viewport
        :param event: QMouseEvent
        """

        self._mouse_press_button = event.button()
        if hasattr(self, 'itemAt'):
            item = self.itemAt(event.pos())
        else:
            item = self.item_at(event.pos())
        if item:
            self.item_mouse_press_event(item, event)
        QAbstractItemView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """
        Triggered on user mouse release events for the current viewport
        :param event: QMouseEvent
        """

        self._mouse_press_button = None
        item = self.selected_item()
        if item:
            self.item_mouse_release_event(item, event)

    def mouseMoveEvent(self, event):
        """
        Triggered on user mouse move events for the current viewport
        :param event: QMouseEvent
        """

        if self._mouse_press_button == Qt.MiddleButton:
            item = self.selected_item()
        else:
            if hasattr(self, 'itemAt'):
                item = self.itemAt(event.pos())
            else:
                item = self.item_at(event.pos())

        self.item_update_event(item, event)

    def leaveEvent(self, event):
        """
        Triggered when the mouse leaves the widget
        :param event: QMouseEvent
        """

        if self._mouse_press_button != Qt.MiddleButton:
            self.item_update_event(None, event)

        QAbstractItemView.leaveEvent(self, event)

    def item_update_event(self, item, event):
        """
        Triggered when an item is updated
        :param item: LibraryItem
        :param event: QKeyEvent
        """

        self.clean_dirty_objects()

        if self._current_item != item:
            if self._current_item:
                self.item_mouse_leave_event(self._current_item, event)
                self._current_item = None
            if item and not self._current_item:
                self._current_item = item
                self.item_mouse_enter_event(item, event)

        if self._current_item:
            self.item_mouse_move_event(item, event)

    def item_mouse_enter_event(self, item, event):
        """
        Triggered when the mouse enters the given item
        :param item: QTreeWidgetItem
        :param event: QMouseEvent
        """

        item.mouse_enter_event(event)

    def item_mouse_leave_event(self, item, event):
        """
        Triggered when the mouse leaves the given item
        :param item: QTreeWidgetItem
        :param event: QMouseEvent
        """

        item.mouse_leave_event(event)

    def item_mouse_move_event(self, item, event):
        """
        Triggerd when the mouse moves withing the given item
        :param item: QTreeWidgetItem
        :param event: QMouseEvent
        """

        item.mouse_move_event(event)

    def item_mouse_press_event(self, item, event):
        """
        Triggered when the mouse is pressed on the given item
        :param item: QTreeWidgetItem
        :param event: QMouseEvent
        """

        item.mouse_press_event(event)

    def item_mouse_release_event(self, item, event):
        """
        Triggered when the mouse is released on the given item
        :param item: QTreeWidgetItem
        :param event: QMouseEvent
        """

        item.mouse_release_event(event)

    def item_key_press_event(self, item, event):
        """
        Triggered when a key is pressed for the selected item
        :param item: QTreeWidgetItem
        :param event: QKeyEvent
        """

        item.key_press_event(event)

    def item_key_release_event(self, item, event):
        """
        Triggered when a key is released for the selected item
        :param item: QTreeWidgetItem
        :param event: QKeyEvent
        """

        item.key_release_event(event)

    def mouse_press_button(self):
        """
        Returns the mouse button that has been pressed
        :return: Qt.MouseButton
        """

        return self._mouse_press_button

    def clean_dirty_objects(self):
        """
        Removes any obejct that may have been deleted
        """

        if self._current_item:
            try:
                self._current_item.text(0)
            except RuntimeError:
                self._hover_item = None
                self._current_item = None
                self._current_selection = None

    def viewer(self):
        """
        Returns parent widget of the library widget
        :return:
        """

        return self.parent()

    def is_control_modifier(self):
        """
        Returns whether control modifier is active or not
        :return: bool
        """

        modifiers = QApplication.keyboardModifiers()
        is_alt_modifier = modifiers == Qt.AltModifier
        is_ctrl_modifier = modifiers == Qt.ControlModifier
        return is_alt_modifier or is_ctrl_modifier

    def items_from_indexes(self, indexes):
        """
        Returns a list of QTreeWidgetItems associated with the given indexes
        :param indexes: list(QModelIndex)
        :return: list(QTreeWidgetItem)
        """

        items = dict()
        for index in indexes:
            if hasattr(self, 'itemFromIndex'):
                item = self.itemFromIndex(index)
            else:
                item = self.item_from_index(index)
            items[id(item)] = item

        return list(items.values())
