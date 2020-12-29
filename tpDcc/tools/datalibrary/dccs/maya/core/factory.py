#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base item factory implementation for Maya
"""

import os

from tpDcc.libs.datalibrary.dccs.maya.data import mayaascii, mayabinary

from tpDcc.tools.datalibrary.core import factory
from tpDcc.tools.datalibrary.dccs.maya.widgets import save, load


class MayaItemsFactory(factory.BaseItemsFactory):
    def __init__(self, *args, **kwargs):
        super(MayaItemsFactory, self).__init__(*args, **kwargs)

    def _register_default_paths(self):
        super(MayaItemsFactory, self)._register_default_paths()

        self.register_path(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))

    def get_save_widget_class(self, data_instance):
        if data_instance in (mayaascii.MayaAsciiData, mayabinary.MayaBinaryData):
            return save.MayaSaveWidget

        return super(MayaItemsFactory, self).get_save_widget_class(data_instance)

    def get_load_widget_class(self, data_instance):
        if data_instance in (mayaascii.MayaAsciiData, mayabinary.MayaBinaryData):
            return load.MayaLoadWidget

        return super(MayaItemsFactory, self).get_load_widget_class(data_instance)
