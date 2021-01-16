#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base item factory implementation
"""

from __future__ import print_function, division, absolute_import

import os

from tpDcc import dcc
from tpDcc.libs.python import decorators, plugin
from tpDcc.libs.datalibrary.data import folder

from tpDcc.tools.datalibrary.core.views import item
from tpDcc.tools.datalibrary.data import base, folder as folder_view
from tpDcc.tools.datalibrary.widgets import load, save, export


class _MetaItemsFactory(type):

    def __call__(self, *args, **kwargs):
        return type.__call__(BaseItemsFactory, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        if dcc.client().is_maya():
            from tpDcc.tools.datalibrary.dccs.maya.core import factory
            return type.__call__(factory.MayaItemsFactory, *args, **kwargs)
        else:
            return type.__call__(BaseItemsFactory, *args, **kwargs)


class BaseItemsFactory(plugin.PluginFactory):
    def __init__(self, paths=None):
        super(BaseItemsFactory, self).__init__(
            interface=item.ItemView, plugin_id='NAME', version_id='VERSION', paths=paths)

        self._register_default_paths()

        self._potential_views = sorted(self.plugins(), key=lambda p: p.PRIORITY)
        self._default_view = self.get_plugin_from_id('Data View')

    def _register_default_paths(self):
        self.register_path(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))

    def get_view(self, data_instance):
        """
        Returns the view to be used by the given DataPart
        :param data_instance: DataPart instance
        :return: DataItemView
        """

        for item_view in self._potential_views:
            for component in data_instance.components():
                if str(component) in item_view.REPRESENTING:
                    return item_view

        return self._default_view

    def get_show_save_widget_function(self, data_instance):
        if data_instance == folder.FolderData:
            return folder_view.FolderItemView.show_save_widget

        return base.BaseDataItemView.show_save_widget

    def get_save_widget_class(self, data_instance):
        return save.SaveWidget

    def get_load_widget_class(self, data_instance):
        return load.LoadWidget

    def get_export_widget_class(self, data_instance):
        return export.ExportWidget


@decorators.add_metaclass(_MetaItemsFactory)
class ItemsFactory(object):
    pass
