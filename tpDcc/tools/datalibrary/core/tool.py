#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tool to manage DCC related data in an easy way.
"""

from __future__ import print_function, division, absolute_import

import os
import sys
import logging

from tpDcc.core import tool
from tpDcc.core import dcc

from tpDcc.tools.datalibrary.core import consts, client, toolset

LOGGER = logging.getLogger(consts.TOOL_ID)


class DataLibraryTool(tool.DccTool, object):

    ID = consts.TOOL_ID
    CLIENT_CLASS = client.DataLibraryClient
    TOOLSET_CLASS = toolset.DataLibraryToolset

    def __init__(self, *args, **kwargs):
        super(DataLibraryTool, self).__init__(*args, **kwargs)

    @classmethod
    def config_dict(cls, file_name=None):
        base_tool_config = tool.DccTool.config_dict(file_name=file_name)
        tool_config = {
            'name': 'Data Library',
            'id': cls.ID,
            'supported_dccs': {
                dcc.Dccs.Maya: ['2017', '2018', '2019', '2020'],
                dcc.Dccs.Max: ['2017.0', '2018.0', '2019.0', '2020.0']
            },
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


if __name__ == '__main__':
    import tpDcc.loader
    from tpDcc.managers import tools

    tool_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    if tool_path not in sys.path:
        sys.path.append(tool_path)

    tpDcc.loader.init()
    tools.ToolsManager().launch_tool_by_id(DataLibraryTool.ID)
    # tools.ToolsManager().launch_tool_by_id(consts.TOOL_ID)
