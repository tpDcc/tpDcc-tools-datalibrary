#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that defines toolset widget implementation for tpDcc-tools-datalibrary
"""

from __future__ import print_function, division, absolute_import

import os

from tpDcc.libs.qt.widgets import toolset
from tpDcc.tools.datalibrary.widgets import window
from tpDcc.tools.datalibrary.widgets import settings


class DataLibraryToolset(toolset.ToolsetWidget, object):
    def __init__(self, *args, **kwargs):
        super(DataLibraryToolset, self).__init__(*args, **kwargs)

        self._repository_widget = settings.DataRepositoryWidget(parent=self._preferences_widget)
        self._preferences_widget.add_category(self._repository_widget.CATEGORY, self._repository_widget)

    @property
    def library_window(self):
        return self._data_library_window

    def post_content_setup(self):
        if not self.client:
            return

        item_paths = self.client.load_data_items() or list()

        paths_to_register = list()
        for item_path in item_paths:
            if not item_path or not os.path.isdir(item_path):
                continue
            paths_to_register.append(item_path)

        library = self._data_library_window.library()
        if not library:
            return

        for path_to_register in paths_to_register:
            library.register_plugin_path(path_to_register)

    def contents(self):
        self._data_library_window = window.LibraryWindow(settings=self.settings, parent=self, client=self._client)
        return [self._data_library_window]
