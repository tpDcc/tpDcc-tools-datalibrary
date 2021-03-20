#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains utils functions to handle persistent wigdet values settings
"""

from __future__ import print_function, division, absolute_import

import os

from tpDcc.managers import libs
from tpDcc.libs.python import path as path_utils

from tpDcc.tools.datalibrary.core import utils


_SETTINGS = dict()


def path():
    """
    Returns settings path
    :return: str
    """

    libs_file_path = libs.LibsManager().get_library_settings_file_path('tpDcc-libs-datalibrary')

    return path_utils.join_path(os.path.dirname(libs_file_path), 'widgetSettings.json')


def read():
    """
    Returns widget related settings
    :return: dict
    """

    global _SETTINGS
    if not _SETTINGS:
        _SETTINGS = utils.read_json(path())

    return _SETTINGS


def save(data):
    """
    Saves the given data dictionary to settings
    :param data: dict
    """

    global _SETTINGS
    _SETTINGS = dict()
    utils.update_json(path(), data)


def get(key, default=None):
    """
    Returns value from disk
    :param key: str
    :param default: object
    :return: object
    """

    return read().get(key, default)


def set(key, value):
    """
    Sets settings value to disk
    :param key: str
    :param value: object
    """

    save({key: value})


def reset():
    """
    Removes and resets the item settings
    """

    global _SETTINGS
    _SETTINGS = dict()
    utils.remove_path(path())
