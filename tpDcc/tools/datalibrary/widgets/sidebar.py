#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains sidebar data library widget implementation
"""

from __future__ import print_function, division, absolute_import

import os
import logging
from functools import partial
from collections import OrderedDict

from Qt.QtCore import Qt, Signal, QSize, QUrl, QEvent
from Qt.QtWidgets import QFrame, QTreeWidget, QTreeWidgetItem, QAbstractItemView
from Qt.QtGui import QCursor, QColor, QPixmap, QPainter, QBrush

from tpDcc.managers import resources
from tpDcc.libs.python import python, path as path_utils
from tpDcc.libs.resources.core import color, pixmap
from tpDcc.libs.qt.core import base, menu, contexts as qt_contexts
from tpDcc.libs.qt.widgets import layouts, buttons, search

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class SidebarWidget(base.BaseWidget):

    itemDropped = Signal(object)
    itemRenamed = Signal(str, str)
    settingsMenuRequested = Signal(object)

    def __init__(self, parent=None):

        self._library = None
        self._previous_filter_text = ''

        super(SidebarWidget, self).__init__(parent=parent)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def get_main_layout(self):
        return layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))

    def ui(self):
        super(SidebarWidget, self).ui()

        self._title_widget = QFrame(self)
        title_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        self._title_widget.setLayout(title_layout)

        buttons_layout = layouts.HorizontalLayout(spacing=0, margins=(0, 0, 0, 0))
        self._title_button = buttons.BaseButton(parent=self)
        self._title_button.setIcon(resources.icon('reset'))
        self._menu_button = buttons.BaseButton(parent=self)
        self._menu_button.setIcon(resources.icon('menu_dots'))
        buttons_layout.addWidget(self._title_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self._menu_button)

        self._filter_search = search.SearchFindWidget(parent=self)
        self._filter_search.setVisible(False)

        title_layout.addLayout(buttons_layout)
        title_layout.addWidget(self._filter_search)

        self._tree_widget = SidebarTree(self)
        self._tree_widget.installEventFilter(self)
        self._tree_widget.itemDropped = self.itemDropped
        self._tree_widget.itemRenamed = self.itemRenamed
        self.itemSelectionChanged = self._tree_widget.itemSelectionChanged

        self._filter_search.set_text(self._tree_widget.filter_text())

        self.main_layout.addWidget(self._title_widget)
        self.main_layout.addWidget(self._tree_widget)

    def setup_signals(self):
        self._title_button.clicked.connect(self.clear_selection)
        self._menu_button.clicked.connect(self._on_show_settings_menu)
        self._filter_search.textChanged.connect(self._on_search_changed)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            text = event.text().strip()
            if text.isalpha() or text.isdigit():
                if text and not self._filter_search.search_line.hasFocus():
                    self._filter_search.set_text(text)
                self.set_filter_visible(True)
                self._previous_filter_text = text

        return super(SidebarWidget, self).eventFilter(obj, event)

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

        if library == self._library:
            return

        self._library = library
        # self._library.dataChanged.connect(self._on_data_changed)
        # self._on_data_changed()

    def set_filter_visible(self, flag):
        """
        Sets whether or not filter widget is visible
        :param flag: bool
        """

        self._filter_search.setVisible(flag)
        self._filter_search.search_line.setFocus()
        if not flag and bool(self._tree_widget.filter_text()):
            self._tree_widget.set_filter_text('')
        else:
            self.refresh_filter()

    def search(self):
        if not self.library():
            LOGGER.info('No library found for sidebar widget')
            return

        self.library().add_query(self.query())
        self.library().search()

    def query(self):
        """
        Returns the query for the sidebar widget
        :return: dict
        """

        filters = list()

        for path in self.selected_paths():
            if self.is_recursive():
                filter_ = ('path', 'startswith', path + '/')
                filters.append(filter_)
            filter_ = ('path', 'not', path)
            filters.append(filter_)
        unique_name = 'sidebar_widget_' + str(id(self))
        return {'name': unique_name, 'operator': 'and', 'filters': filters}

    # ============================================================================================================
    # TREE HELPERS FUNCTIONS
    # ============================================================================================================

    def tree_widget(self):
        return self._tree_widget

    def set_dpi(self, dpi):
        self._tree_widget.set_dpi(dpi)

    def is_root_visible(self):
        return self._tree_widget.is_root_visible()

    def set_root_visible(self, flag):
        self._tree_widget.set_root_visible(flag)

    def filter_text(self):
        return self._tree_widget.filter_text()

    def set_filter_text(self, text):
        self._filter_search.set_text(text)

    def refresh_filter(self):
        self._tree_widget.set_filter_text(self._filter_search.get_text())

    def is_filter_visible(self):
        return bool(self._tree_widget.filter_text()) or self._filter_search.isVisible()

    def icons_visible(self):
        return self._tree_widget.icons_visible()

    def set_icons_visible(self, flag):
        self._tree_widget.set_icons_visible(flag)

    def is_recursive(self):
        return self._tree_widget.is_recursive()

    def set_recursive(self, flag):
        self._tree_widget.set_recursive(flag)

    def is_locked(self):
        return self._tree_widget.is_locked()

    def set_locked(self, flag):
        self._tree_widget.set_locked(flag)

    def set_data(self, *args, **kwargs):
        self._tree_widget.set_data(*args, **kwargs)

    def set_item_data(self, item_id, item_data):
        self._tree_widget.set_path_settings(item_id, item_data)

    def selected_path(self):
        return self._tree_widget.selected_path()

    def selected_paths(self):
        return self._tree_widget.selected_paths()

    def select_paths(self, paths):
        self._tree_widget.select_paths(paths)

    def clear_selection(self):
        self._tree_widget.clearSelection()

    # ============================================================================================================
    # SETTINGS
    # ============================================================================================================

    def settings(self):
        """
        Returns sidebar widget settings
        :return: dict
        """

        settings = self._tree_widget.settings()
        settings['filterText'] = self.filter_text()
        settings['filterVisible'] = self.is_filter_visible()

        return settings

    def set_settings(self, settings_dict):
        """
        Sets sidebar widget settings
        :param settings_dict: dict
        """

        value = settings_dict.get('filterText')
        if value is not None:
            self.set_filter_text(value)

        self._tree_widget.set_settings(settings_dict)
        value = settings_dict.get('filterVisible')
        if value is not None:
            self.set_filter_visible(value)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _filter_visible_trigger(self, flag):
        """
        Internal function that sets filter visible
        """

        self.set_filter_visible(flag)
        self._filter_search.select_all()

    def _create_settings_menu(self, settings_menu):
        """
        Internal function that creates sidebar settings context menu
        :param settings_menu: Menu
        :return: Menu
        """

        show_filter_action = settings_menu.addAction(resources.icon('filter'), 'Show Filter')
        show_filter_action.setCheckable(True)
        show_filter_action.setChecked(self.is_filter_visible())
        show_filter_action_callback = partial(self._filter_visible_trigger, not self.is_filter_visible())
        show_filter_action.triggered.connect(show_filter_action_callback)

        show_icons_action = settings_menu.addAction(resources.icon('icons'), 'Show Icons')
        show_icons_action.setCheckable(True)
        show_icons_action.setChecked(self.icons_visible())
        show_icons_action_callback = partial(self.set_icons_visible, not self.icons_visible())
        show_icons_action.triggered.connect(show_icons_action_callback)

        show_root_folder_action = settings_menu.addAction(resources.icon('folder_tree'), 'Show Root Folder')
        show_root_folder_action.setCheckable(True)
        show_root_folder_action.setChecked(self.is_root_visible())
        show_root_folder_action_callback = partial(self.set_root_visible, not self.is_root_visible())
        show_root_folder_action.triggered.connect(show_root_folder_action_callback)

        return settings_menu

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_data_changed(self):
        """
        Internal callback function that is triggered when the library data changes
        """

        pass

    def _on_search_changed(self, text):
        """
        Internal callback function called when the search filter has changed
        :param text: str
        """

        self.refresh_filter()
        if text:
            self.set_filter_visible(True)
        else:
            self._tree_widget.setFocus()
            self.set_filter_visible(False)

    def _on_show_settings_menu(self):
        settings_menu = menu.Menu(self)
        self.settingsMenuRequested.emit(settings_menu)
        self._create_settings_menu(settings_menu)
        point = QCursor.pos()
        point.setX(point.x() + 3)
        point.setY(point.y() + 3)
        settings_menu.exec_(point)
        settings_menu.close()


class SidebarTree(QTreeWidget):

    DEFAULT_SEPARATOR = '/'

    itemDropped = Signal(object)
    itemRenamed = Signal(str, str)
    itemSelectionChanged = Signal()     # This is overriding an standard signal.Check if this can cause problems.

    def __init__(self, *args, **kwargs):
        super(SidebarTree, self).__init__(*args, **kwargs)

        self._dpi = 1.0
        self._data = list()
        self._items = list()
        self._index = dict()
        self._locked = False
        self._library = None
        self._recursive = True
        self._filter_text = ''
        self._root_visible = False
        self._icons_visible = True

        self._options = {
            'field': 'path',
            'separator': '/',
            'recursive': True,
            'autoRootPath': True,
            'rootText': 'FOLDERS',
            'sortBy': None,
            'queries': [{'filters': [('type', 'is', 'Folder')]}]
        }

        self.set_dpi(1.0)

        self.setAcceptDrops(True)
        self.setHeaderHidden(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.itemExpanded.connect(self.update)
        self.itemCollapsed.connect(self.update)

    # ============================================================================================================
    # CLASS METHODS
    # ============================================================================================================

    @classmethod
    def find_root(cls, paths, separator=None):
        """
        Finds the common path for the given paths
        :param paths: list(str)
        :param separator: str
        :return: str
        """

        path = paths[0] if paths else ''
        result = None
        separator = separator or cls.DEFAULT_SEPARATOR
        tokens = path.split(separator)
        for i, token in enumerate(tokens):
            root = separator.join(tokens[:i + 1])
            match = True
            for path in paths:
                if not path.startswith(root + separator):
                    match = False
                    break
            if not match:
                break
            result = root

        return result

    @classmethod
    def paths_to_dict(cls, paths, root='', separator=None):
        """
        Returns the given paths as a nested dict
        paths = ['/test/a', '/test/b']
        Result = {'test' : {'a':{}}, {'b':{}}}
        :param paths: list(str)
        :param root: str
        :param separator: str or None
        :return: dict
        """

        separator = separator or cls.DEFAULT_SEPARATOR
        results = OrderedDict()
        paths = path_utils.normalize_paths(paths)

        for path in paths:
            p = results
            # This is to add support for grouping by the given root path.
            if root and root in path:
                path = path.replace(root, "")
                p = p.setdefault(root, OrderedDict())
            keys = path.split(separator)[0:]
            for key in keys:
                if key:
                    p = p.setdefault(key, OrderedDict())

        return results

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def items(self):
        """
        Returns a list of all the items in the tree widget
        :return: list(QTreeWidgetItem)
        """

        items = self.findItems('*', Qt.MatchWildcard | Qt.MatchRecursive)
        return items

    def itemAt(self, pos):
        """
        Overrides base QTreeWidget itemAt function
        :param pos: QPoint
        :return:
        """

        index = self.indexAt(pos)
        if not index.isVaild():
            return None

        return self.itemFromIndex(index)

    def selectionChanged(self, *args):
        """
        Overrides base QTreeWidget selectionChanged function
        :param args:
        :return:
        """

        self.parent().search()

    def dragEnterEvent(self, event):
        """
        Overrides base QTreeWidget dragMoveEvent function
        :param event: QEvent
        """

        mime_data = event.mimeData()
        if mime_data.hasUrls():
            event.accept()
        else:
            event.ignore()

        item = self.itemAt(event.pos())
        if item:
            self.select_paths([item.path()])

    def dragEnterEvent(self, event):
        """
        Overrides base QTreeWidget dragMoveEvent function
        :param event: QEvent
        """

        event.accept()

    def dropEvent(self, event):
        """
        Overrides base QTreeWidget dropEvent function
        :param event: QEvent
        """

        if self.is_locked():
            LOGGER.warning('Folder is locked! Cannot accept drop!')
            return

        self.itemDropped.emit(event)

    def clear(self):
        """
        Clears all the items from the tree widget
        """

        self._items = list()
        self._index = dict()
        super(SidebarTree, self).clear()

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def is_root_visible(self):
        """
        Returns whether or not root root item is visible
        :return: flag
        """

        return self._root_visible

    def set_root_visible(self, flag):
        """
        Sets whether or not root item is visible
        :param flag: bool
        """

        self._root_visible = flag
        self.refresh_data()

    def icons_visible(self):
        """
        Returns whether or not tree item icons are visible
        :return: bool
        """

        return self._icons_visible

    def set_icons_visible(self, flag):
        """
        Sets whether or not tree items icons are visible
        :param flag: bool
        """

        self._icons_visible = flag
        self.refresh_data()

    def is_locked(self):
        """
        Returns whether widget items are read only or not
        :return: bool
        """

        return self._locked

    def set_locked(self, locked):
        """
        Sets whether widget items are read only or not
        :param locked: bool
        """

        self._locked = locked

    def is_recursive(self):
        """
        Returns whether the recursive query is enabled or not
        :return: bool
        """

        return self._recursive

    def set_recursive(self, enable):
        """
        Sets whether recursive query is enabled or not
        :param enable: bool
        """

        self._recursive = enable
        self.parent().search()

    def separator(self):
        """
        Returns the separator used in the fields to seaprate level values
        :return: str
        """

        return self._options.get('separator', self.DEFAULT_SEPARATOR)

    def add_paths(self, paths, root='', split=None):
        """
        Set the given items as a flat list
        :param paths: list(str)
        :param root: str or None
        :param split: str or None
        """

        data = self.paths_to_dict(paths, root=root, separator=split)
        self.create_items(data, split=split)
        if isinstance(paths, dict):
            self.set_settings(paths)

    def select_item(self, item):
        """
        Selects given item
        :param item: QTreeWidgetItem
        """

        self.select_paths([item.path()])

    def selected_item(self):
        """
        Returns the current selected item
        :return: QTreeWidgetItem
        """

        path = self.selected_path()
        return self.item_from_path(path)

    def selected_path(self):
        """
        Returns the current selected path
        :return: str
        """
        paths = self.selected_paths()
        if paths:
            return paths[-1]

    def selected_paths(self):
        """
        Returns the paths that are selected
        :return: list(str)
        """

        paths = list()
        items = self.selectedItems()
        for item in items:
            path = item.path()
            paths.append(path)

        return path_utils.normalize_paths(paths)

    def select_path(self, path):
        """
        Selects the given path
        :param path: str
        """

        self.select_paths([path])

    def select_paths(self, paths):
        """
        Select the items with the given paths
        :param paths: list(str)
        """

        paths = path_utils.normalize_paths(paths)
        items = self.items()
        for item in items:
            if path_utils.clean_path(item.path()) in paths:
                item.setSelected(True)
            else:
                item.setSelected(False)

    def select_url(self, url):
        """
        Select the item with the given url
        :param url: str
        """

        items = self.items()
        for item in items:
            if item.url() == url:
                item.setSelected(True)
            else:
                item.setSelected(False)

    def selected_urls(self):
        """
        Returns the urls for the selected items
        :return: list(str)
        """

        urls = list()
        items = self.selectedItems()
        for item in items:
            urls.append(item.url())

        return urls

    def item_from_url(self, url):
        """
        Returns the item for the given URL
        :param url: QUrl
        :return: QTreeWidgetItem
        """

        for item in self.items():
            if url == item.url():
                return item

    def item_from_path(self, path):
        """
        Returns the item for the given path
        :param path: str
        :return: QTreeWidgetItem
        """

        return self._index.get(path)

    def expanded_items(self):
        """
        Returns all the expanded items
        :return: list(QTreeWidgetItem)
        """

        for item in self.items():
            if self.isItemExpanded(item):
                yield item

    def expanded_paths(self):
        """
        Returns all the expanded paths
        :return: list(QUrl)
        """

        for item in self.expanded_items():
            yield item.url()

    def set_expanded_paths(self, paths):
        """
        Sets the given paths as expanded
        :param paths: list(str)
        """

        for item in self.items():
            if item.url() in paths:
                item.setExpanded(True)

    def set_data(self, data, root='', split=None):
        """
        Sets the items to the given items
        :param data: list(str)
        :param root: str
        :param split: str
        """

        self._data = data
        settings = self.settings()
        with qt_contexts.block_signals(self):
            self.clear()
            if not root:
                root = self.find_root(list(data.keys()), self.separator())
            self.add_paths(data, root=root, split=split)
            self.set_settings(settings)

        self.parent().search()

    def refresh_data(self):
        """
        Updates current tree data
        """

        self.set_data(self._data)

    def create_items(self, data, split=None):
        """
        Creates the items from the given data dict
        :param data: dict
        :param split: str or None
        """

        split = split or self.DEFAULT_SEPARATOR
        self._index = dict()
        for key in data:
            root = split.join([key])
            item = None
            if self.is_root_visible():
                text = key.split(split)
                text = text[-1] if text else key
                item = SidebarTreeItem(self)
                item.setText(0, text)
                item.set_path(root)
                item.setExpanded(True)
                self._index[root] = item

            def _recursive(parent, children, split=None, root=''):
                for text, val in sorted(children.items()):
                    parent = parent or self
                    path = split.join([root, text]).replace('//', '/')

                    # TODO: Maybe we should move this into a filter?
                    # We do not show special folders that starts with '.'
                    if text.startswith('.'):
                        continue

                    child = SidebarTreeItem(parent)
                    child.setText(0, str(text))
                    child.set_path(path)
                    self._index[path] = child
                    _recursive(child, val, split=split, root=path)

            _recursive(item, data[key], split=split, root=root)

        self.update()
        self.refresh_filter()

    def filter_text(self):
        """
        Returns current filter text
        :return: str
        """

        return self._filter_text

    def set_filter_text(self, text):
        """
        Sets current filter text
        :param text: str
        """

        self._filter_text = text.strip()
        self.refresh_filter()

    def refresh_filter(self):
        """
        Refreshes current visible items depending the current filter text
        """

        items = self.items()
        for item in items:
            if self._filter_text.lower() in item.text(0).lower():
                item.setHidden(False)
                for parent in item.parents():
                    parent.setHidden(False)
            else:
                item.setHidden(True)

    def root_text(self):
        """
        Returns the root text
        :return: str
        """

        return self._options.get('rootText')

    def field(self):
        """
        Returns the field
        :return: str
        """

        return self._options.get('field', '')

    def sort_by(self):
        """
        Returns the sort by field
        :return: str
        """

        return self._options.get('sortBy', [self.field()])

    def update(self):
        """
        Updates current tree items
        """

        for item in self.items():
            item.update()

    # ============================================================================================================
    # DPI
    # ============================================================================================================

    def dpi(self):
        """
          Returns the zoom multiplier
          :return: float
          """

        return self._dpi

    def set_dpi(self, dpi):
        """
        Sets zoom multiplier
        :param dpi: float
        """

        self._dpi = dpi
        width = 20 * dpi
        height = 18 * dpi
        self.setIndentation(9 * dpi)
        self.setMinimumWidth(20 * dpi)
        self.setIconSize(QSize(width, height))
        self.setStyleSheet('height: {}px'.format(height))

    # ============================================================================================================
    # SETTINGS
    # ============================================================================================================

    def settings(self):
        """
        Returns the current state of the item as a dictionary
        :return: dict
        """

        settings = dict()

        vertical_scroll_bar = self.verticalScrollBar()
        horizontal_scroll_bar = self.horizontalScrollBar()
        settings['verticalScrollBar'] = {'value': vertical_scroll_bar.value()}
        settings['horizontalScrollBar'] = {'value': horizontal_scroll_bar.value()}

        for item in self.items():
            item_settings = item.settings()
            if item_settings:
                settings[item.path()] = item.settings()

        return settings

    def set_settings(self, settings_dict):
        """
        Sets the current state of the item from a dictionary
        :param settings_dict: dict
        """

        for path in sorted(list(settings_dict.keys())):
            setting_path = settings_dict.get(path, None)
            self.set_path_settings(path, setting_path)

        vertical_scrollbar_setting = settings_dict.get('verticalScrollBar', dict())
        value = vertical_scrollbar_setting.get('value', None)
        if value:
            self.verticalScrollBar().setValue(value)

        horizontal_scrollbar_setting = settings_dict.get('horizontalScrollBar', dict())
        value = horizontal_scrollbar_setting.get('value', None)
        if value:
            self.horizontalScrollBar().setValue(value)

        self.set_dpi(self.dpi())

    def set_path_settings(self, path, settings):
        """
        Set paths settings
        :param path: list(str)
        :param settings: dict
        """

        item = self.item_from_path(path)
        if item and settings:
            item.set_settings(settings)


class SidebarTreeItem(QTreeWidgetItem):

    _PIXMAP_CACHE = dict()

    def __init__(self, *args, **kwargs):
        super(SidebarTreeItem, self).__init__(*args, **kwargs)

        self._path = ''
        self._bold = None
        self._icon_visible = True
        self._icon_path = None
        self._icon_color = None
        self._text_color = None
        self._expanded_icon_path = None
        self._collapsed_icon_path = None

        self._settings = dict()

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def setSelected(self, flag):
        """
        Overrides base LibrarySideBarWidget setSelected function
        :param select: bool
        """

        super(SidebarTreeItem, self).setSelected(flag)
        if flag:
            self.set_expanded_parents(flag)

    def textColor(self):
        """
        Returns the foreground color of the item
        :return: QColor
        """

        clr = self.foreground(0).color()
        return color.Color.from_color(clr)

    def setTextColor(self, text_color):
        """
        Sets the foreground color to the given color
        :param text_color: variant, QColor or str
        """

        if isinstance(text_color, QColor):
            text_color = color.Color.from_color(text_color)
        elif python.is_string(text_color):
            text_color = color.Color.from_string(text_color)
        self._settings['textColor'] = text_color.to_string()
        brush = QBrush()
        brush.setColor(text_color)
        self.setForeground(0, brush)

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def path(self):
        """
        Returns item path
        :return: str
        """

        return self._path

    def set_path(self, path):
        """
        Sets the path for the item
        :param path: str
        """

        self._path = path

    def default_icon_path(self):
        """
        Returns the default icon path
        :return: str
        """

        return resources.get('icons', 'folder.svg')

    def icon_path(self):
        """
        Returns the icon path for the item
        :return: str
        """

        return self._icon_path or self.default_icon_path()

    def set_icon_path(self, path):
        """
        Sets the icon path for the item
        :param path: str
        """

        self._icon_path = path
        self.update_icon()

    def expanded_icon_path(self):
        """
        Returns the icon path to be shown when expanded
        :return: str
        """

        return self._expanded_icon_path or resources.get('icons', 'black', 'open_folder.png')

    def collapsed_icon_path(self):
        """
        Returns the icon path to be shown when collapsed
        :return: str
        """

        return self._collapsed_icon_path or resources.get('icons', 'black', 'folder.png') or self.default_icon_path()

    def is_icon_visible(self):
        """
        Returns whether or not the tree item icon is visible
        :return: bool
        """

        return self.treeWidget().icons_visible() and self._icon_visible

    def set_icon_visible(self, flag):
        """
        Sets whether or not tree item icon is visible
        :param flag: bool
        """

        self._icon_visible = flag

    def default_icon_color(self):
        """
        Returns the default icon color
        :return: str
        """

        palette = self.treeWidget().palette()
        default_color = palette.color(self.treeWidget().foregroundRole())
        default_color = color.Color.from_color(default_color).to_string()

        return str(default_color)

    def icon_color(self):
        """
        Returns the icon color
        :return: variant, QColor or None
        """

        return self._icon_color or self.default_icon_color()

    def set_icon_color(self, icon_color):
        """
        Sets the icon color
        :param icon_color: variant, QColor or str
        """

        if icon_color:
            if isinstance(icon_color, QColor):
                icon_color = color.Color.from_color(icon_color)
            elif python.is_string(icon_color):
                icon_color = color.Color.from_string(icon_color)
            self._icon_color = icon_color.to_string()
        else:
            self._icon_color = None

        self.update_icon()

    def update_icon(self):
        """
        Forces the icon to update
        """

        if not self.is_icon_visible():
            return

        if self.isExpanded():
            path = self.expanded_icon_path()
        else:
            path = self.collapsed_icon_path()
        item_pixmap = self._create_pixmap(path, self.icon_color())
        self.setIcon(0, item_pixmap)

    def update(self):
        """
        Updates current item
        """

        self.update_icon()

    def bold(self):
        """
        Returns whether item text is bold or not
        :return: bool
        """

        return self.font(0).bold()

    def set_bold(self, flag):
        """
        Sets whether item text is bold or not
        :param flag: bool
        """

        if flag:
            self._settings['bold'] = flag

        font = self.font(0)
        font.setBold(flag)
        self.setFont(0, font)

    def url(self):
        """
        Returns the url path
        :return: QUrl
        """

        return QUrl(self.path())

    def parents(self):
        """
        Returns all item parents
        :return: list(LibrarySidebarWidgetItem)
        """

        parents = list()
        parent = self.parent()
        if parent:
            parents.append(parent)
            while parent.parent():
                parent = parent.parent()
                parents.append(parent)

        return parents

    def set_expanded_parents(self, expanded):
        """
        Sets all the parents of the item to the value of expanded
        :param expanded: bool
        """

        parents = self.parents()
        for parent in parents:
            parent.setExpanded(expanded)

    def settings(self):
        """
        Returns the current state of the item as a dictionary
        :return: dict
        """

        settings = dict()

        is_selected = self.isSelected()
        if is_selected:
            settings['selected'] = is_selected
        is_expanded = self.isExpanded()
        if is_expanded:
            settings['expanded'] = is_expanded
        bold = self._settings.get('bold')
        if bold:
            settings['bold'] = bold
        text_color = self._settings.get('textColor')
        if text_color:
            settings['textColor'] = text_color

        return settings

    def set_settings(self, settings):
        """
        Sets the current state of the item from a dictionary
        :param settings: dict
        """

        text = settings.get('text')
        if text:
            self.setText(0, text)
        icon_path = settings.get('icon')
        if icon_path:
            self.set_icon_path(icon_path)
        icon_color = settings.get('color')
        if icon_color:
            self.set_icon_color(icon_color)
        is_selected = settings.get('selected')
        if is_selected is not None:
            self.setSelected(is_selected)
        is_expanded = settings.get('expanded')
        if is_expanded is not None and self.childCount() > 0:
            self.setExpanded(is_expanded)
            self.update_icon()
        bold = settings.get('bold')
        if bold is not None:
            self.set_bold(bold)
        text_color = settings.get('textColor')
        if text_color:
            self.setTextColor(text_color)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _create_pixmap(self, path, color):
        """
        Internal function that creates a new item pixmap from the given path
        :param path: str
        :param color: str or QColor
        :return: QPixmap
        """

        if not path:
            return QPixmap()

        dpi = self.treeWidget().dpi()
        key = path + color + 'DPI-' + str(dpi)
        item_pixmap = self._PIXMAP_CACHE.get(key)
        if not item_pixmap:
            width = 20 * dpi
            height = 18 * dpi
            if '/' not in path and '\\' not in path:
                path = resources.get('icons', path)
            if not path or not os.path.exists(path):
                path = self.default_icon_path()
            pixmap2 = pixmap.Pixmap(path)
            pixmap2.set_color(color)
            pixmap2 = pixmap2.scaled(16 * dpi, 16 * dpi, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (width - pixmap2.width()) / 2
            y = (height - pixmap2.height()) / 2
            item_pixmap = QPixmap(QSize(width, height))
            item_pixmap.fill(Qt.transparent)
            painter = QPainter(item_pixmap)
            painter.drawPixmap(x, y, pixmap2)
            painter.end()
            self._PIXMAP_CACHE[key] = item_pixmap

        return item_pixmap
