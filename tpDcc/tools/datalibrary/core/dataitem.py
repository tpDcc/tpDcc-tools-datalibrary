#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library data item widget implementation
"""

from __future__ import print_function, division, absolute_import

import os
import logging
import traceback
from functools import partial

from Qt.QtCore import Qt, Signal, QObject, QUrl
from Qt.QtWidgets import QApplication, QAction, QDialogButtonBox, QFileDialog, QMessageBox
from Qt.QtGui import QIcon

from tpDcc.managers import resources, configs
from tpDcc.libs.python import path as path_utils
from tpDcc.libs.qt.widgets import messagebox

from tpDcc.libs.datalibrary.core import dataitem, utils, exceptions
from tpDcc.tools.datalibrary.core import consts

LOGGER = logging.getLogger('tpDcc-tools-datalibrary')


class LibraryDataItemSignals(QObject, object):
    """
    Class that contains definition for LibraryItem signals
    """

    saved = Signal(object)
    saving = Signal(object)
    loaded = Signal(object)
    copied = Signal(object, object, object)
    deleted = Signal(object)
    renamed = Signal(object, object, object)
    dataChanged = Signal(object)


class LibraryDataItem(dataitem.DataItem):

    MENU_NAME = ''
    MENU_ICON_NAME = consts.ITEM_DEFAULT_MENU_ICON
    MENU_ORDER = consts.ITEM_DEFAULT_MENU_ORDER
    SYNC_ORDER = 10

    EXTENSION = consts.ITEM_DEFAULT_EXTENSION
    EXTENSIONS = list()

    ENABLE_DELETE = False
    ENABLE_NESTED_ITEMS = False

    SAVE_WIDGET_CLASS = None
    LOAD_WIDGET_CLASS = None

    DEFAULT_THUMBNAIL_NAME = 'thumbnail.png'

    _libraryItemSignals = LibraryDataItemSignals()
    saved = _libraryItemSignals.saved
    saving = _libraryItemSignals.saving
    loaded = _libraryItemSignals.loaded
    copied = _libraryItemSignals.copied
    renamed = _libraryItemSignals.renamed
    deleted = _libraryItemSignals.deleted
    dataChanged = _libraryItemSignals.dataChanged

    def __init__(self, path='', library=None, library_window=None):
        super(LibraryDataItem, self).__init__()

        self._path = None
        self._modal = None
        self._metadata = None
        self._library = None
        self._library_window = None
        self._read_only = False
        self._ignore_exists_dialog = False

        self._default_thumbnail_path = resources.get('icons', self.DEFAULT_THUMBNAIL_NAME)
        self._menu_icon_path = resources.get('icons', self.MENU_ICON_NAME)

        if library_window:
            self.set_library_window(library_window)

        if library:
            self.set_library(library)

        if path:
            self.set_path(path)

    # ============================================================================================================
    # CLASS FUNCTIONS
    # ============================================================================================================

    @classmethod
    def create_action(cls, menu, library_window):
        """
        Returns the action to be displayed when the user clicks the "Add New Item" icon
        :param menu: QMenu
        :param library_window: LibraryWindow
        :return: QAction
        """

        if not cls.NAME:
            LOGGER.warning(
                'Impossible to show "{}" Create Menu because its NAME attribute is not defined!'.format(cls.NAME))
            return

        icon_name = os.path.splitext(cls.MENU_ICON_NAME)[0] if cls.MENU_ICON_NAME else None
        action_icon = resources.icon(icon_name) if icon_name else QIcon()
        callback = partial(cls.show_create_widget, library_window)
        action = QAction(action_icon, cls.NAME, menu)
        action.triggered.connect(callback)
        menu.addAction(action)

        return action

    @classmethod
    def show_create_widget(cls, library_window):
        data_item = cls()

    @classmethod
    def match(cls, path):
        """
        Returns whether the given path locations is supported by the item
        :param path: str
        :return: bool
        """

        extensions = cls.EXTENSIONS if cls.EXTENSIONS else [cls.EXTENSION]
        for ext in extensions:
            path_extension = os.path.splitext(path)[-1]
            if path_extension == ext:
                return True

        return False

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def thumbnail_path(self):
        """
        Return the thumbnail path for the item on disk
        :return: str
        """

        if not self.path():
            return self._default_thumbnail_path

        thumbnail_path = self.path() + '/{}'.format(self.DEFAULT_THUMBNAIL_NAME)
        if os.path.exists(thumbnail_path):
            return thumbnail_path

        thumbnail_path = thumbnail_path.replace('.jpg', '.png')
        if os.path.exists(thumbnail_path):
            return thumbnail_path

        return self._default_thumbnail_path

    def is_default_thumbnail_path(self):
        """
        Returns whether or not current thumbnail path is the default one
        :return: bool
        """

        return self.thumbnail_path() == self._default_thumbnail_path

    def mime_text(self):
        """
        Returns the mime text for drag and drop
        :return: str
        """

        # if self.path():
        #     file_path = path_utils.clean_path(os.path.join(self.path(), self.name()))
        #     if not os.path.isfile(file_path):
        #         file_path = self.path()
        #     return file_path

        return self.path()

    def url(self):
        """
        Used by the mime data when dragging/droping the item
        :return: Qurl
        """

        # if self.path():
        #     file_path = path_utils.clean_path(os.path.join(self.path(), self.name()))
        #     if not os.path.isfile(file_path):
        #         file_path = self.path()
        #     return QUrl('file:///{}'.format(file_path))

        return QUrl('file:///{}'.format(self.path()))

    def create_item_data(self):
        """
        Creates the data dictionary of the current item
        :return: dict
        """

        path = self.path()
        item_data = dict(self.read_metadata())

        dirname, basename, extension = path_utils.split_path(path)
        name = os.path.basename(path)
        category = os.path.basename(dirname) or dirname

        modified = ''
        if os.path.exists(path):
            modified = os.path.getmtime(path)

        item_data.update({
            'name': name,
            'path': path,
            'type': self.DATA_TYPE or extension,
            'folder': dirname,
            'category': category,
            'modified': modified,
            '__class__': '{}.{}'.format(self.__class__.__module__, self.__class__.__name__)
        })

        return item_data

    def sync_item_data(self, emit_data_changed=True):
        """
        Syncs the item data to the data located in the data base
        :param emit_data_changed: bool
        Override in custom items
        """

        data = self.create_item_data()
        self.set_item_data(data)

        if self.library():
            self.library().save_item_data([self], emit_data_changed=emit_data_changed)

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def id(self):
        """
        Returns the unique id for the item
        :return: str
        """

        return self.path()

    def path(self):
        """
        Returns the path for the item
        :return: str
        """

        return self._path

    def set_path(self, path):
        """
        Sets the path location on disk for the item
        :param path: str
        """

        self._path = path_utils.clean_path(path)

    def library(self):
        """
        Returns library model for the item
        :return: DataLibrary
        """

        if not self._library and self.library_window():
            return self.library_window().library()

        return self._library

    def set_library(self, library):
        """
        Sets the library model for the item
        :param library: Library
        """

        if self._library == library:
            return

        self._library = library

    def library_window(self):
        """
        Returns the library widget containing the item
        :return: LibraryWindow
        """

        return self._library_window

    def set_library_window(self, library_window):
        """
        Sets the library widget containing the item
        :param library_window: LibraryWindow
        """

        self._library_window = library_window

    def is_locked(self):
        """
        Returns whether or not this item is locked
        :return: bool
        """

        locked = False
        if self.library_window():
            locked = self.library_window().is_locked()

        return locked

    def is_read_only(self):
        """
        Returns whether or not this item is read only
        :return: bool
        """

        if self.is_locked():
            return True

        return self._read_only

    def set_read_only(self, flag):
        """
        Sets whether or not this item is read only
        :param flag: bool
        """

        self._read_only = flag

    def is_deletable(self):
        """
        Returns whether or not this item is deletable
        :return: bool
        """

        if self.is_locked():
            return False

        return self.ENABLE_DELETE

    # ============================================================================================================
    # LOAD / SAVE
    # ============================================================================================================

    def load(self, *args, **kwargs):
        """
        This function MUST be reimplemented to load any item data
        :param args: list
        :param kwargs: dict
        """

        raise NotImplementedError('load method for {} has not been implemented!'.format(self.__class__.__name__))

    def save(self, *args, **kwargs):
        """
        This function MUST be reimplemented to load any item data
        :param args: list
        :param kwargs: dict
        """

        raise NotImplementedError('save method for {} has not been implemented!'.format(self.__class__.__name__))

    # ============================================================================================================
    # METADATA
    # ============================================================================================================

    def metadata_path(self):
        """
        Returns item metadata paths
        :return: str
        """

        metadata_path = None
        datalib_config = configs.get_library_config('tpDcc-libs-datalibrary')
        if datalib_config:
            metadata_path = datalib_config.get('metadata_path')
            if metadata_path:
                metadata_path = utils.format_path(metadata_path, self.path())
        if not metadata_path:
            metadata_path = path_utils.join_path(path_utils.get_user_data_dir('dataLibrary'), 'metadata.db')

        return metadata_path

    def metadata(self):
        """
        Returns the item metadata info from disk
        :return: dict
        """

        return self._metadata

    def set_metadata(self, metadata):
        """
        Sets the given metadata for the item
        :param metadata: dict
        """

        self._metadata = metadata

    def read_metadata(self):
        """
        Reads the item metadata from disk
        :return: dict
        """

        if not self._metadata:
            metadata_path = self.metadata_path()
            if os.path.isfile(metadata_path):
                self._metadata = utils.read_json(metadata_path)
            else:
                self._metadata = dict()

        return self._metadata

    def update_metadata(self, metadata):
        """
        Updates the current metadata from disk with the given metadata
        :param metadata: dict
        """

        current_metadata = self.read_metadata()
        current_metadata.update(metadata)
        self.save_metadata(current_metadata)

    def save_metadata(self, metadata):
        """
        Saves the given metadata into disk
        :param metadata: dict
        """

        metadata_path = self.metadata_path()
        if not metadata_path or not os.path.isfile(metadata_path):
            return
        utils.save_json(metadata_path, metadata)
        self.set_metadata(metadata)
        self.sync_item_data(emit_data_changed=False)
        self.dataChanged.emit(self)

    # ============================================================================================================
    # SCHEMA
    # ============================================================================================================

    def save_schema(self):
        """
        Returns the schema used for saving the item
        :return: dict
        """

        return list()

    def load_schema(self):
        """
        Gets the options used to load the item
        :return: list(dict)
        """

        return list()

    def save_validator(self, **fields):
        """
        Validates the given save fields
        :param fields: dict
        :return: list(dict)
        """

        return list()

    def load_validator(self, **options):
        """
        Validates the current load options
        :param options: dict
        :return: list(dict)
        """

        return list()

    # ============================================================================================================
    # COPY / RENAME
    # ============================================================================================================

    def copy(self, target):
        """
        Makes a copy/duplicate the current item to the given destination
        :param target: str
        """

        source = self.path()
        target = utils.copy_path(source, target)
        if self.library():
            self.library().copy_path(source, target)
        self.copied.emit(self, source, target)
        if self.library_window():
            self.library_window().refresh()

    def move(self, target):
        """
        Moves the current item to the given destination
        :param target: str
        """

        self.rename(target)

    def rename(self, target, extension=None, rename_file=False):
        """
        Renames the current path to the give destination path
        :param target: str
        :param extension: bool or None
        :param rename_file: bool or None
        """

        library = self.library()

        extension = extension or self.EXTENSION
        if target and extension not in target:
            target += extension

        source = self.path()
        target = utils.rename_path(source, target)

        if library:
            library.rename_path(source, target)

        self._path = target

        self.sync_item_data()

        self.renamed.emit(self, source, target)

    def delete(self):
        """
        Deletes the item from disk and the library model
        """

        utils.remove_path(self.path())
        if self.library():
            self.library().remove_path(self.path())
        self.deleted.emit(self)

    # ============================================================================================================
    # DIALOGS
    # ============================================================================================================

    def show_toast_message(self, text):
        """
        Function that shows the toast widget with the given text
        :param text: str
        """

        if self.library_window():
            self.library_window().show_toast_message(text)

    def show_error_dialog(self, title, text):
        """
        Function that shows an error dialog to the user
        :param title: str
        :param text: str
        :return: QMessageBox.StandardButton or None
        """

        if self.library_window():
            self.library_window().show_error_message(text)

        button = None
        if not self._modal:
            self._modal = True
            try:
                button = messagebox.MessageBox.critical(self.library_window(), title, text)
            finally:
                self._modal = False

        return button

    def show_exception_dialog(self, title, error, exception):
        """
        Function that shows a question dialog to the user
        :param title: str
        :param error: str
        :param exception: str
        """

        LOGGER.exception(exception)
        return self.show_error_dialog(title, error)

    def show_question_dialog(self, title, text):
        """
        Function that shows a question dialog to the user
        :param title: str
        :param text: str
        :return: QMessageBox.StandardButton
        """

        return messagebox.MessageBox.question(self.library_window(), title, text)

    def show_rename_dialog(self, parent=None):
        """
        Shows the rename dialog
        :param parent: QWidget
        """

        select = False
        if self.library_window():
            parent = parent or self.library_window()
            select = self.library_window().selected_folder_path() == self.path()

        name, btn = messagebox.MessageBox.input(
            parent, 'Rename item', 'Rename the current item to:', input_text=self.name())
        if btn == QDialogButtonBox.Ok:
            try:
                self.rename(name)
                if select:
                    self.library_window().select_folder_path(self.path())
            except Exception as e:
                self.show_exception_dialog('Rename Error', e, traceback.format_exc())
                raise

        return btn

    def show_move_dialog(self, parent=None):
        """
        Shows the move to browser dialog
        :param parent: QWidget
        """

        path = os.path.dirname(os.path.dirname(self.path()))
        target = QFileDialog.getExistingDirectory(parent, 'Move To ...', path)
        if target:
            try:
                self.move(target)
            except Exception as exc:
                self.show_exception_dialog('Move Error', exc, traceback.format_exc())
                raise

    def show_delete_dialog(self):
        """
        Shows the delete item dialog
        """

        button = self.show_question_dialog('Delete Item', 'Are you sure you want to delete this item?')
        if button == QDialogButtonBox.Yes:
            try:
                self.delete()
            except Exception as exc:
                self.show_exception_dialog('Delete Error', exc, traceback.format_exc())
                raise

    def show_already_existing_dialog(self):
        """
        Shows a warning dialog if the item already exists on save
        """

        if not self.library_window():
            raise exceptions.ItemSaveError('Item already exists!')

        path = self.path()
        buttons = QMessageBox.Yes | QMessageBox.Cancel

        try:
            QApplication.setOverrideCursor(Qt.ArrowCursor)
            button = self.library_window().show_question_dialog(
                'Item already exists',
                'Would you like to move the existing item "{}" to trash?'.format(self.name()), buttons
            )
        finally:
            QApplication.restoreOverrideCursor()

        if button == QMessageBox.Yes:
            self._move_to_trash()
        else:
            raise exceptions.ItemSaveError('You cannot save over an existing item.')

        return button

    # ============================================================================================================
    # CONTEXTUAL MENUS
    # ============================================================================================================

    def context_menu(self, menu):
        """
        Returns the context menu for the item
        This function MUST be implemented in subclass to return a custom context menu for the item
        :return: QMenu
        """

        pass

    def context_edit_menu(self, menu, items=None):
        """
        This function is called when the user opens context menu
        The given menu is shown as a submenu of the main context menu
        This function can be override to create custom context menus in LibraryItems
        :param menu: QMenu
        :param items: list(LibraryItem)
        """

        rename_action = QAction(resources.icon('rename'), 'Rename', menu)
        rename_action.triggered.connect(self._on_show_rename_dialog)
        menu.addAction(rename_action)

        move_to_action = QAction(resources.icon('move'), 'Move to', menu)
        move_to_action.triggered.connect(self._on_move_dialog)
        menu.addAction(move_to_action)

        copy_path_action = QAction(resources.icon('copy'), 'Copy Path', menu)
        copy_path_action.triggered.connect(self._on_copy_path)
        menu.addAction(copy_path_action)

        if self.library_window():
            select_folder_action = QAction(resources.icon('select'), 'Select Folder', menu)
            select_folder_action.triggered.connect(self._on_select_folder)
            menu.addAction(select_folder_action)

        show_in_folder_action = QAction(resources.icon('folder'), 'Show in Folder', menu)
        show_in_folder_action.triggered.connect(self._on_show_in_folder)
        menu.addAction(show_in_folder_action)

        if self.is_deletable():
            delete_action = QAction(resources.icon('delete'), 'Delete', menu)
            delete_action.triggered.connect(self._on_show_delete_dialog)
            menu.addSeparator()
            menu.addAction(delete_action)

        self.create_overwrite_menu(menu)

    def create_overwrite_menu(self, menu):
        """
        Creates a menu or action to trigger the overwrite functionality
        :param menu: QMenu
        """

        if self.is_read_only():
            return

        menu.addSeparator()
        overwrite_action = QAction(resources.icon('replace'), 'Overwrite', menu)
        overwrite_action.triggered.connect(self._on_overwrite)
        menu.addAction(overwrite_action)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _move_to_trash(self):
        """
        Internal function that moves current item to trash
        """

        path = self.path()
        library = self.library()
        item = LibraryDataItem(path, library=library)
        self.library_window().move_items_to_trash([item])

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_show_rename_dialog(self):
        pass

    def _on_move_dialog(self):
        pass

    def _on_copy_path(self):
        pass

    def _on_select_folder(self):
        pass

    def _on_show_in_folder(self):
        pass

    def _on_show_delete_dialog(self):
        pass

    def _on_overwrite(self):
        pass