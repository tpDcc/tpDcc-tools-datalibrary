#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library item tree view implementation
"""

from __future__ import print_function, division, absolute_import

import logging
from functools import partial

from Qt.QtCore import Qt
from Qt.QtWidgets import QApplication, QTreeWidget, QAbstractItemView, QMenu
from Qt.QtGui import QCursor, QFontMetrics, QClipboard

from tpDcc.libs.python import python

from tpDcc.tools.datalibrary.core import consts
from tpDcc.tools.datalibrary.data import group
from tpDcc.tools.datalibrary.widgets import mixinview

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class ViewerTreeView(mixinview.ViewerViewWidgetMixin, QTreeWidget):
    def __init__(self, *args, **kwargs):
        QTreeWidget.__init__(self, *args, **kwargs)
        mixinview.ViewerViewWidgetMixin.__init__(self)

        self._header_labels = list()
        self._hidden_columns = dict()

        self.setAutoScroll(False)
        self.setMouseTracking(True)
        self.setSortingEnabled(False)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        header = self.header()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._on_show_header_menu)

        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    # ============================================================================================================
    # OVERRIDES - MIXIN
    # ============================================================================================================

    def mouseMoveEvent(self, event):
        """
        Triggered when the user moves the mouse over the current viewport
        :param event: QMouseEvent
        """

        mixinview.ViewerViewWidgetMixin.mouseMoveEvent(self, event)
        QTreeWidget.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        """
        Triggered when the user releases the mouse button on the viewport
        :param event: QMouseEvent
        """

        mixinview.ViewerViewWidgetMixin.mouseReleaseEvent(self, event)
        QTreeWidget.mouseReleaseEvent(self, event)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def drawRow(self, painter, options, index):
        """
        Overrides base QTreeWidget drawDrow function
        :param painter: QPainter
        :param options: QStyleOption
        :param index: QModelIndex
        """

        item = self.itemFromIndex(index)
        item.paint_row(painter, options, index)

    def items(self):
        """
        Overrides base QTreeWidget items function
        Return a list of all items in the tree widget
        :return: list(LibraryItem)
        """

        items_list = list()
        for item in self._items():
            if not isinstance(item, group.GroupDataItemView):
                items_list.append(item)

        return items_list

    def selectedItems(self):
        """
        Overrides base QTreeWidget selectedItems function
        Returns all selected items
        :return: list(LibraryItem)
        """

        items_list = list()
        items_ = super(ViewerTreeView, self).selectedItems()

        for item in items_:
            if not isinstance(item, group.GroupDataItemView):
                items_list.append(item)

        return items_list

    def setColumnHidden(self, column, value):
        """
        Overrides base QTreeWidget setColumnHidden function
        :param column: int or str
        :param value: bool
        """

        if python.is_string(column):
            column = self.column_from_label(column)

        label = self.label_from_column(column)
        self._hidden_columns[label] = value

        super(ViewerTreeView, self).setColumnHidden(column, value)

        width = self.columnWidth(column)
        if width < consts.TREE_MINIMUM_WIDTH:
            width = consts.TREE_DEFAULT_WIDTH
            self.setColumnWidth(column, width)

    def resizeColumnToContents(self, column):
        """
        Overrides base QTreeWidget resizeColumnToContents function
        Resize the given column to the data of that column
        :param column: int or str
        """

        width = 0
        for item in self.items():
            text = item.text(column)
            font = item.font(column)
            metrics = QFontMetrics(font)
            text_width = metrics.width(text) + item.padding()
            width = max(width, text_width)

        self.setColumnWidth(column, width)

    def setHeaderLabels(self, labels):
        """
        Overrides base QTreeWidget setHeaderLabels function
        :param labels: list(str)
        """

        s = set()
        sadd = s.add
        labels = [x for x in labels if x.strip() and not (x in s or sadd(x))]

        if 'Custom Order' not in labels:
            labels.append('Custom Order')
        self.setColumnHidden('Custom Order', True)

        column_settings = self.column_settings()
        super(ViewerTreeView, self).setHeaderLabels(labels)
        self._header_labels = labels
        self.update_column_hidden()
        self.set_column_settings(column_settings)

    def clear(self, *args):
        """
        Overrides base QTreeWidget clear function
        Clear all dirty tree items
        """

        super(ViewerTreeView, self).clear(*args)
        self.clean_dirty_objects()

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def set_items(self, items):
        """
        Add given items to the tree, clearing the tree first
        :param items: list(LibraryItem)
        """

        selected_items = self.selectedItems()
        self.take_top_level_items()
        self.addTopLevelItems(items)
        self.set_items_selected(selected_items, True)

    def set_items_selected(self, items, value, scroll_to=True):
        """
        Selects the given library items
        :param items: list(LibraryItem)
        :param value: bool, Whether to select or deselect the items
        :param scroll_to: bool, Whether to scroll or not to selected items
        """

        for item in items:
            self.setItemSelected(item, value)
        if scroll_to:
            self.viewer().scroll_to_selected_item()

    def selected_item(self):
        """
        Returns the last non-hidden selected item
        :return: LibraryItem
        """

        items = self.selectedItems()
        if items:
            return items[-1]

        return None

    def take_top_level_items(self):
        """
        Returns all items from the tree widget
        :return: list(LibraryItem)
        """

        items_list = list()
        for item in self._items():
            # It is faster to take from first index
            items_list.append(self.takeTopLevelItem(1))
        items_list.append(self.takeTopLevelItem(0))

        return items_list

    def text_from_items(self, items, column, split=None, duplicates=False):
        """
        Returns all the text data for the given items and column
        :param items: list(LibraryItem)
        :param column: int or str
        :param split: str
        :param duplicates: bool
        :return: list(str)
        """

        results = list()

        for item in items:
            text = item.text(column)
            if text and split:
                results.extend(text.split(split))
            elif text:
                results.append(text)
        if not duplicates:
            results = list(set(results))

        return results

    def text_from_column(self, column, split=None, duplicates=False):
        """
        Returns all data for the given column
        :param column: int or str
        :param split: str
        :param duplicates: bool
        :return: list(str)
        """

        items_list = self.items()
        results = self.text_from_items(items_list, column, split=split, duplicates=duplicates)

        return results

    def header_labels(self):
        """
        Returns all header labels
        :return: list(str)
        """

        return self._header_labels

    def is_header_label(self, label):
        """
        Returns whether given label is a valid header label or not
        :param label: str
        :return: bool
        """

        return label in self._header_labels

    def column_labels(self):
        """
        Returns all header labels for the tree widget
        :return: list(str)
        """

        return self.header_labels()

    def column_from_label(self, label):
        """
        Returns the column for the given label
        :param label: str
        :return: int
        """

        try:
            return self._header_labels.index(label)
        except ValueError:
            return -1

    def label_from_column(self, column):
        """
        Returns the column label for the given column
        :param column: int
        :return: str
        """

        if column is not None:
            return self.headerItem().text(column)

    def item_row(self, item):
        """
        Returns the row for the given item
        :param item: LibraryItem
        :return: int
        """

        index = self.indexFromItem(item)
        return index.row()

    def row_at(self, pos):
        """
        Returns the row for the given position
        :param pos: QPoint
        :return: int
        """

        item = self.itemAt(pos)
        return self.item_row(item)

    def show_all_columns(self):
        """
        Show all available columns
        """

        for column in range(self.columnCount()):
            self.setColumnHidden(column, False)

    def hide_all_columns(self):
        """
        Hide all available columns
        """

        for column in range(1, self.columnCount()):
            self.setColumnHidden(column, True)

    def update_column_hidden(self):
        """
        Updates the hidden state for all the current columns
        """

        self.show_all_columns()
        column_labels = list(self._hidden_columns.keys())
        for column_label in column_labels:
            self.setColumnHidden(column_label, self._hidden_columns[column_label])

    # ============================================================================================================
    # CUSTOM ORDER
    # ============================================================================================================

    def is_sort_by_custom_order(self):
        """
        Returns True if items are currently sorted by custom order
        :return: bool
        """

        return 'Custom Order' in str(self.viewer().library().sort_by())

    def items_custom_order(self):
        """
        Returns the items sorted by hte custom order data
        :return: list(DataItem)
        """

        items = self.items()

        def sort_key(item):
            return item.item_data().get('Custom Order', 0)

        custom_order = sorted(items, key=sort_key)

        return custom_order

    def set_items_custom_order(self, items, row=1, padding=5):
        """
        Sets the custom order for the given items by their list order
        :param items:
        :param row:
        :param padding:
        :return:
        """

        for item in items:
            item.item_data()['Custom Order'] = str(row).zfill(padding)
            row += 1

    def move_items(self, items, item_at):
        """
        Moves the given items to the position of the target row
        :param items: list(DataItem)
        :param item_at: DataItem
        """

        row = 0
        ordered_items = self.items_custom_order()
        if item_at:
            row = ordered_items.index(item_at)
        removed_items = list()

        for item in items:
            index = ordered_items.index(item)
            removed_items.append(ordered_items.pop(index))

        for item in removed_items:
            ordered_items.insert(row, item)

        self.set_items_custom_order(ordered_items)

        for item in items:
            item.setSelected(True)

        self.viewer().scroll_to_selected_item()

    # ============================================================================================================
    # CLIPBOARD
    # ============================================================================================================

    def copy_text(self, column):
        """
        Copy the given column text to clipboard
        :param column: int or text
        """

        items = self.selectedItems()
        text = '\n'.join([item.text(column) for item in items])
        clipboard = QApplication.clipboard()
        clipboard.setText(text, QClipboard.Clipboard)

    def create_copy_text_menu(self):
        """
        Creates a menu to cpoy the selected item data to the clipboard
        :return: QMenu
        """

        menu = QMenu('Copy Text', self)
        if self.selectedItems():
            for column in range(self.columnCount()):
                label = self.label_from_column(column)
                action = menu.addAction(label)
                action_callback = partial(self.copy_text, column)
                action.triggered.connect(action_callback)
        else:
            action = menu.addAction('No items selected')
            action.setEnabled(False)

        return menu

    # ============================================================================================================
    # MENUS
    # ============================================================================================================

    def show_header_menu(self, pos):
        """
        Creates and show the header menu at the cursor position
        :param pos: QPoint
        :return: QMenu
        """

        header = self.header()
        column = header.logicalIndexAt(pos)
        menu = self._create_header_menu(column)
        menu.addSeparator()
        sub_menu = self._create_hide_column_menu()
        menu.addMenu(sub_menu)
        menu.exec_(QCursor.pos())

    # ============================================================================================================
    # SETTINGS
    # ============================================================================================================

    def settings(self):
        """
        Returns the current widget settings
        :return: dict
        """

        settings = dict()
        settings['columnSettings'] = self.column_settings()

        return settings

    def set_settings(self, settings):
        """
        Sets the current widget settings
        :param settings: dict
        :return: dict
        """

        column_settings = settings.get('columnSettings', dict())
        self.set_column_settings(column_settings)

        return settings

    def column_settings(self):
        """
        Returns the settings for each column
        :return: dict
        """

        column_settings = dict()

        for column in range(self.columnCount()):
            label = self.label_from_column(column)
            hidden = self.isColumnHidden(column)
            width = self.columnWidth(column)
            column_settings[label] = {
                'index': column,
                'hidden': hidden,
                'width': width
            }

        return column_settings

    def set_column_settings(self, settings):
        """
        Set the settings for each column
        :param settings: dict
        """

        for label in settings:
            if self.is_header_label(label):
                column = self.column_from_label(label)
                width = settings[label].get('width', 100)
                if width < consts.TREE_MINIMUM_WIDTH:
                    width = consts.TREE_DEFAULT_WIDTH
                self.setColumnWidth(column, width)
                hidden = settings[label].get('hidden', False)
                self.setColumnHidden(column, hidden)
            else:
                LOGGER.debug('Cannot set the column setting for header label: {}'.format(label))

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _items(self):
        """
        Internal function that returns a list of all items in the tree widget
        :return: list(LibraryItem)
        """

        return self.findItems('*', Qt.MatchWildcard | Qt.MatchRecursive)

    def _create_header_menu(self, column):
        """
        Internal function that creates a new header menu
        :param column, iht
        :return: QMenu
        """

        menu = QMenu(self)
        label = self.label_from_column(column)
        hide_action = menu.addAction('Hide "{}"'.format(label))
        hide_callback = partial(self.setColumnHidden, column, True)
        hide_action.triggered.connect(hide_callback)
        menu.addSeparator()
        resize_action = menu.addAction('Resize to Contents')
        resize_callback = partial(self.resizeColumnToContents, column)
        resize_action.triggered.connect(resize_callback)

        return menu

    def _create_hide_column_menu(self):
        """
        Internal function that creates the hide column menu
        :return: QMenu
        """

        menu = QMenu('Show/Hide Column', self)
        show_all_action = menu.addAction('Show All')
        show_all_action.triggered.connect(self.show_all_columns)
        hide_all_action = menu.addAction('Hide All')
        hide_all_action.triggered.connect(self.hide_all_columns)
        menu.addSeparator()
        for column in range(self.columnCount()):
            label = self.label_from_column(column)
            is_hidden = self.isColumnHidden(column)
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(not is_hidden)
            action_callback = partial(self.setColumnHidden, column, not is_hidden)
            action.triggered.connect(action_callback)

        return menu

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_show_header_menu(self):
        pass

    def _on_item_clicked(self, item):
        item.clicked()

    def _on_item_double_clicked(self, item):
        item.double_clicked()
