#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains different widgets used in libraries
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt, QSize
from Qt.QtWidgets import QSizePolicy, QWidget, QToolButton, QToolBar, QAction
from Qt.QtGui import QColor, QPainter, QBrush

from tpDcc.libs.resources.core import icon
from tpDcc.libs.qt.core import qtutils, image, animation


class ImageSequenceWidget(QToolButton, object):

    DEFAULT_PLAYHEAD_COLOR = QColor(255, 255, 255, 220)
    DEFAULT_PLAYHEAD_HEIGHT = 4

    def __init__(self, *args):
        super(ImageSequenceWidget, self).__init__(*args)

        self.setMouseTracking(True)

        self._image_sequence = image.ImageSequence('')
        self._image_sequence.frameChanged.connect(self._on_frame_changed)

        self._toolbar = QToolBar(self)
        animation.fade_out_widget(self._toolbar, duration=0)

        spacer = QWidget()
        spacer.setMaximumWidth(4)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._toolbar.addWidget(spacer)

        spacer1 = QWidget()
        spacer1.setMaximumWidth(4)
        spacer1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._first_spacer = self._toolbar.addWidget(spacer1)

        self.set_size(150, 150)

    # =================================================================================================================
    # OVERRIDES
    # =================================================================================================================

    def addAction(self, path, text, tip, callback):
        """
        Overrides base QToolButton addAction function
        Adds aan action to the toolbar
        :param path: str
        :param text: str
        :param tip: str
        :param callback: fn
        :return: QAction
        """

        action_icon = icon.Icon.state_icon(
            path,
            color='rgb(250,250,250,160)',
            color_active='rgb(250,250,250,250)',
            color_disabled='rgb(0,0,0,20)'
        )
        action = QAction(action_icon, text, self._toolbar)
        action.setToolTip(tip)
        self._toolbar.insertAction(self._first_spacer, action)
        action.triggered.connect(callback)

        return action

    def actions(self):
        """
        Overrides base QToolButton actions function
        Returns all the actions that are a child of the toolbar
        :return: list(QAction)
        """

        actions = list()
        for child in self._toolbar.children():
            if isinstance(child, QAction):
                actions.append(child)

        return actions

    def resizeEvent(self, event):
        """
        Overrides base QToolButton resizeEvent function
        Called when the widget is resized
        :param event: QResizeEvent
        """

        self.update_toolbar()

    def enterEvent(self, event):
        """
        Overrides base QToolButton enterEvent function
        Starts playing the image sequence when the mouse enters the widget
        :param event: QEvent
        """

        self._image_sequence.start()
        animation.fade_in_widget(self._toolbar, duration=300)

    def leaveEvent(self, event):
        """
        Overrides base QToolButton leaveEvent function
        Stops playing the image sequence when the mouse leaves the widget
        :param event: QEvent
        """

        self._image_sequence.pause()
        animation.fade_out_widget(self._toolbar, duration=300)

    def mouseMoveEvent(self, event):
        """
        Overrides base QToolButton mouseMoveEvent function
        :param event: QEvent
        """

        if qtutils.is_control_modifier() and self._image_sequence.frame_count() > 1:
            percent = 1.0 - (float(self.width() - event.pos().x()) / float(self.width()))
            frame = int(self._image_sequence.frame_count() * percent)
            self._image_sequence.jump_to_frame(frame)
            frame_icon = self._image_sequence.current_icon()
            self.setIcon(frame_icon)

    def paintEvent(self, event):
        """
        Overrides base QToolButton paintEvent function
        Triggered on frame changed
        :param event: QEvent
        """

        super(ImageSequenceWidget, self).paintEvent(event)

        painter = QPainter()
        painter.begin(self)
        if self.current_filename() and self._image_sequence.frame_count() > 1:
            r = event.rect()
            playhead_height = self.playhead_height()
            playhead_pos = self._image_sequence.percent() * r.width() - 1
            x = r.x()
            y = self.height() - playhead_height
            painter.seten(Qt.NoPen)
            painter.setBrush(QBrush(self.DEFAULT_PLAYHEAD_COLOR))
            painter.drawRect(x, y, playhead_pos, playhead_height)

        painter.end()

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def is_sequence(self):
        """
        Returns whether or not the image sequence has more than one frame
        :return: bool
        """

        return bool(self._image_sequence.frame_count() > 1)

    def dirname(self):
        """
        Returns the directory where the image sequence is located on disk
        :return: str
        """

        return self._image_sequence.dirname()

    def has_frames(self):
        """
        Returns whether or not image sequences has any frames
        :return: bool
        """

        return bool(self.first_frame())

    def first_frame(self):
        """
        Returns first frame path in the image sequence
        :return: str
        """

        return self._image_sequence.first_frame()

    def set_path(self, path):
        """
        Sets a single frame image sequence
        :param path: str
        """

        self._image_sequence.set_path(path)
        self.update_icon()

    def set_dirname(self, dirname):
        """
        Sets the location of the image sequence
        :param dirname: str
        """

        self._image_sequence.set_dirname(dirname)
        self.update_icon()

    def current_filename(self):
        """
        Returns the current image location
        :return: str
        """

        return self._image_sequence.current_filename()

    def playhead_height(self):
        """
        Returns the height of the playhead
        :return: int
        """

        return self.DEFAULT_PLAYHEAD_COLOR

    def set_size(self, w, h):
        """
        Set the size of the widget and updates icon size at the same time
        :param w: int
        :param h: int
        """

        self._size = QSize(w, h)
        self.setIconSize(self._size)
        self.setFixedSize(self._size)

    def update_icon(self):
        """
        Updates the icon for the current frame
        """

        if self._image_sequence.frames():
            frame_icon = self._image_sequence.current_icon()
            self.setIcon(frame_icon)

    def update_toolbar(self):
        """
        Updates the toolbar size depending on the number of actions
        """

        self._toolbar.setIconSize(QSize(16, 16))
        count = len(self.actions()) - 3
        width = 26 * count
        self._toolbar.setGeometry(0, 0, width, 25)
        x = self.rect().center().x() - (self._toolbar.width() * 0.5)
        y = self.height() - self._toolbar.height() - 12
        self._toolbar.setGeometry(x, y, self._toolbar.width(), self._toolbar.height())

    # =================================================================================================================
    # CALLBACKS
    # =================================================================================================================

    def _on_frame_changed(self, frame=None):
        """
        Internal callback function triggered when the image sequence changes frame
        :param frame: int or None
        """

        if not qtutils.is_control_modifier():
            frame_icon = self._image_sequence.current_icon()
            self.setIcon(frame_icon)
