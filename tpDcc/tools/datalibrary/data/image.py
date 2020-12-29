#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library data item widget implementation
"""

from __future__ import print_function, division, absolute_import

import os

from tpDcc.libs.datalibrary.data import png, jpg

from tpDcc.tools.datalibrary.data import base


class ImageItemView(base.BaseDataItemView):

    REPRESENTING = [png.PngImageData.__name__, jpg.JpgImageData.__name__]

    NAME = 'Image View'

    def thumbnail_path(self):

        item_path = self.item.format_identifier()
        if os.path.isfile(item_path):
            return item_path

        return self._default_thumbnail_path
