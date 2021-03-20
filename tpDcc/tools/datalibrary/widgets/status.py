#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains status data library widget implementation
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.qt.core import statusbar
from tpDcc.libs.qt.widgets import progressbar


class DataStatusWidget(statusbar.StatusWidget):

    DEFAULT_DISPLAY_TIME = 5000  # milliseconds -> 5 seconds

    def __init__(self, *args, **kwargs):
        super(DataStatusWidget, self).__init__(*args, **kwargs)

        self._progress_bar = progressbar.FrameProgressBar(self)
        self._progress_bar.setVisible(False)
        self.main_layout.addWidget(self._progress_bar)

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def progress_bar(self):
        """
        Returns the progress bar widget
        :return:  progressbar.ProgressBar
        """

        return self._progress_bar
