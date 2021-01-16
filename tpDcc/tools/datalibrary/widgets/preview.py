#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base preview widget for data items
"""

from __future__ import print_function, division, absolute_import

from Qt.QtCore import Qt, QSize
from Qt.QtWidgets import QWidget, QFrame, QMenu
from Qt.QtGui import QCursor

from tpDcc.managers import resources
from tpDcc.libs.qt.core import base
from tpDcc.libs.qt.widgets import layouts, label, buttons, formwidget, group

from tpDcc.tools.datalibrary.widgets import sequence


class PreviewWidget(base.BaseWidget, object):
    def __init__(self, item_view, parent=None):

        self._item_view = item_view
        self._sequence_widget = None
        self._form_widget = None

        super(PreviewWidget, self).__init__(parent=parent)

        self._create_sequence_widget()

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def get_main_layout(self):
        main_layout = layouts.VerticalLayout(spacing=2, margins=(0, 0, 0, 0))
        main_layout.setAlignment(Qt.AlignTop)

        return main_layout

    def ui(self):
        super(PreviewWidget, self).ui()

        title_frame = QFrame(self)
        title_frame_layout = layouts.HorizontalLayout(spacing=0, margins=(0, 0, 0, 0))
        title_frame.setLayout(title_frame_layout)
        title_widget = QWidget(self)
        title_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        title_widget.setLayout(title_layout)
        buttons_layout = layouts.HorizontalLayout(spacing=0, margins=(0, 0, 0, 0))
        title_layout.addLayout(buttons_layout)
        self._title_icon = label.BaseLabel(parent=self)
        self._title_button = label.ElidedLabel(parent=self)
        self._title_button.setText(self.item().name())
        self._menu_button = buttons.BaseButton(parent=self)
        self._menu_button.setIcon(resources.icon('menu_dots'))
        buttons_layout.addWidget(self._title_icon)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self._title_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self._menu_button)
        title_frame_layout.addWidget(title_widget)

        item_icon_name = self.item().icon() or 'tpDcc'
        item_icon = resources.icon(item_icon_name)
        if not item_icon:
            item_icon = resources.icon('tpDcc')
        self._title_icon.setPixmap(item_icon.pixmap(QSize(20, 20)))

        icon_title_frame = QFrame(self)
        icon_title_frame_layout = layouts.VerticalLayout(spacing=0, margins=(4, 2, 4, 2))
        icon_title_frame.setLayout(icon_title_frame_layout)

        self._icon_group_frame = QFrame(self)
        icon_group_layout = layouts.HorizontalLayout(spacing=0, margins=(0, 0, 0, 0))
        self._icon_group_frame.setLayout(icon_group_layout)
        self._icon_frame = QFrame(self)
        icon_frame_layout = layouts.VerticalLayout(spacing=0, margins=(4, 2, 4, 2))
        self._icon_frame.setLayout(icon_frame_layout)
        icon_group_layout.addWidget(self._icon_frame)
        icon_group_box_widget = group.GroupBoxWidget('Icon', widget=self._icon_group_frame, parent=self)
        icon_title_frame_layout.addWidget(icon_group_box_widget)

        form_frame = QFrame(self)
        form_frame_layout = layouts.VerticalLayout(spacing=0, margins=(4, 2, 4, 2))
        form_frame.setLayout(form_frame_layout)

        buttons_frame = QFrame(self)
        buttons_frame_layout = layouts.HorizontalLayout(spacing=4, margins=(4, 4, 4, 4))
        buttons_frame.setLayout(buttons_frame_layout)

        self._accept_button = buttons.BaseButton('Load')
        self._accept_button.setIcon(resources.icon('open'))
        self._accept_button.setVisible(False)
        buttons_frame_layout.addWidget(self._accept_button)

        schema = self._item_view.item.load_schema() if self._item_view else None
        if schema:
            self._form_widget = formwidget.FormWidget(self)
            self._form_widget.setObjectName('{}Form'.format(self._item_view.__class__.__name__))
            self._form_widget.set_schema(schema)
            self._form_widget.set_validator(self.validator)
            form_frame_layout.addWidget(self._form_widget)

        self.main_layout.addWidget(title_frame)
        self.main_layout.addWidget(icon_title_frame)
        self.main_layout.addWidget(self._icon_group_frame)
        self.main_layout.addWidget(form_frame)
        self.main_layout.addStretch()
        self.main_layout.addWidget(buttons_frame)

    def setup_signals(self):
        self._menu_button.clicked.connect(self._on_show_menu)
        self._accept_button.clicked.connect(self.on_load)

    def resizeEvent(self, event):
        """
        Overrides base BaseWidget resizeEvent function to make sure the icon image size is updated
        :param event: QSizeEvent
        """

        self.update_thumbnail_size()

    def close(self):
        """
        Overrides base BaseWidget close function to save widget persistent data
        """

        # TODO: It is not sure this function it is going to be called when the app is closed
        # TODO: Find a better approach

        if self._form_widget:
            self._form_widget.save_persistent_values()

        super(PreviewWidget, self).close()

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def item(self):
        """
        Returns the library item to load
        :return: LibraryItem
        """

        return self._item_view

    def validator(self, **kwargs):
        """
        Returns validator used for validating the item loaded arguments
        :param kwargs: dict
        """

        self._item_view.load_validator(**kwargs)
        self.update_icon()

    def update_icon(self):
        """
        Updates item thumbnail icon
        """

        # Updates static icon
        icon = self._item_view.thumbnail_icon()
        if icon:
            self._sequence_widget.setIcon(icon)

        # Update images sequence (if exist)
        if self._item_view.image_sequence_path():
            self._sequence_widget.set_dirname(self._item_view.image_sequence_path())

    def update_thumbnail_size(self):
        """
        Updates the thumbnail button to the size of the widget
        """

        width = self.width() - 5
        width = width if width <= 150 else 150
        size = QSize(width, width)
        self._icon_frame.setMaximumSize(size)
        self._icon_group_frame.setMaximumSize(size)

        if self._sequence_widget:
            self._sequence_widget.setIconSize(size)
            self._sequence_widget.setMinimumSize(size)
            self._sequence_widget.setMaximumSize(size)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _create_sequence_widget(self):
        """
        Internal function that creates sequence widget for the item
        """

        self._sequence_widget = sequence.ImageSequenceWidget(self._icon_frame)
        self._icon_frame.layout().insertWidget(0, self._sequence_widget)
        self.update_icon()

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_item_data_changed(self, *args, **kwargs):
        """
        Internal callback function that is called when item data changes
        :param args:
        :param kwargs:
        """

        self.update_icon()

    def _on_show_menu(self):
        """
        Internal callback function triggered when item menu should be opened
        :return: QAction
        """

        menu = QMenu(self)
        self.item().context_edit_menu(menu)
        point = QCursor.pos()
        point.setX(point.x() + 3)
        point.setY(point.y() + 3)

        return menu.exec_(point)

    def on_load(self):
        """
        Internal callback function that is triggered when load button is pressed by the user
        """

        kwargs = self._form_widget.values()
        self._item_view.load(**kwargs)
