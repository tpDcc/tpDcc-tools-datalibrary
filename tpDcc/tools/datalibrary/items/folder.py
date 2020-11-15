#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library folder item widget implementation
"""

from __future__ import print_function, division, absolute_import

from tpDcc.tools.datalibrary.core import dataitem


class LibraryFolderItem(dataitem.LibraryDataItem):

    NAME = 'Folder'
    DATA_TYPE = 'folder'
    ICON_NAME = 'folder'

    MENU_ORDER = 0          # First menu item
    SYNC_ORDER = 100        # Last item to run when syncing

    ENABLE_NESTED_ITEMS = True

    # TypeIconPath = 'folder.png'
    # DefaultThumbnailName = 'folder.png'
    # TrashIconName = 'trash.png'

    def _init__(self, path='', *args, **kwargs):
        super(LibraryFolderItem, self).__init__(path=path, *args, **kwargs)
