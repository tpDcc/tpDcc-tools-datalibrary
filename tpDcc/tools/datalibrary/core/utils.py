#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains utils functions used by tpDcc-tools-datalibrary
"""

from __future__ import print_function, division, absolute_import

import os
import json
import locale
import shutil
import logging
import tempfile
from collections import OrderedDict, Mapping

from tpDcc.managers import configs
from tpDcc.libs.python import osplatform, path as path_utils

LOGGER = logging.getLogger('tpDcc-tools-datalibrary')


def absolute_path(data, start):
    """
    Returns an absolute version of all the paths in data using the start path
    :param data: str
    :param start: str
    :return: str
    """

    rel_path1 = path_utils.normalize_path(os.path.dirname(start))
    rel_path2 = path_utils.normalize_path(os.path.dirname(rel_path1))
    rel_path3 = path_utils.normalize_path(os.path.dirname(rel_path2))

    if not rel_path1.endswith("/"):
        rel_path1 += "/"

    if not rel_path2.endswith("/"):
        rel_path2 += "/"

    if not rel_path3.endswith("/"):
        rel_path3 += "/"

    data = data.replace('../../../', rel_path3)
    data = data.replace('../../', rel_path2)
    data = data.replace('../', rel_path1)

    return data


def update(data, other):
    """
    Update teh value of a nested dictionary of varying depth
    :param data: dict
    :param other: dict
    :return: dict
    """

    for key, value in other.items():
        if isinstance(value, Mapping):
            data[key] = update(data.get(key, {}), value)
        else:
            data[key] = value

    return data


def read(path):
    """
    Returns the contents of the given file
    :param path: str
    :return: str
    """

    data = ''
    path = path_utils.normalize_path(path)
    if os.path.isfile(path):
        with open(path) as f:
            data = f.read() or data
    data = absolute_path(data, path)

    return data


def write(path, data):
    """
    Writes the given data to the given file on disk
    :param path: str
    :param data: str
    """

    path = path_utils.normalize_path(path)
    data = path_utils.get_relative_path(data, path)

    tmp = path + '.tmp'
    bak = path + '.bak'

    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except Exception:
            pass
        if os.path.exists(tmp):
            msg = 'The path is locked for writing and cannot be accessed {}'.format(tmp)
            raise IOError(msg)

    try:
        with open(tmp, 'w') as f:
            f.write(data)
            f.flush()

        if os.path.exists(bak):
            os.remove(bak)
        if os.path.exists(path):
            os.rename(path, bak)
        if os.path.exists(tmp):
            os.rename(tmp, path)
        if os.path.exists(path) and os.path.exists(bak):
            os.remove(bak)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
        if not os.path.exists(path) and os.path.exists(bak):
            os.rename(bak, path)

        raise


def update_json(path, data):
    """
    Update a JSON file with the given data
    :param path: str
    :param data: dict
    """

    data_ = read_json(path)
    data_ = update(data_, data)
    save_json(path, data_)


def read_json(path):
    """
    Reads the given JSON file and deserialize it to a Python object
    :param path: str
    :return: dict
    """

    path = path_utils.normalize_path(path)
    data = read(path) or '{}'
    data = json.loads(data)

    return data


def save_json(path, data):
    """
    Serialize given tdata to a JSON string and write it to the given path
    :param path: str
    :param data: dict
    """

    path = path_utils.normalize_path(path)
    data = OrderedDict(sorted(data.items(), key=lambda t: t[0]))
    data = json.dumps(data, indent=4)
    write(path, data)


def replace_json(path, old, new, count=-1):
    """
    Replaces the old value with the new value in the given JSON file
    :param path: str
    :param old: str
    :param new: str
    :param count: int
    :return: dict
    """

    old = str(old.encode("unicode_escape"))
    new = str(new.encode("unicode_escape"))

    data = read(path) or "{}"
    data = data.replace(old, new, count)
    data = json.loads(data)

    save_json(path, data)

    return data


def format_path(format_string, path='', **kwargs):
    """
    Resolves given path by replacing necessary info with proper data
    :param format_string: str
    :param path: str
    :param kwargs:
    :return: str
    """

    dirname, name, extension = path_utils.split_path(path)
    encoding = locale.getpreferredencoding()

    temp = tempfile.gettempdir()
    if temp:
        try:
            temp = temp.decode(encoding)
        except Exception:
            pass

    username = osplatform.get_user(lower=True)
    if username:
        try:
            username = username.decode(encoding)
        except Exception:
            pass

    local = os.getenv('APPDATA') or os.getenv('HOME')
    if local:
        try:
            local = local.decode(encoding)
        except Exception:
            pass

    kwargs.update(os.environ)

    format_dict = {
        'name': name,
        'path': path,
        'root': path,
        'user': username,
        'temp': temp,
        'home': local,
        'local': local,
        'dirname': dirname,
        'extension': extension
    }
    kwargs.update(format_dict)

    resolve_string = path_utils.normalize_path(format_string).format(**kwargs)

    return path_utils.clean_path(resolve_string)


def copy_path(source, target, force=False):
    """
    Makes a copy of the given source path to the given destination path
    :param source: str
    :param target: str
    :param force: bool
    :return: str
    """

    dirname = os.path.dirname(source)
    if '/' not in target:
        target = os.path.join(dirname, target)

    source = path_utils.normalize_path(source)
    target = path_utils.normalize_path(target)

    if source == target:
        raise IOError('The source path and destination path are the same: {}'.format(source))
    if not force and os.path.exists(target):
        raise IOError('Cannot copy over an existing path: {}'.format(target))

    if force and os.path.exists(target):
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)

    # Ensure target directory exists
    target_directory = os.path.dirname(target)
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    if os.path.isfile(source):
        shutil.copy(source, target)
    else:
        shutil.copytree(source, target)

    return target


def temp_path(*args):
    """
    Returns the temporal directory based on library settings
    :param args:
    """

    datalib_config = configs.get_library_config('tpDcc-libs-datalibrary')
    temp_path = datalib_config.get('temp_path')
    if not temp_path:
        temp_path = tempfile.mkdtemp()

    temp_path = path_utils.normalize_path(os.path.join(format_path(temp_path), *args))

    return temp_path


def settings_path():
    """
    Returns library settings file path
    :return: str
    """

    datalib_config = configs.get_tool_config('tpDcc-tools-datalibrary')
    settings_file_path = datalib_config.get('settings_path')
    settings_file_path = format_path(settings_file_path)

    return settings_file_path


def read_settings(settings_file_path):
    """
    Returns all user settings
    :return: dict
    """

    path = settings_file_path or settings_path()
    data = dict()
    try:
        data = read_json(path)
    except Exception:
        LOGGER.exception('Cannot read settings from "{}"'.format(path))

    return data


def update_settings(data, settings_file_path=None):
    """
    Updates the settings with the given data
    :param data: dict
    :param settings_file_path: str or None
    """

    settings = read_settings(settings_file_path)
    update(settings, data)
    save_settings(settings)


def save_settings(data, settings_file_path=None):
    """
    Saves the given data to the settings path
    :param data: dict
    :param settings_file_path: str or None
    """

    path = settings_file_path or settings_path()
    try:
        save_json(path, data)
    except Exception:
        LOGGER.exception('Cannot save settings to "{}"'.format(path))
