#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tests for tpDcc-tools-datalibrary
"""

import pytest

from tpDcc.tools.datalibrary import __version__


def test_version():
    assert __version__.get_version()
