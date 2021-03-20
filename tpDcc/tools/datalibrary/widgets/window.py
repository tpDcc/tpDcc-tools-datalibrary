#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains data library window widget implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
import time
import copy
import logging
import operator
from functools import partial

from Qt.QtCore import Qt, Signal, QPoint
from Qt.QtWidgets import QSizePolicy, QWidget, QFrame, QSplitter, QFileDialog, QDialogButtonBox, QMenu, QAction
from Qt.QtGui import QCursor, QColor, QIcon, QKeyEvent, QStatusTipEvent

from tpDcc.managers import configs, resources
from tpDcc.libs.python import python, osplatform, fileio, folder, path as path_utils
from tpDcc.libs.resources.core import icon
from tpDcc.libs.qt.core import qtutils, base, animation, menu, decorators as qt_decorators
from tpDcc.libs.qt.widgets import layouts, stack, toolbar, messagebox
from tpDcc.libs.datalibrary.core import datalib

from tpDcc.tools.datalibrary.core import consts, utils, factory
from tpDcc.tools.datalibrary.core.views import item as items_view
from tpDcc.tools.datalibrary.widgets import viewer, search, sidebar, status
from tpDcc.tools.datalibrary.widgets.menus import filter, group, sort, libraries

logger = logging.getLogger(consts.TOOL_ID)


class PreviewFrame(QFrame):
    pass


class SidebarFrame(QFrame):
    pass


