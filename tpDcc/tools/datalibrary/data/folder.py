#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library folder item widget implementation
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt, QLocale, QFileInfo
from Qt.QtWidgets import QDialogButtonBox, QAction
from Qt.QtGui import QPainter

import os

from tpDcc.managers import resources
from tpDcc.libs.python import path as path_utils
from tpDcc.libs.resources.core import theme, color as qt_color, pixmap as qt_pixmap, icon as qt_icon
from tpDcc.libs.qt.widgets import messagebox, action
from tpDcc.libs.datalibrary.data import folder

from tpDcc.tools.datalibrary.core import consts
from tpDcc.tools.datalibrary.widgets import preview
from tpDcc.tools.datalibrary.core.views import dataitem


@theme.mixin
class FolderItemView(dataitem.DataItemView):

    NAME = 'Folder View'
    REPRESENTING = [folder.FolderData.__name__]

    LOAD_WIDGET_CLASS = preview.PreviewWidget

    DEFAULT_THUMBNAIL_NAME = 'folder.png'

    _THUMBNAIL_ICON_CACHE = dict()

    def _init__(self, *args, **kwargs):
        super(FolderItemView, self).__init__(*args, **kwargs)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    @classmethod
    def show_save_widget(cls, item_class, library_window, item_view=None):
        """
        Function used to show the create widget of the current item
        :param library_window: LibraryWindow
        :param item_view: LibraryItem or None
        """

        path = library_window.selected_folder_path() or library_window.path()
        name, button = messagebox.MessageBox.input(
            library_window, 'Create Folder', 'Create a new folder with the name:')
        if not name or not button == QDialogButtonBox.Ok:
            return
        path = path_utils.join_path(path, name.strip())

        item_data = item_class(path, library_window.library())
        if not item_data:
            return

        save_function = item_data.functionality().get('save')
        if not save_function:
            return

        valid = save_function()
        if not valid:
            return

        if library_window:
            library_window.sync()
            library_window.refresh()
            library_window.select_folder_path(path)

    def double_clicked(self):
        """
        Triggered when an item is double clicked
        """

        if not self.library_window():
            return

        self.library_window().select_folder_path(self.path())

    def thumbnail_icon(self):
        """
        Returns the thumbnail icon
        :return: QIcon
        """

        # custom_path = self.custom_icon_path()
        # if custom_path and '/' not in custom_path and '\\' not in custom_path:
        #     custom_path = resources.icon('icons/{}'.format(self.theme().style()), custom_path)
        # if not custom_path or not os.path.isfile(custom_path):
        #     return super(FolderItemView, self).thumbnail_icon()

        return super(FolderItemView, self).thumbnail_icon()

        color = self.icon_color()
        if not color:
            color = consts.DEFAULT_FOLDER_ICON_COLOR

        icon_key = custom_path + color

        icon = self._THUMBNAIL_ICON_CACHE.get(icon_key)
        if not icon:
            color1 = qt_color.Color.from_string(color)
            color2 = qt_color.Color.from_string('rgb(255, 255, 255, 150)')
            pixmap1 = qt_pixmap.Pixmap(self.THUMBNAIL_PATH)
            pixmap2 = qt_pixmap.Pixmap(custom_path)
            pixmap1.set_color(color1)
            pixmap2.set_color(color2)
            pixmap1 = pixmap1.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pixmap2 = pixmap2.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (128 - pixmap2.width()) / 2
            y = (128 - pixmap2.width()) / 2
            painter = QPainter(pixmap1)
            painter.drawPixmap(x, y + 5, pixmap2)
            painter.end()
            icon = qt_icon.Icon(pixmap1)
            self._THUMBNAIL_ICON_CACHE[icon_key] = icon

        return self._THUMBNAIL_ICON_CACHE.get(icon_key)

    def context_edit_menu(self, menu, items=None):
        """
        This function is called when the user opens context menu
        The given menu is shown as a submenu of the main context menu
        This function can be override to create custom context menus in LibraryItems
        :param menu: QMenu
        :param items: list(LibraryItem)
        """

        super(FolderItemView, self).context_edit_menu(menu, items=items)

        # show_preview_action = QAction(resources.icon('preview'), 'Show in Preview', menu)
        # show_preview_action.triggered.connect(self._on_show_preview_from_menu)
        # menu.addAction(show_preview_action)
        # menu.addSeparator()
        # color_picker_action = action.ColorPickerAction(menu)
        # color_picker_action.picker().set_colors(consts.DEFAULT_FOLDER_ICON_COLORS)
        # color_picker_action.picker().colorChanged.connect(self.set_icon_color)
        # color_picker_action.picker().set_current_color(self.icon_color())
        # menu.addAction(color_picker_action)
        # icon_name = self.item.data.get('icon', '')
        # icon_picker_action = action.IconPickerAction(menu)
        # icon_picker_action.picker().set_icons(consts.DEFAULT_FOLDER_ICONS)
        # icon_picker_action.picker().set_current_icon(icon_name)
        # icon_picker_action.picker().iconChanged.connect(self.set_custom_icon)
        # menu.addAction(icon_picker_action)

        # color_picker_action.setVisible(False)
        # icon_picker_action.setVisible(False)

    def create_overwrite_menu(self, menu):
        """
        Overwrites base LibraryDataItem create_overwrite_menu function to hide the overwrite menu action
        :param menu: QMenu
        """

        pass

    def _on_metadata_updated(self, metadata):
        """
        Internal callback function that is called when metadata is updated
        Override to support the update of the library widget directly
        :param metadata: dict
        """

        super(FolderItemView, self)._on_metadata_updated(metadata)

        if self.library_window():
            self.library_window().set_folder_data(self.path(), self.item.data)
            self.update_icon()

    # ============================================================================================================
    # CALLBACK
    # ============================================================================================================

    def _on_show_preview_from_menu(self):
        if self.library_window():
            self.library_window().viewer().clear_selection()
        self.show_preview_widget(self.library_window())
