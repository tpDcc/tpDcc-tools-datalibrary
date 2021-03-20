#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base library item view implementation
"""

from __future__ import print_function, division, absolute_import

import os
import logging

from Qt.QtCore import Qt
from Qt.QtWidgets import QApplication, QAction

from tpDcc import dcc
from tpDcc.managers import resources
from tpDcc.libs.python import decorators, path as path_utils

from tpDcc.tools.datalibrary.core.views import dataitem

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class _MetaBaseDataItem(type):

    def __call__(self, *args, **kwargs):
        as_class = kwargs.get('as_class', True)
        if dcc.client().is_maya():
            from tpDcc.libs.datalibrary.dccs.maya.core import dataitem
            if as_class:
                return dataitem.MayaDataItemView
            else:
                return type.__call__(dataitem.MayaDataItemView, *args, **kwargs)
        else:
            if as_class:
                return BaseDataItemView
            else:
                return type.__call__(BaseDataItemView, *args, **kwargs)


class BaseDataItemView(dataitem.DataItemView):

    NAME = 'Data View'

    def __init__(self, data_item=None, *args, **kwargs):
        super(BaseDataItemView, self).__init__(data_item=data_item, *args, **kwargs)

        # self._item.emitError.connect(self._on_item_error)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def context_menu(self, menu, items=None):
        """
        Returns the context menu for the item
        :return: QMenu
        """

        self._select_content_action = QAction(resources.icon('cursor'), 'Select content', menu)
        self._select_content_action.triggered.connect(self.select_content)
        menu.addAction(self._select_content_action)
        menu.addSeparator()

    @classmethod
    def show_save_widget(cls, item_class, library_window, item_view=None):
        """
        Function used to show the create widget of the current item
        Override to allow us set the destination location for the save widget
        :param item_class: DataItem
        :param library_window: LibraryWindow
        :param item_view: LibraryItem or None
        """

        library = library_window.library()
        if not library:
            LOGGER.warning('Impossible to save data because library is not defined!')
            return

        save_widget_class = library_window.factory.get_save_widget_class(item_class)
        if not save_widget_class:
            LOGGER.warning(
                'Impossible to create new item of type "{}" because no save widget implementation defined!'.format(
                    item_class.__name__))
            return

        item_path = library_window.selected_folder_path()
        if not item_path or not os.path.exists(item_path):
            item_path = library_window.path()

        if not item_view:
            # NOTE: Here we generate a temporal file name to generate the proper composite data
            temp_item_path = path_utils.join_path(item_path, '__temp__{}'.format(item_class.EXTENSION))
            item_data = library.get(temp_item_path, only_extension=True)
            item_view_class = library_window.factory.get_view(item_data)
            item_view = item_view_class(item_data, library_window=library_window)

        widget = save_widget_class(item_view=item_view, client=library_window.client, parent=library_window)
        widget.set_folder_path(item_path)
        widget.set_library_window(library_window)
        library_window.set_save_widget(widget)
        library_window.folderSelectionChanged.connect(widget.set_folder_path)

    @classmethod
    def show_export_widget(cls, item_class, data_path, library_window):
        """
        Function used to show the export widget of the current item
        :param data_path: DataItem
        :param library_window: LibraryWindow
        """

        library = library_window.library()
        if not library:
            LOGGER.warning('Impossible to export data because library is not defined!')
            return

        export_widget_class = library_window.factory.get_export_widget_class(item_class)
        if not export_widget_class:
            LOGGER.warning(
                'Impossible to export item of type "{}" because no export widget implementation defined!'.format(
                    item_class.__name__))
            return

        if not data_path or not os.path.isfile(data_path):
            LOGGER.warning('Impossible to export item "{}" because its path does not exists: "{}"'.format(
                item_class, data_path))
            return

        item_data = library.get(data_path, only_extension=True)
        if not item_data:
            LOGGER.warning('Impossible to export data "{}" because was not found!'.format(data_path))
            return

        item_view_class = library_window.factory.get_view(item_data)
        item_view = item_view_class(item_data, library_window=library_window)

        widget = export_widget_class(item_view=item_view, client=library_window.client, parent=library_window)
        widget.set_library_window(library_window)
        library_window.set_export_widget(widget)

    def double_clicked(self):
        """
        Triggered when an item is double clicked
        """

        # self._item.load_from_current_values()

        load_function = self._item.functionality().get('load')
        if not load_function:
            return

        load_function()

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def select_content(self, **kwargs):
        """
        Select the contents of this item in the current DCC scene
        :param kwargs: dict
        """

        kwargs = kwargs or self._selection_modifiers()
        self._item.select_content(**kwargs)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _selection_modifiers(self):
        """
        Internal function that returns a dictionary with the current key modifiers
        :return: dict
        """

        result = {'add': False, 'deselect': False}
        modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.ShiftModifier:
            result['deselect'] = True
        elif modifiers == Qt.ControlModifier:
            result['add'] = True

        return result

    def _on_item_error(self, error, trace):
        self.show_error_dialog(str(error), str(trace))


@decorators.add_metaclass(_MetaBaseDataItem)
class DataItemView(object):
    pass