class LibraryWindow(base.BaseWidget):

    DEFAULT_NAME = consts.DEFAULT_LIBRARY_NAME

    DEFAULT_SETTINGS = {
        "library": {
            "sort_by": ["name:asc"],
            "group_by": ["type:asc"]
        },
        "paneSizes": [130, 280, 180],
        "trashFolderVisible": False,
        "sidebarWidgetVisible": True,
        "previewWidgetVisible": True,
        "toolBarWidgetVisible": True,
        "statusBarWidgetVisible": True,
        "recursiveSearchEnabled": True,
        "viewerWidget": {
            "spacing": 2,
            "padding": 6,
            "zoomAmount": 80,
            "textVisible": True,
        },
        "searchWidget": {
            "text": "",
        },
        "filterByMenu": {
            "Folder": False
        }
    }

    PROGRESS_BAR_VISIBLE = consts.PROGRESS_BAR_VISIBLE
    TRASH_ENABLED = True
    TEMP_PATH_MENU_ENABLED = False
    DPI_ENABLED = False

    LIBRARY_CLASS = datalib.DataLibrary
    VIEWER_CLASS = viewer.DataViewer
    SEARCH_WIDGET_CLASS = search.DataSearcherWidget
    STATUS_WIDGET_CLASS = status.DataStatusWidget
    TOOLBAR_WIDGET_CLASS = toolbar.ToolBar
    SIDEBAR_WIDGET_CLASS = sidebar.SidebarWidget
    SORTBY_MENU_CLASS = sort.SortByMenu
    GROUPBY_MENU_CLASS = group.GroupByMenu
    FILTERBY_MENU_CLASS = filter.FilterByMenu

    itemSelectionChanged = Signal(object)
    folderSelectionChanged = Signal(object)

    def __init__(
            self, settings, name='', items_factory=None,
            json_settings_file_path='', library_path='', client=None, parent=None):

        self._dpi = 1.0
        self._client = client
        self._settings = settings
        self._name = name or self.DEFAULT_NAME
        self._items = list()
        self._is_locked = False
        self._is_loaded = False
        self._library = None
        self._refresh_enabled = False
        self._trash_enabled = self.TRASH_ENABLED
        self._superusers = None
        self._lock_reg_exp = None
        self._unlock_reg_exp = None
        self._kwargs = dict()
        self._path = None
        self._menu_items = list()
        self._repository_type = None
        self._repository_path = ''

        self._preview_widget = None
        self._new_item_widget = None
        self._current_item = None
        self._items_factory = items_factory

        self._items_hidden_count = 0
        self._items_visible_count = 0

        self._is_trash_folder_visible = False
        self._sidebar_widget_visible = True
        self._preview_widget_visible = True
        self._status_widget_visible = True

        self._libraries_menu = None
        self._settings_file_path = json_settings_file_path or utils.settings_path()

        super(LibraryWindow, self).__init__(parent)

        # # TODO: THIS IS FOR DEV
        # library_path = r'D:\rigs\rigscript\chimp\data.db'
        self.set_library(library_path or self._settings.get('last_path'))

        self.set_dpi(1.0)

    # ============================================================================================================
    # PROPERTIES
    # ============================================================================================================

    @property
    def client(self):
        return None if not self._client else self._client

    @property
    def factory(self):
        return self._items_factory

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def get_main_layout(self):
        return layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))

    def ui(self):
        super(LibraryWindow, self).ui()

        self.setMinimumWidth(5)
        self.setMinimumHeight(5)

        self._stack = stack.SlidingStackedWidget()
        self.main_layout.addWidget(self._stack)

        self._sidebar_frame = SidebarFrame(self)
        sidebar_frame_lyt = layouts.VerticalLayout(margins=(0, 1, 0, 0))
        self._sidebar_frame.setLayout(sidebar_frame_lyt)

        self._new_item_frame = PreviewFrame(self)
        self._new_item_frame.setMinimumWidth(5)
        new_item_lyt = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        self._new_item_frame.setLayout(new_item_lyt)

        self._preview_frame = PreviewFrame(self)
        self._preview_frame.setMinimumWidth(5)
        preview_frame_lyt = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        self._preview_frame.setLayout(preview_frame_lyt)

        self._viewer = self.VIEWER_CLASS(self)
        self._viewer.installEventFilter(self)
        self._viewer.setContextMenuPolicy(Qt.CustomContextMenu)

        self._toolbar_widget = self.TOOLBAR_WIDGET_CLASS(self)
        self._search_widget = self.SEARCH_WIDGET_CLASS(self)
        self._sort_by_menu = self.SORTBY_MENU_CLASS(self)
        self._group_by_menu = self.GROUPBY_MENU_CLASS(self)
        self._filter_by_menu = self.FILTERBY_MENU_CLASS(self)
        self._status_widget = self.STATUS_WIDGET_CLASS(self)
        self._sidebar_widget = self.SIDEBAR_WIDGET_CLASS(self)
        self._sidebar_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        sidebar_frame_lyt.addWidget(self._sidebar_widget)

        self._splitter = QSplitter(Qt.Horizontal, self)
        self._splitter.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self._splitter.setHandleWidth(2)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self._sidebar_frame)
        self._splitter.addWidget(self._viewer)
        self._splitter.addWidget(self._preview_frame)
        self._splitter.setStretchFactor(0, False)
        self._splitter.setStretchFactor(1, True)
        self._splitter.setStretchFactor(2, False)

        base_widget = QWidget()
        base_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        base_widget.setLayout(base_layout)
        base_layout.addWidget(self._toolbar_widget)
        base_layout.addWidget(self._splitter)
        base_layout.addWidget(self._status_widget)

        self._stack.addWidget(base_widget)
        self._stack.addWidget(self._new_item_frame)

        self._setup_toolbar()

    def setup_signals(self):
        self.folderSelectionChanged.connect(self.update_lock)
        self._sidebar_widget.itemSelectionChanged.connect(self._on_folder_selection_changed)
        self._sidebar_widget.itemDropped.connect(self._on_item_dropped)
        self._sidebar_widget.customContextMenuRequested.connect(self._on_show_folders_menu)
        self._sidebar_widget.settingsMenuRequested.connect(self._on_sidebar_settings_menu_requested)
        self._viewer.itemSelectionChanged.connect(self._on_item_selection_changed)
        self._viewer.itemMoved.connect(self._on_item_moved)
        self._viewer.itemDropped.connect(self._on_item_dropped)
        self._viewer.keyPressed.connect(self._on_key_pressed)
        self._viewer.customContextMenuRequested.connect(self._on_show_items_context_menu)

    def event(self, event):
        """
        Overrides LibraryWindow event function
        """

        if isinstance(event, QKeyEvent):
            if qtutils.is_control_modifier() and event.key() == Qt.Key_F:
                self.search_widget().setFocus()
        elif isinstance(event, QStatusTipEvent):
            self.status_widget().show_info_message(event.tip())

        return super(LibraryWindow, self).event(event)

    def showEvent(self, event):
        """
        Overrides LibraryWindow showEvent function
        """

        super(LibraryWindow, self).showEvent(event)

        if not self.is_loaded():
            self._is_loaded = True
            self.load_settings()
            self.set_refresh_enabled(True)

    # ============================================================================================================
    # CLASS METHODS
    # ============================================================================================================

    @classmethod
    def create_action(cls, item_class, menu, library_window):
        """
        Returns the action to be displayed when the user clicks the "Add New Item" icon
        :param item_class: str
        :param menu: QMenu
        :param library_window: LibraryWindow
        :return: QAction
        """

        if not item_class.MENU_NAME:
            return

        show_save_widget = library_window.factory.get_show_save_widget_function(item_class)

        icon_name = os.path.splitext(item_class.MENU_ICON)[0] if item_class.MENU_ICON else None
        icon_name = icon_name or 'tpDcc'
        action_icon = resources.icon(icon_name) if icon_name else QIcon()
        if action_icon.isNull():
            action_icon = resources.icon('tpDcc')
        callback = partial(show_save_widget, item_class, library_window)
        action = QAction(action_icon, item_class.MENU_NAME, menu)
        action.triggered.connect(callback)
        menu.addAction(action)

        return action

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def name(self):
        """
        Returns library name
        :return: str
        """

        return self._name

    def library(self):
        """
        Returns data library being used
        :return: DataLibrary
        """

        return self._library

    def set_library(self, library):
        """
        Sets data library to use
        :param library: str or DataLibrary
        """

        if self._library and library and self._library == library:
            return

        if not library and self._library:
            try:
                qtutils.safe_disconnect_signal(self._library.dataChanged)
            except Exception as exc:
                pass

        if python.is_string(library):
            if not self._library or library != self._library.identifier:
                if not library:
                    logger.warning('Given library path "{}" does not exists!'.format(library))
                else:
                    if not os.path.isfile(library):
                        self._library = self.LIBRARY_CLASS.create(library)
                    else:
                        self._library = self.LIBRARY_CLASS.load(library)
                    self._library.add_scan_location(path_utils.clean_path(os.path.join(os.path.dirname(library))))
        else:
            self._library = library

        if self._library:
            plugin_locations = self._library.plugin_locations() or list()

            # Create factory to hold all available item views
            if not self._items_factory:
                self._items_factory = factory.ItemsFactory(paths=plugin_locations)

            self._path = path_utils.clean_path(os.path.dirname(self.database_path()))

            # This is very time consuming, we should avoid calling this
            self._library.sync()

            # Add some default queries
            self._library.add_query(
                {'name': 'invalid extensions', 'operator': 'and', 'filters': [('extension', 'not', '.pyc')]}
            )

            self._library.dataChanged.connect(self.refresh)

        self._sort_by_menu.set_library(self._library)
        self._group_by_menu.set_library(self._library)
        self._filter_by_menu.set_library(self._library)
        self._viewer.set_library(self._library)
        self._search_widget.set_library(self._library)
        self._sidebar_widget.set_library(self._library)

        self.set_refresh_enabled(True)
        self.update_view_button()
        self.update_filters_button()
        self.update_preview_widget()

    def database_path(self):
        """
        Returns path to the database showed by the window
        :return: str
        """

        if not self._library:
            return

        return self._library.identifier

    def path(self):
        """
        Returns the path being used by the library
        :return: str
        """

        return self._path

    def set_path(self, path):
        path = path_utils.clean_path(path)

        if path == self.path():
            return

        self._path = path

        if not self._library:
            self.set_library(self._path)

        if not os.path.exists(self.database_path()):
            self.sync()

        self.refresh()
        self.library().search()
        self.update_preview_widget()

    def is_loaded(self):
        """
        Returns whether or not Data library window has been loaded
        :return: bool
        """

        return self._is_loaded

    def is_refresh_enabled(self):
        """
        Returns whether refresh is enabled or not
        If not, all updates will be ignored
        :return: bool
        """

        return self._refresh_enabled

    def set_refresh_enabled(self, flag):
        """
        Whether widgets should be updated or not
        :param flag: bool
        """

        library = self.library()
        if not library:
            return

        library.set_search_enabled(flag)
        self._refresh_enabled = flag

    def is_recursive_search_enabled(self):
        """
        Returns whether recursive search is enabled or not
        :return: bool
        """

        return self.sidebar_widget().is_recursive()

    def set_recursive_search_enabled(self, flag):
        """
        Sets whether recursive search is enabled or not
        :param flag: bool
        """

        self.sidebar_widget().set_recursive(flag)

    def clean_library(self):
        """
        Cleans library data by removing files that are not being managed by database
        NOTE: This is a destructive operation
        :return:
        """

        if not self.library():
            return

        # TODO: This operation should only be available for superusers

        res = messagebox.MessageBox.question(
            self, 'Clean Library', 'This is a destructive operation. Files and folders not being managed by database '
                                   'will be removed. Is recommended to backup your data before proceeding with this '
                                   'operation. Are you sure you want to continue?')
        if res != QDialogButtonBox.Yes:
            return

        self.library().cleanup()

    def superusers(self):
        """
        Returns the superusers for the window
        :return: list(str)
        """

        return self._superusers

    def set_superusers(self, superusers):
        """
        Sets the valid superusres for the library widget
        This will lock all folders unless the current user is a superuser
        :param superusers: list(str)
        """

        self._superusers = superusers
        self.update_lock()

    def lock_reg_exp(self):
        """
        Returns the lock regular expression used for locking the widget
        :return: str
        """

        return self._lock_reg_exp

    def set_lock_reg_exp(self, reg_exp):
        """
        Sets the lock regular expression used for locking the widget
        Locks only folders that contain the given regular expression in their path
        :param reg_exp: str
        """

        self._lock_reg_exp = reg_exp
        self.update_lock()

    def unlock_reg_exp(self):
        """
        Returns the unlock regular expression used for unlocking the widget
        :return: str
        """

        return self._unlock_reg_exp

    def set_unlock_reg_exp(self, reg_exp):
        """
        Sets the unlock regular expression used for locking the widget
        Unlocks only folders that contain the given regular expression in their path
        :param reg_exp: str
        """

        self._unlock_reg_exp = reg_exp
        self.update_lock()

    def is_lock_reg_exp_enabled(self):
        """
        Returns whether the lock regular expression or unlock regular expression has been set
        :return: bool
        """

        return not (self.superusers() is None and self.lock_reg_exp() is None and self.unlock_reg_exp() is None)

    def refresh(self):
        """
        Refresh all necessary items
        """

        if self.is_refresh_enabled():
            self.update()

    def update(self):
        """
        Overrides base QMainWindow update function
        Update the library widget and the data
        """

        self.refresh_sidebar()
        self.update_window_title()

    def update_window_title(self):
        """
        Updates the window title
        """

        window_title = self.windowTitle()

        if self.is_locked():
            window_title += ' (Locked)'

        self.setWindowTitle(window_title)

    def update_filters_button(self):
        """
        Updates the icon for the filters menu
        """

        action = self.toolbar_widget().find_action('Filters')
        filter_icon = resources.icon('filter', theme='black')
        if filter_icon.isNull():
            return
        # icon.set_color(self.icon_color())
        filter_icon.set_color(QColor(255, 255, 255, 255))
        if self._filter_by_menu.is_active():
            filter_icon.set_badge(18, 1, 9, 9, color=consts.ICON_BADGE_COLOR)
        action.setIcon(filter_icon)

    def update_lock(self):
        """
        Updates the lock state for the library
        """

        if not self.is_lock_reg_exp_enabled():
            return

        superusers = self.superusers() or list()
        re_locked = re.compile(self.lock_reg_exp() or '')
        re_unlocked = re.compile(self.unlock_reg_exp() or '')

        if osplatform.get_user(lower=True) in superusers:
            self.set_locked(False)
        elif re_locked.match('') and re_unlocked.match(''):
            if superusers:
                self.set_locked(True)
            else:
                self.set_locked(False)
        else:
            # Lock/Unlock folders matching regex
            folders = self.selected_folder_paths()
            if not re_locked.match(''):
                for folder_found in folders:
                    if re_locked.search(folder_found):
                        self.set_locked(True)
                        return
                self.set_locked(False)
            if not re_unlocked.match(''):
                for folder_found in folders:
                    if re_unlocked.search(folder_found):
                        self.set_locked(False)
                        return

    @qt_decorators.show_wait_cursor
    def sync(self, force_start=True, force_search=True):
        """
        Sync any data that might be out of date with the model
        """

        def _sync():
            start_time = time.time()
            self.library().sync(progress_callback=self._set_progress_bar_value)
            elapsed_time = time.time() - start_time
            self.status_widget().show_info_message('Synced items in {0:.3f} seconds'.format(elapsed_time))
            self._set_progress_bar_value('Done')
            if force_start:
                progress_bar.close()
            else:
                animation.fade_out_widget(progress_bar, duration=500, on_finished=progress_bar.close)

            if force_search and self.library():
                # self.library().set_dirty(True)
                self.library().search()

        progress_bar = self.status_widget().progress_bar()
        self._set_progress_bar_value('Syncing')
        if self.PROGRESS_BAR_VISIBLE:
            progress_bar.show()

        if force_start:
            _sync()
        else:
            animation.fade_in_widget(progress_bar, duration=1, on_finished=_sync)

    def set_sizes(self, sizes):
        """
        :type sizes: (int, int, int)
        :rtype: None
        """
        first_size, second_size, third_size = sizes

        if third_size == 0:
            third_size = 200

        if first_size == 0:
            first_size = 120

        self._splitter.setSizes([first_size, second_size, third_size])
        self._splitter.setStretchFactor(1, 1)

    # ============================================================================================================
    # DPI
    # ============================================================================================================

    def is_dpi_enabled(self):
        """
        Returns whether or not DPI functionality is enabled
        :return: bool
        """

        dpi_enabled = self.DPI_ENABLED
        datalib_config = configs.get_library_config('tpDcc-tools-datalibrary')
        if datalib_config:
            dpi_enabled = datalib_config.get('dpi_enabled') or dpi_enabled

        return dpi_enabled

    def dpi(self):
        """
        Returns current library wiget DPI
        :return: float
        """

        if not self.is_dpi_enabled():
            return 1.0

        return float(self._dpi)

    def set_dpi(self, dpi):
        """
        Sets the current DPI for library widget
        :param dpi: float
        """

        if not self.is_dpi_enabled():
            dpi = 1.0

        self._dpi = dpi

        self.viewer().set_dpi(dpi)
        self.toolbar_widget().set_dpi(dpi)
        self.sidebar_widget().set_dpi(dpi)
        self.status_widget().setFixedHeight(20 * dpi)

        self._splitter.setHandleWidth(2 * dpi)

        self.show_toast_message('DPI: {}'.format(int(dpi * 100)))

        # self.reload_stylesheet()

    # ============================================================================================================
    # VERSION
    # ============================================================================================================

    def get_repository_type(self):
        if self._repository_type:
            return self._repository_type

        if not self._settings:
            return None

        return self._settings.get('version_control', default_value=0, setting_group='Version', begin_group='Repository')

    def set_repository_type(self, repository_type_index):
        try:
            repository_type_index = int(repository_type_index)
        except Exception:
            return
        self._repository_type = repository_type_index

    def get_repository_path(self):
        if not self._library:
            return None

        library_path = self._library.identifier
        if not os.path.isfile(library_path):
            return None

        return os.path.dirname(library_path)

    # ============================================================================================================
    # LOCK / UNLOCK
    # ============================================================================================================

    def is_locked(self):
        """
        Returns whether the library is locked or not
        :return: bool
        """

        return self._is_locked

    def set_locked(self, flag):
        """
        Sets the state of the library to be editable or not
        :param flag: bool
        """

        self._is_locked = flag

        self.sidebar_widget().set_locked(flag)
        self.viewer().set_locked(flag)
        self.update_create_item_button()
        self.update_window_title()
        self.lockChanged.emit(flag)

    def update_create_item_button(self):
        """
        Updates the create item icon depending of the lock status
        """

        action = self.toolbar_widget().find_action('New Item')
        if self.is_locked():
            icon = resources.icon('lock')
            action.setEnabled(False)
        else:
            icon = resources.icon('plus')
            action.setEnabled(True)
        # icon.set_color(self.icon_color())
        action.setIcon(icon)

    # ============================================================================================================
    # TOOLBAR WIDGET
    # ============================================================================================================

    def toolbar_widget(self):
        """
        Returns menu bar widget
        :return: toolbar.ToolBar
        """

        return self._toolbar_widget

    def add_toolbar_action(self, name, icon, tip, callback=None):
        """
        Internal function that adds a button/action into menu bar widget
        :param name: str
        :param icon: QIcon
        :param tip: str
        :param callback: fn
        :return: QAction
        """

        # We need to do this to avoid PySide2 errors
        def _callback():
            callback()

        action = self.toolbar_widget().addAction(name)
        if icon:
            action.setIcon(icon)
        if tip:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if callback:
            action.triggered.connect(_callback)

        return action

    def is_toolbar_widget_visible(self):
        """
        Returns whether toolbar widget is visible or not
        :return: bool
        """

        return self.toolbar_widget().is_expanded()

    def set_toolbar_widget_visible(self, flag):
        """
        Sets whether menubar widget is visible or not
        :param flag: bool
        """

        flag = bool(flag)
        if flag:
            self.toolbar_widget().expand()
        else:
            self.toolbar_widget().collapse()

    # ============================================================================================================
    # SEARCH WIDGET
    # ============================================================================================================

    def search_widget(self):
        """
        Returns search widget
        :return: LibrarySearchWidget
        """

        return self._search_widget

    def set_search_text(self, text):
        """
        Set the search widget text
        :param text: str
        """

        self.search_widget().setText(text)

    def items_visible_count(self):
        """
        Return the number of visible items
        :return: int
        """

        return self._items_visible_count

    def items_hidden_count(self):
        """
        Return the number of hidden items
        :return: int
        """

        return self._items_hidden_count

    # ============================================================================================================
    # SIDEBAR WIDGET
    # ============================================================================================================

    def sidebar_widget(self):
        """
        Return the sidebar widget
        :return: LibrarySidebarWidget
        """

        return self._sidebar_widget

    def is_sidebar_widget_visible(self):
        """
        Return whether SideBar widget is visible or not
        :return: bool
        """

        return self._sidebar_widget_visible

    def set_sidebar_widget_visible(self, flag):
        """
        Set whether SideBar widget is visible or not
        :param flag: bool
        """

        flag = bool(flag)
        self._sidebar_widget_visible = flag

        if flag:
            self._sidebar_frame.setVisible(True)
        else:
            self._sidebar_frame.setVisible(False)

        self.update_view_button()

    def set_folder_data(self, path, data):
        """
        Sets sidebar folder data
        :param path: str
        :param data: dict
        """

        self.sidebar_widget().set_item_data(path, data)

    @qt_decorators.show_wait_cursor
    def refresh_sidebar(self):
        """
        Refresh the state of the sidebar widget
        """

        path = self.path()
        if not path and self._allow_non_path:
            return
        else:
            if not path:
                return self.show_hello_dialog()
            elif not os.path.exists(path):
                return self.show_path_error_dialog()

            self.update_sidebar()

    def update_sidebar(self):
        """
        Update the folders to be shown in the folders widget
        """

        library = self.library()
        if not library:
            return

        current_data = dict()
        root = self.path()

        root_identifier = self.library().get_identifier(root)
        queries = [{'operator': 'and',
                    'filters': [('folder', 'is', 'True'), ('directory', 'startswith', root_identifier)]}]

        items = self.library().find_items(queries)
        for item in items:
            if not item:
                continue
            current_data[item.format_identifier()] = item.data()

        self.sidebar_widget().set_data(current_data, root=root)

    def selected_folder_path(self):
        """
        Return the selected folder items
        :return: str or None
        """

        return self.sidebar_widget().selected_path()

    def selected_folder_paths(self):
        """
        Return the selected folder items
        :return: list(str)
        """

        return self.sidebar_widget().selected_paths()

    def select_folder_path(self, path):
        """
        Select the given folder path
        :param path: str
        """

        self.select_folder_paths([path])

    def select_folder_paths(self, paths):
        """
        Select the given folder paths
        :param paths: list(str)
        """

        self.sidebar_widget().select_paths(paths)

    def create_folder_context_menu(self):
        """
        Returns the folder menu for the selected folders
        :return: QMenu
        """

        path = self.selected_folder_path()
        items = list()
        if path:
            queries = [{"filters": [("path", "is", path)]}]
            items = self.library().find_items(queries)
            if items:
                self._items = items

        return self._create_item_context_menu(items)

    # ============================================================================================================
    # VIEWER WIDGET
    # ============================================================================================================

    def viewer(self):
        """
        Returns muscle viewer widget
        :return:
        """

        return self._viewer

    def items(self):
        """
        Return all the loaded items
        :return: list(LibraryItem)
        """

        return self._items

    def selected_items(self):
        """
        Return selected items
        :return: list(LibraryItem)
        """

        return self.viewer().selected_items()

    # ============================================================================================================
    # STATUS WIDGET
    # ============================================================================================================

    def status_widget(self):
        """
        Returns the status widget
        :return: StatusWidget
        """

        return self._status_widget

    def is_status_widget_visible(self):
        """
        Return whether StatusWidget is visible or not
        :return: bool
        """

        return self._status_widget_visible

    def set_status_widget_visible(self, flag):
        """
        Set whether StatusWidget is visible or not
        :param flag: bool
        """

        flag = bool(flag)
        self._status_widget_visible = flag
        self.status_widget().setVisible(flag)

    # ============================================================================================================
    # PREVIEW WIDGET
    # ============================================================================================================

    def preview_widget(self):
        """
        Returns the current preview widget
        :return: QWidget
        """

        return self._preview_widget

    def set_preview_widget(self, widget):
        """
        Set the preview widget
        :param widget: QWidget
        """

        if self._preview_widget == widget:
            msg = 'Preview widget already contains widget {}'.format(widget)
            logger.debug(msg)
        else:
            self.close_preview_widget()
            self._preview_widget = widget
            if self._preview_widget:
                self._preview_frame.layout().addWidget(self._preview_widget)
                self._preview_widget.show()

    def is_preview_widget_visible(self):
        """
        Returns whether preview widget is visible or not
        :return: bool
        """

        return self._preview_widget_visible

    def set_preview_widget_visible(self, flag):
        """
        Set if the PreviewWidget should be showed or not
        :param flag: bool
        """

        flag = bool(flag)
        self._preview_widget_visible = flag

        if flag:
            self._preview_frame.setVisible(True)
        else:
            self._preview_frame.setVisible(False)

        self.update_view_button()

    def update_preview_widget(self):
        """
        Update the current preview widget
        """

        self.set_preview_widget_from_item(self._current_item, force=True)

    def set_preview_widget_from_item(self, item, force=True):
        """
        Set the preview widget from the given item
        :param item: LibvraryItem
        :param force: bool
        """

        if not force and self._current_item == item:
            logger.debug('The current item preview widget is already set!')
            return

        self._current_item = item

        if item:
            self.close_preview_widget()
            try:
                item.show_preview_widget(self)
            except Exception as e:
                self.show_error_message(e)
                self.clear_preview_widget()
                raise
        else:
            self.clear_preview_widget()

    def clear_preview_widget(self):
        """
        Set the default preview widget
        """

        self._preview_widget = None
        widget = base.PlaceholderWidget()
        self.set_preview_widget(widget)

    def close_preview_widget(self):
        """
        Close and delete the preview widget
        """

        frame_layout = self._preview_frame.layout()

        while frame_layout.count():
            item = frame_layout.takeAt(0)
            item.widget().hide()
            item.widget().close()
            item.widget().deleteLater()

        self._preview_widget = None

    def set_save_widget(self, create_widget):
        """
        Set the widget that should be showed when saving a new item
        :param create_widget: QWidget
        """

        if not create_widget:
            return

        self.set_new_item_widget_visible(True)

        self.set_new_item_widget(create_widget)
        create_widget.cancelled.connect(partial(self._stack.slide_in_index, 0))
        create_widget.saved.connect(partial(self._stack.slide_in_index, 0))

    def set_export_widget(self, export_widget):
        """
        Sets the widget that should be showed when exporting a new item
        :param export_widget: QWidget
        """

        if not export_widget:
            return

        self.set_new_item_widget_visible(True)

        self.set_new_item_widget(export_widget)
        export_widget.cancelled.connect(partial(self._stack.slide_in_index, 0))
        export_widget.saved.connect(partial(self._stack.slide_in_index, 0))

    # ============================================================================================================
    # NEW ITEM WIDGET
    # ============================================================================================================

    def new_item_widget(self):
        """
        Returns the current new item widget
        :return: QWidget
        """

        return self._new_item_widget

    def set_new_item_widget(self, widget):
        """
        Sets the new item widget
        :param widget: QWidget
        """

        if self._new_item_widget == widget:
            msg = 'New Item widget already contains widget {}'.format(widget)
            logger.debug(msg)
        else:
            self.close_new_item_widget()
            self._new_item_widget = widget
            if self._new_item_widget:
                self._new_item_frame.layout().addWidget(self._new_item_widget)
                self._new_item_widget.show()

    def is_new_item_widget_visible(self):
        """
        Returns whether new item widget is visible or not
        :return: bool
        """

        return self._new_item_widget_visible

    def set_new_item_widget_visible(self, flag):
        """
        Set if the New Item widget should be showed or not
        :param flag: bool
        """

        flag = bool(flag)
        self._new_item_widget_visible = flag

        if flag:
            self._stack.slide_in_index(1)
            self._new_item_frame.show()
        else:
            self._stack.slide_in_index(0)
            self._new_item_frame.hide()

        self.update_view_button()

    def clear_new_item_widget(self):
        """
        Set the default new item widget
        """

        self._new_item_widget = None
        widget = base.PlaceholderWidget()
        self.set_new_item_widget(widget)

    def close_new_item_widget(self):
        """
        Close and delete the new item widget
        """

        lyt = self._new_item_frame.layout()

        while lyt.count():
            item = lyt.takeAt(0)
            item.widget().hide()
            item.widget().close()
            item.widget().deleteLater()

        self._new_item_widget = None

    # ============================================================================================================
    # TRASH FOLDER
    # ============================================================================================================

    def trash_enabled(self):
        """
        Returns True if moving items to trash
        :return: bool
        """

        return self._trash_enabled

    def set_trash_enabled(self, flag):
        """
        Sets if items can be trashed or not
        :param flag: bool
        """

        self._trash_enabled = flag

    def is_path_in_trash(self, path):
        """
        Returns whether given path is in trash or not
        :param path: str
        :return: bool
        """

        return consts.TRASH_NAME in path.lower()

    def trash_path(self):
        """
        Returns the trash path for the library
        :return: str
        """

        path = self.path()
        return '{}/{}'.format(path, consts.TRASH_NAME.title())

    def trash_folder_exists(self):
        """
        Returns whether trash folder exists or not
        :return: bool
        """

        return os.path.exists(self.trash_path())

    def create_trash_folder(self):
        """
        Create the trash folder if it does not already exists
        """

        trash_path = self.trash_path()
        if not os.path.exists(trash_path):
            os.makedirs(trash_path)

    def is_trash_folder_visible(self):
        """
        Return whether trash folder is visible or not
        :return: bool
        """

        return self._is_trash_folder_visible

    def set_trash_folder_visible(self, flag):
        """
        Set whether trash folder is visible or not
        :param flag: bool
        """

        self._is_trash_folder_visible = flag

        if flag:
            query = {
                'name': 'trash_query',
                'filters': list()
            }
        else:
            query = {
                'name': 'trash_query',
                'filters': [('path', 'not_contains', consts.TRASH_NAME.title())]
            }

        # self.library().add_global_query(query)
        # self.update_sidebar()
        # self.library().search()

    def is_trash_selected(self):
        """
        Return whether the selected folders are in the trash or not
        :return: bool
        """

        folders = self.selected_folder_paths()
        for folder in folders:
            if self.is_path_in_trash(folder):
                return True

        items = self.selected_items()
        for item in items:
            if self.is_path_in_trash(item.path()):
                return True

        return False

    def move_items_to_trash(self, items):
        """
        Move the given items to trash path
        :param items: list(LibraryItem)
        """

        self.create_trash_folder()
        self.move_items(items, target_folder=self.trash_path(), force=True)

    def show_move_items_to_trash_dialog(self, items=None):
        """
        Show the "Move to Trash" dialog for the selected items
        :param items: list(LibraryItem) or None
        """

        items = items or self.selected_items()
        if items:
            title = 'Move to Trash?'
            text = 'Are you sure you want to move the selected item/s to the trash?'
            result = self.show_question_dialog(title, text)
            if result == QDialogButtonBox.Yes:
                self.move_items_to_trash(items)

    # ============================================================================================================
    # TOAST/MESSAGES
    # ============================================================================================================

    def show_toast_message(self, text, duration=1000):
        """
        Shows toast widget with the given text and duration
        :param text: str
        :param duration:int
        """

        self.viewer().show_toast_message(text, duration)

    def show_success_message(self, text, msecs=None):
        """
        Shows success message to the user
        :param text: str
        :param msecs: int or None
        """

        self.status_widget().show_ok_message(text, msecs)

    def show_info_message(self, text, msecs=None):
        """
        Shows info message to the user
        :param text: str
        :param msecs: int or None
        """

        self.status_widget().show_info_message(text, msecs)

    def show_warning_message(self, text, msecs=None):
        """
        Shows warning message to the user
        :param text: str
        :param msecs: int or None
        """

        self.status_widget().show_warning_message(text, msecs)
        self.set_status_widget_visible(True)

    def show_error_message(self, text, msecs=None):
        """
        Shows error message to the user
        :param text:str
        :param msecs: int or None
        """

        self.status_widget().show_error_message(text, msecs)
        self.set_status_widget_visible(True)

    def show_refresh_message(self):
        """
        Show long the current refresh took
        """

        item_count = len(self.library().results())
        elapsed_time = self.library().search_time()

        plural = ''
        if item_count > 1:
            plural = 's'

        msg = 'Found {0} item{1} in {2:.3f} seconds.'.format(item_count, plural, elapsed_time)
        self.status_widget().show_info_message(msg)

        logger.debug(msg)

    @qt_decorators.show_arrow_cursor
    def show_hello_dialog(self):
        """
        This function is called when there is not root path set for the library
        """

        text = 'Please choose a folder location for storing the data'
        dialog = messagebox.create_message_box(
            None, 'Welcome {}'.format(self.name()), text, header_pixmap=self._library_icon_path)
        dialog.accepted.connect(self.show_change_path_dialog)
        dialog.show()

    @qt_decorators.show_arrow_cursor
    def show_path_error_dialog(self):
        """
        This function is called when the root path does not exists during refresh
        """

        path = self.path()
        text = 'The current root path does not exists "{}". Please select a new root path to continue.'.format(path)
        dialog = messagebox.create_message_box(self, 'Path Error', text)
        dialog.show()
        dialog.accepted.connect(self.show_change_path_dialog)

    def show_change_path_dialog(self):
        """
        Shows a file browser dialog for changing the root path
        :return: str
        """

        path = self._show_change_path_dialog()
        if path:
            self.set_path(path)
        else:
            self.refresh()

    def show_info_dialog(self, title, text):
        """
        Function that shows an information dialog to the user
        :param title: str
        :param text: str
        :return: QDialogButtonBox.StandardButton
        """

        buttons = QDialogButtonBox.Ok
        return messagebox.MessageBox.question(self, title, text, buttons=buttons)

    def show_question_dialog(self, title, text, buttons=None):
        """
        Function that shows a question dialog to the user
        :param title: str
        :param text: str
        :param buttons: list(QDialogButtonBox.StandardButton)
        :return: QDialogButtonBox.StandardButton
        """

        buttons = buttons or QDialogButtonBox.Yes | QDialogButtonBox.No | QDialogButtonBox.Cancel
        return messagebox.MessageBox.question(self, title, text, buttons=buttons)

    def show_error_dialog(self, title, text):
        """
        Function that shows an error dialog to the user
        :param title: str
        :param text: str
        :return: QDialogButtonBox.StandardButton
        """

        self.show_error_message(text)
        return messagebox.MessageBox.critical(self, title, text)

    def show_exception_dialog(self, title, text):
        """
        Function that shows an exception dialog to the user
        :param title: str
        :param text: str
        :return: QDialogButtonBox.StandardButton
        """

        logger.exception(text)
        self.show_error_dialog(title, text)

    # ============================================================================================================
    # OTHERS
    # ============================================================================================================

    def is_compact_view(self):
        """
        Returns whether the folder and preview widget are hidden
        :return: bool
        """

        return not self.is_sidebar_widget_visible() and not self.is_preview_widget_visible()

    def toggle_view(self):
        """
        Toggles the preview widget and folder widget visibility
        """

        compact = self.is_compact_view()
        if qtutils.is_control_modifier():
            compact = False
            self.set_toolbar_widget_visible(compact)

        self.set_preview_widget_visible(compact)
        self.set_sidebar_widget_visible(compact)

    def update_view_button(self):
        """
        Updates the icon for the view action
        """

        compact = self.is_compact_view()
        action = self.toolbar_widget().find_action('View')
        if not compact:
            new_icon = resources.icon('view_all', theme='black')
        else:
            new_icon = resources.icon('view_compact', theme='black')
        # new_icon.set_color(self.icon_color())
        if new_icon.isNull():
            return
        new_icon.set_color(QColor(255, 255, 255, 255))
        action.setIcon(new_icon)

    # ============================================================================================================
    # SETTINGS
    # ============================================================================================================

    def settings_file_path(self):
        """
        Returns custom settings file path
        :return: str
        """

        return self._settings_file_path

    def set_settings_file_path(self, file_path):
        """
        Sets settings file path used by the library
        :param file_path: str
        """

        self._settings_file_path = file_path

        self._libraries_menu.set_settings_path(self._settings_file_path)

    def settings(self):
        """
        Return a dictionary with the widget settings
        :return: dict
        """

        settings = dict()

        settings['dpi'] = self.dpi()
        settings['kwargs'] = self._kwargs
        settings['library'] = self.library().settings()
        settings['paneSizes'] = self._splitter.sizes()
        settings['trashFolderVisible'] = self.is_trash_folder_visible()
        settings['sidebarWidgetVisible'] = self.is_sidebar_widget_visible()
        settings['previewWidgetVisible'] = self.is_preview_widget_visible()
        settings['toolBarWidgetVisible'] = self.is_toolbar_widget_visible()
        settings['statusBarWidgetVisible'] = self.is_status_widget_visible()
        settings['viewerWidget'] = self.viewer().settings()
        settings['searchWidget'] = self.search_widget().settings()
        settings['sidebarWidget'] = self.sidebar_widget().settings()
        settings['recursiveSearchEnabled'] = self.is_recursive_search_enabled()
        settings['filterByMenu'] = self._filter_by_menu.settings()
        settings['path'] = self.path()

        return settings

    def set_settings(self, settings_dict):
        """
        Sets the widget settings from the given dictionary
        :param settings_dict: dict
        """

        defaults = copy.deepcopy(self.DEFAULT_SETTINGS)
        settings = utils.update(defaults, settings_dict)

        is_refresh_enabled = self.is_refresh_enabled()

        try:
            self.set_refresh_enabled(False)
            self.viewer().set_toast_enabled(False)

            if not self.path():
                path = settings.get('path')
                if path and os.path.exists(path):
                    self.set_path(path)

            dpi = settings.get('dpi', 1.0)
            self.set_dpi(dpi)

            value = settings.get('library')
            if value is not None and self.library():
                self.library().update_settings(value)

            sizes = settings.get('paneSizes')
            if sizes and len(sizes) == 3:
                self.set_sizes(sizes)

            value = settings.get("sidebarWidgetVisible")
            if value is not None:
                self.set_sidebar_widget_visible(value)

            value = settings.get("toolBarWidgetVisible")
            if value is not None:
                self.set_toolbar_widget_visible(value)

            value = settings.get("previewWidgetVisible")
            if value is not None:
                self.set_preview_widget_visible(value)

            value = settings.get("statusBarWidgetVisible")
            if value is not None:
                self.set_status_widget_visible(value)

            value = settings.get('searchWidget')
            if value is not None:
                self.search_widget().set_settings(value)

            value = settings.get("recursiveSearchEnabled")
            if value is not None:
                self.set_recursive_search_enabled(value)

            value = settings.get('filterByMenu')
            if value is not None:
                self._filter_by_menu.set_settings(value)

        finally:
            self.set_refresh_enabled(is_refresh_enabled)
            self.refresh()

        value = settings.get('trashFolderVisible')
        if value is not None:
            self.set_trash_folder_visible(value)

        value = settings.get('sidebarWidget', {})
        self.sidebar_widget().set_settings(value)

        value = settings.get('viewerWidget', {})
        self.viewer().set_settings(value)

        self.update_filters_button()

    @qt_decorators.show_wait_cursor
    def load_settings(self):
        """
        Loads the user settings from disk
        """

        settings = self.read_settings()
        self.set_settings(settings)

    def read_settings(self):
        """
        Reads settings from disk
        :return: dict
        """

        key = self.name()
        data = utils.read_settings(self._settings_file_path)

        return data.get(key, dict())

    def save_settings(self, settings_dict=None):
        """
        Save the settings to the settings path
        :param settings_dict: dict
        """

        settings = utils.read_settings(self._settings_file_path)
        settings.setdefault(self.name(), dict())
        settings[self.name()].update(settings_dict or self.settings())
        utils.save_settings(settings)

        self.show_toast_message('Saved')

    def update_settings(self, settings):
        """
        Saves settings in the settings file on disk
        """

        data = self.read_settings()
        data.update(settings)
        self.save_settings(data)

    def reset_settings(self):
        """
        Reset the settings to the default ones
        """

        self.set_settings(self.DEFAULT_SETTINGS)

    def open_settings(self):
        """
        Opens current library settings file in explorer
        """

        path = self._settings_file_path or utils.settings_path()
        if not path or not os.path.isfile(path):
            return

        fileio.open_browser(path)

    def open_temp_path(self):
        """
        Opens library temporal directory in explorer
        """

        temp_path = utils.temp_path()
        folder.open_folder(temp_path)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _setup_toolbar(self):
        self.add_toolbar_action(
            'New Item', resources.icon('plus'), 'Add a new item to the selected folder',
            callback=self._on_show_new_menu)

        self._toolbar_widget.addWidget(self._search_widget)

        self.add_toolbar_action(
            'Filters', resources.icon('filter'),
            'Filter the current results by type.\nCtrl + Click will hide the others and show the selected one.',
            callback=self._on_show_filter_by_menu)

        self.add_toolbar_action(
            'Item View', resources.icon('slider'), 'Change the style of the item view',
            callback=self._on_show_item_view_menu)

        self.add_toolbar_action(
            'Group By', resources.icon('grid_view'), 'Group the current items in the view by column',
            callback=self._on_show_group_by_menu)

        self.add_toolbar_action(
            'Sort By', resources.icon('descending_sorting'), 'Group the current items in the view by column',
            callback=self._on_show_sort_by_menu)

        self.add_toolbar_action(
            'View', resources.icon('add'),
            'Choose to show/hide both the preview and navigation pane\nCtrl + click will hide the menu bar as well.',
            callback=self._on_toggle_view)

        self.add_toolbar_action(
            'Sync Items', resources.icon('sync'), 'Sync with the filesystem', callback=self._on_sync)

        self.add_toolbar_action(
            'Settings', resources.icon('settings'), 'Settings menu', callback=self._on_show_settings_menu)

    def _create_new_item_menu(self):
        """
        Internal function that creates a new item menu for adding new items
        :return: QMenu
        """

        item_icon = resources.icon('add')
        menu = QMenu(self)
        menu.setIcon(item_icon)
        menu.setTitle('New')

        library = self.library()
        if not library:
            return

        all_sorted_data = sorted(list(library.get_all_data_plugins()), key=operator.attrgetter('PRIORITY'))

        for data_item_class in all_sorted_data:
            action = self.create_action(data_item_class, menu, self)
            if action:
                action_icon = icon.Icon(action.icon())
                # action_icon.set_color(self.icon_color())
                action.setIcon(action_icon)
                menu.addAction(action)

        return menu

    def _set_progress_bar_value(self, label, value=-1):
        """
        Internal function that sets the progress bar label and value
        :param label: str
        :param value: int
        """

        progress_bar = self.status_widget().progress_bar()
        if value == -1:
            value = 100

        progress_bar.set_value(value)
        progress_bar.set_text(label)

    def _create_item_context_menu(self, items):
        """
        Internal function that returns the item context menu for the given items
        :param items: list(LibraryItem)
        :return:
        """

        self._menu_items = list()

        context_menu = QMenu(self)

        item_view = None
        if items:
            item_data = items[-1]
            if isinstance(item_data, items_view.ItemView):
                item_view = item_data
            else:
                view_class = self._items_factory.get_view(item_data)
                if view_class:
                    item_view = view_class(item_data, library_window=self)
            if item_view:
                item_view.context_menu(context_menu)

                # NOTE: We do thos to avoid Python to garbage collect the item views. Otherwise menu functionality
                # NOTE: related with item views will not work
                self._menu_items.append(item_view)

        if not self.is_locked():
            context_menu.addMenu(self._create_new_item_menu())
            if item_view:
                edit_icon = resources.icon('edit')
                edit_menu = QMenu(self)
                edit_menu.setTitle('Edit')
                edit_menu.setIcon(edit_icon)
                context_menu.addMenu(edit_menu)
                item_view.context_edit_menu(edit_menu)
                if self.trash_enabled():
                    edit_menu.addSeparator()
                    callback = partial(self.show_move_items_to_trash_dialog, items)
                    action = QAction(resources.icon('trash'), 'Move to Trash', edit_menu)
                    action.setEnabled(not self.is_trash_selected())
                    action.triggered.connect(callback)
                    edit_menu.addAction(action)

        context_menu.addSeparator()
        context_menu.addMenu(self._create_settings_menu())

        return context_menu

    def _create_settings_menu(self):
        """
        Returns the settings menu for changing the library widget
        :return: QMenu
        """

        settings_icon = resources.icon('settings')
        context_menu = menu.Menu('', self)
        context_menu.setTitle('Settings')
        context_menu.setIcon(settings_icon)

        settings_action = context_menu.addAction(settings_icon, 'Settings')
        settings_action.triggered.connect(self._on_show_settings_dialog)

        sync_action = context_menu.addAction(resources.icon('sync'), 'Sync')
        sync_action.triggered.connect(self._on_sync)

        context_menu.addSeparator()

        self._libraries_menu = libraries.LibrariesMenu(self._settings_file_path, library_window=self)
        context_menu.addMenu(self._libraries_menu)

        context_menu.addSeparator()

        # if consts.DPI_ENABLED:
        #     dpi_action = action.SliderAction('Dpi', context_menu)
        #     dpi = self.dpi() * 100.0
        #     dpi_action.slider().setRange(consts.DPI_MIN_VALUE, consts.DPI_MAX_VALUE)
        #     dpi_action.slider().setValue(dpi)
        #     dpi_action.valueChanged.connect(self._on_dpi_slider_changed)
        #     context_menu.addAction(dpi_action)
        #     context_menu.addSeparator()

        show_menu_action = QAction('Show Menu', context_menu)
        show_menu_action.setCheckable(True)
        show_menu_action.setChecked(self.is_toolbar_widget_visible())
        show_menu_action.triggered[bool].connect(self.set_toolbar_widget_visible)
        context_menu.addAction(show_menu_action)

        show_sidebar_action = QAction('Show Sidebar', context_menu)
        show_sidebar_action.setCheckable(True)
        show_sidebar_action.setChecked(self.is_sidebar_widget_visible())
        show_sidebar_action.triggered[bool].connect(self.set_sidebar_widget_visible)
        context_menu.addAction(show_sidebar_action)

        show_preview_action = QAction('Show Preview', context_menu)
        show_preview_action.setCheckable(True)
        show_preview_action.setChecked(self.is_preview_widget_visible())
        show_preview_action.triggered[bool].connect(self.set_preview_widget_visible)
        context_menu.addAction(show_preview_action)

        show_status_action = QAction('Show Status', context_menu)
        show_status_action.setCheckable(True)
        show_status_action.setChecked(self.is_status_widget_visible())
        show_status_action.triggered[bool].connect(self.set_status_widget_visible)
        context_menu.addAction(show_status_action)

        context_menu.addSeparator()

        save_settings_action = QAction(resources.icon('save'), 'Save Settings', context_menu)
        save_settings_action.triggered.connect(self.save_settings)
        context_menu.addAction(save_settings_action)

        reset_settings_action = QAction(resources.icon('reset'), 'Reset Settings', context_menu)
        reset_settings_action.triggered.connect(self.reset_settings)
        context_menu.addAction(reset_settings_action)

        open_settings_action = QAction(resources.icon('open'), 'Open Settings', context_menu)
        open_settings_action.triggered.connect(self.open_settings)
        context_menu.addAction(open_settings_action)

        if self.TEMP_PATH_MENU_ENABLED:
            temp_path_action = QAction(resources.icon('open'), 'Open Temp Path', context_menu)
            temp_path_action.triggered.connect(self.open_temp_path)
            context_menu.addAction(temp_path_action)

        context_menu.addSeparator()

        if self.trash_enabled():
            show_trash_action = QAction(resources.icon('trash'), 'Show Trash Folder', context_menu)
            show_trash_action.setEnabled(self.trash_folder_exists())
            show_trash_action.setCheckable(True)
            show_trash_action.setChecked(self.is_trash_folder_visible())
            show_trash_action.triggered[bool].connect(self.set_trash_folder_visible)
            context_menu.addAction(show_trash_action)

        context_menu.addSeparator()

        recursive_search_action = QAction(resources.icon('repeat'), 'Enable Recursive Search', context_menu)
        recursive_search_action.setCheckable(True)
        recursive_search_action.setChecked(self.is_recursive_search_enabled())
        recursive_search_action.triggered[bool].connect(self.set_recursive_search_enabled)
        context_menu.addAction(recursive_search_action)

        context_menu.addSeparator()

        cleanup_library_action = QAction(resources.icon('clean'), 'Clean Library', context_menu)
        cleanup_library_action.triggered[bool].connect(self.clean_library)
        context_menu.addAction(cleanup_library_action)

        context_menu.addSeparator()

        view_menu = self.viewer().create_settings_menu()
        context_menu.addMenu(view_menu)

        return context_menu

    @qt_decorators.show_arrow_cursor
    def _show_change_path_dialog(self):
        """
        Internal function that opens a file dialog for setting a new root path
        :return: str
        """

        path = self.path()
        if not path:
            path = os.path.expanduser('~')

        path = QFileDialog.getExistingDirectory(None, 'Choose a root folder location', path)
        if not path:
            return

        data_path = path_utils.join_path(path, 'data.db')

        return path_utils.clean_path(data_path)

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_show_new_menu(self):
        """
        Internal callback function that is called when user right clicks on an item
        Shows items contextual menu
        :return: QMenu
        """

        new_menu = self._create_new_item_menu()
        if not new_menu:
            return
        point = self.toolbar_widget().mapToGlobal(self.toolbar_widget().rect().bottomLeft())
        new_menu.show()

        return new_menu.exec_(point)

    def _on_show_filter_by_menu(self):
        """
        Internal callback function called when the user clicks on the filter action
        """

        widget = self.toolbar_widget().find_tool_button('Filters')
        point = widget.mapToGlobal(QPoint(0, widget.height()))
        self._filter_by_menu.show(point)
        self.update_filters_button()

    def _on_show_item_view_menu(self):
        """
        Internal callback function when triggered when the user clicks on item view action
        """

        menu = self.viewer().create_settings_menu()
        item_view_widget = self.toolbar_widget().find_tool_button('Item View')
        point = item_view_widget.mapToGlobal(QPoint(0, item_view_widget.height()))
        menu.exec_(point)

    def _on_show_group_by_menu(self):
        """
        Internal callback function called when the user presses group by action
        """

        widget = self.toolbar_widget().find_tool_button('Group By')
        point = widget.mapToGlobal(QPoint(0, widget.height()))
        self._group_by_menu.show(point)

    def _on_show_sort_by_menu(self):
        """
        Internal callback function called when the user presses Sort by action
        """

        widget = self.toolbar_widget().find_tool_button('Sort By')
        point = widget.mapToGlobal(QPoint(0, widget.height()))
        self._sort_by_menu.show(point)

    def _on_toggle_view(self):
        """
        Internal callback function called whe the user press view action
        """

        self.toggle_view()

    def _on_show_settings_menu(self):
        """
        Internal callback function triggered when the user show settings
        Show the settings menu at the current cursor position
        :return: QAction
        """

        settings_menu = self._create_settings_menu()
        point = self.toolbar_widget().rect().bottomRight()
        point = self.toolbar_widget().mapToGlobal(point)
        if osplatform.is_linux():
            settings_menu.move(-1000, -1000)
        settings_menu.show()
        point.setX(point.x() - settings_menu.width())

        return settings_menu.exec_(point)

    def _on_sync(self):
        """
        Internal callback function that is executed when the user selects the Sync
        context menu action
        """

        self.sync(force_search=True)

    def _on_show_settings_dialog(self):
        # TODO: Open settings dialog
        # If there is an attacher, we use attacher settings view, if not we create it
        pass

    def _on_folder_selection_changed(self):
        """
        Internal callback triggered when a folder is selected or deselect from sidebar widget
        """

        item_path = self.selected_folder_path()
        # self.library().search()
        self.folderSelectionChanged.emit(item_path)
        # self.globalSignal.folderSelectionChanged.emit(self, item_path)

    def _on_item_dropped(self, event):
        """
        Internal callback function that is triggered when items are dropped on the viewer or sidebar widget
        :param event: QEvent
        """

        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            path = self.selected_folder_path()
            items = self.create_items_from_urls(urls)
            if self.is_move_items_enabled():
                self.show_move_items_dialog(items, target_folder=path)
            elif not self.is_custom_order_enabled():
                self.show_info_message('Please use sort by "Custom Order" to reorder items!')

    def _on_show_folders_menu(self):
        """
        Internal callback function that is called when sidebar context menu is requested
        :return: QAction
        """

        folders_menu = self.create_folder_context_menu()
        point = QCursor.pos()
        point.setX(point.x() + 3)
        point.setY(point.y() + 3)
        action = folders_menu.exec_(point)
        folders_menu.close()

        return action

    def _test(self):
        print('hello')

    def _on_sidebar_settings_menu_requested(self, settings_menu):
        """
        Internal callback function triggered when sidebar settings menu is requested to show
        :param settings_menu: Menu
        """

        change_path_action = QAction(resources.icon('change'), 'Change Path', settings_menu)
        change_path_action.triggered.connect(self.show_change_path_dialog)
        settings_menu.addAction(change_path_action)
        settings_menu.addSeparator()

    def _on_item_selection_changed(self):
        """
        Internal callback function that is triggered when an item is selected or deselected
        """

        item = self.viewer().selected_item()

        self.set_preview_widget_from_item(item)
        self.itemSelectionChanged.emit(item)

    def _on_key_pressed(self, event):
        """
        Internal callback function that is triggered when a key is pressed on viewer widget
        :param event: QKeyEvent
        """

        text = event.text().strip()

        if not text.isalpha() and not text.isdigit():
            return

        if text and not self.search_widget().hasFocus():
            self.search_widget().setFocus()
            self.search_widget().setText(text)

    def _on_item_moved(self, item):
        """
        Internal callback function that is triggered when the custom order has changed
        :param item, LibraryItem
        """

        self.save_custom_order()

    def _on_item_dropped(self, event):
        """
        Internal callback function that is triggered when items are dropped on the viewer or sidebar widget
        :param event: QEvent
        """

        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            path = self.selected_folder_path()
            items = self.create_items_from_urls(urls)
            if self.is_move_items_enabled():
                self.show_move_items_dialog(items, target_folder=path)
            elif not self.is_custom_order_enabled():
                self.show_info_message('Please use sort by "Custom Order" to reorder items!')

    def _on_show_items_context_menu(self):
        """
        Internal callback function that is called when user right clicks on muscle viewer
        Shows the item context menu at the current cursor position
        :param pos, QPoint
        :return: QAction
        """

        item_views = self.viewer().selected_items()
        menu = self._create_item_context_menu(item_views)
        point = QCursor.pos()
        point.setX(point.x() + 3)
        point.setY(point.y() + 3)
        action = menu.exec_(point)

        return action
