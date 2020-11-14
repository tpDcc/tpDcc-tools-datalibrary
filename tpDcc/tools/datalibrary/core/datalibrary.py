#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tool to manage DCC related data in an easy way.
"""

from __future__ import print_function, division, absolute_import

import os

from tpDcc.core import tool
from tpDcc.libs.qt.widgets import toolset

from tpDcc.libs.datalibrary.managers import data

# Defines ID of the tool
TOOL_ID = 'tpDcc-tools-datalibrary'


class DataLibraryTool(tool.DccTool, object):
    def __init__(self, *args, **kwargs):
        super(DataLibraryTool, self).__init__(*args, **kwargs)

    @classmethod
    def config_dict(cls, file_name=None):
        base_tool_config = tool.DccTool.config_dict(file_name=file_name)
        tool_config = {
            'name': 'Data Library',
            'id': TOOL_ID,
            'icon': 'datalibrary',
            'tooltip': 'Tool to manage DCC related data in an easy way.',
            'tags': ['tpDcc', 'dcc', 'tool', 'data'],
            'is_checkable': False,
            'is_checked': False,
            'menu_ui': {'label': 'Data Library', 'load_on_startup': False, 'color': '', 'background_color': ''},
        }
        base_tool_config.update(tool_config)

        return base_tool_config

    def launch(self, *args, **kwargs):
        return self.launch_frameless(*args, **kwargs)


class DataLibraryToolset(toolset.ToolsetWidget, object):
    ID = TOOL_ID

    def __init__(self, *args, **kwargs):
        super(DataLibraryToolset, self).__init__(*args, **kwargs)

        default_items_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'items')
        data.add_directory(default_items_path, 'tpDcc', do_reload=True)

    def contents(self):

        from tpDcc.tools.datalibrary.widgets import window

        data_library_window = window.LibraryWindow(parent=self)
        return [data_library_window]
