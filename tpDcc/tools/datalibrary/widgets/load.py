#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base load widget for data items
"""

from __future__ import print_function, division, absolute_import

import os
import logging

from Qt.QtCore import QSize
from Qt.QtWidgets import QSizePolicy, QFrame, QMenu
from Qt.QtGui import QCursor

from tpDcc import dcc
from tpDcc.managers import resources
from tpDcc.libs.python import decorators
from tpDcc.libs.qt.core import base
from tpDcc.libs.qt.widgets import layouts, label, group, buttons, formwidget, dividers
from tpDcc.libs.datalibrary.core import version as data_version

from tpDcc.tools.datalibrary.data import base as base_data
from tpDcc.tools.datalibrary.widgets import sequence, version

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class _MetaLoadWidget(type):

    def __call__(self, *args, **kwargs):
        as_class = kwargs.get('as_class', False)
        if dcc.client().is_maya():
            from tpDcc.tools.datalibrary.dccs.maya.widgets import load
            if as_class:
                return load.MayaLoadWidget
            else:
                return type.__call__(load.MayaLoadWidget, *args, **kwargs)
        else:
            if as_class:
                return BaseLoadWidget
            else:
                return type.__call__(BaseLoadWidget, *args, **kwargs)


class BaseLoadWidget(base.BaseWidget, object):
    def __init__(self, item_view, client=None, parent=None):

        self._item_view = item_view
        self._client = client
        self._form_widget = None
        self._sequence_widget = None

        super(BaseLoadWidget, self).__init__(parent=parent)

        self.setObjectName('LoadWidget')

        try:
            self.form_widget().validate()

        except NameError as error:
            LOGGER.exception(error)

        self.update_thumbnail_size()

        item = self.item()
        if item:
            self._accept_button.setVisible(bool(item.functionality().get('load', False)))
            self._update_version_info()

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def get_main_layout(self):
        return layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))

    def ui(self):
        super(BaseLoadWidget, self).ui()

        self.setWindowTitle('Load Item')

        title_frame = QFrame(self)
        title_frame_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        title_frame.setLayout(title_frame_layout)
        title_widget = QFrame(self)
        title_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        title_widget.setLayout(title_layout)
        title_buttons_layout = layouts.HorizontalLayout(spacing=0, margins=(0, 0, 0, 0))
        title_layout.addLayout(title_buttons_layout)
        title_icon = label.BaseLabel(parent=self)
        title_button = label.BaseLabel(self.item().label(), parent=self)
        title_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._menu_button = buttons.BaseButton(parent=self)
        self._menu_button.setIcon(resources.icon('menu_dots'))
        title_buttons_layout.addWidget(title_icon)
        title_buttons_layout.addWidget(title_button)
        title_buttons_layout.addWidget(self._menu_button)
        title_frame_layout.addWidget(title_widget)

        item_icon_name = self.item().icon() or 'tpDcc'
        item_icon = resources.icon(item_icon_name)
        if not item_icon:
            item_icon = resources.icon('tpDcc')
        title_icon.setPixmap(item_icon.pixmap(QSize(20, 20)))

        main_frame = QFrame(self)
        main_frame_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        main_frame.setLayout(main_frame_layout)
        icon_frame = QFrame(self)
        icon_frame_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        icon_frame.setLayout(icon_frame_layout)
        icon_title_frame = QFrame(self)
        icon_title_frame_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        icon_frame_layout.addWidget(icon_title_frame)
        icon_title_frame.setLayout(icon_title_frame_layout)
        icon_frame2 = QFrame(self)
        icon_frame2_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        icon_frame2.setLayout(icon_frame2_layout)
        thumbnail_layout = layouts.HorizontalLayout(spacing=0, margins=(0, 0, 0, 0))
        self._thumbnail_frame = QFrame(self)
        thumbnail_frame_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        self._thumbnail_frame.setLayout(thumbnail_frame_layout)
        icon_frame_layout.addWidget(icon_frame2)
        icon_frame2_layout.addLayout(thumbnail_layout)
        thumbnail_layout.addWidget(self._thumbnail_frame)
        form_frame = QFrame(self)
        form_frame_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        form_frame.setLayout(form_frame_layout)
        main_frame_layout.addWidget(icon_frame)
        main_frame_layout.addWidget(form_frame)

        version_frame = QFrame(self)
        version_frame_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        version_frame.setLayout(version_frame_layout)
        self._versions_widget = version.VersionHistoryWidget(parent=self)
        version_frame_layout.addWidget(self._versions_widget)

        self._custom_widget_frame = QFrame(self)
        custom_widget_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        self._custom_widget_frame.setLayout(custom_widget_layout)

        self._preview_buttons_frame = QFrame(self)
        preview_buttons_layout = layouts.HorizontalLayout(spacing=2, margins=(0, 0, 0, 0))
        self._preview_buttons_frame.setLayout(preview_buttons_layout)
        self._accept_button = buttons.BaseButton('Load', parent=self)
        self._accept_button.setIcon(resources.icon('open'))
        preview_buttons_layout.addStretch()
        preview_buttons_layout.addWidget(self._accept_button)
        preview_buttons_layout.addStretch()

        self._export_btn = buttons.BaseButton('Export', parent=self)
        self._export_btn.setIcon(resources.icon('export'))
        self._import_btn = buttons.BaseButton('Import', parent=self)
        self._import_btn.setIcon(resources.icon('import'))
        self._reference_btn = buttons.BaseButton('Reference', parent=self)
        self._reference_btn.setIcon(resources.icon('reference'))
        for btn in [self._export_btn, self._import_btn, self._reference_btn]:
            btn.setToolTip(btn.text())
        extra_buttons_frame = QFrame(self)
        extra_buttons_layout = layouts.HorizontalLayout(spacing=2, margins=(0, 0, 0, 0))
        extra_buttons_frame.setLayout(extra_buttons_layout)
        extra_buttons_layout.addWidget(self._export_btn)
        extra_buttons_layout.addWidget(self._import_btn)
        extra_buttons_layout.addWidget(self._reference_btn)

        group_box = group.GroupBoxWidget('Icon', icon_frame)
        group_box.set_persistent(True)
        group_box.set_checked(True)

        self._version_box = group.GroupBoxWidget('Version', version_frame)
        self._version_box.set_persistent(True)
        self._version_box.set_checked(True)

        self._sequence_widget = sequence.ImageSequenceWidget(self)
        thumbnail_frame_layout.insertWidget(0, self._sequence_widget)

        if os.path.exists(self._item_view.image_sequence_path()):
            self._sequence_widget.set_path(self._item_view.image_sequence_path())
        elif os.path.exists(self._item_view.thumbnail_path()):
            self._sequence_widget.set_path(self._item_view.thumbnail_path())

        self._form_widget = formwidget.FormWidget(self)
        self._form_widget.set_schema(self.item().load_schema())
        self._form_widget.set_validator(self.item().load_validator)
        form_frame_layout.addWidget(self._form_widget)

        self.main_layout.addWidget(title_frame)
        self.main_layout.addWidget(group_box)
        self.main_layout.addWidget(main_frame)
        self.main_layout.addWidget(self._version_box)
        self.main_layout.addWidget(version_frame)
        self.main_layout.addWidget(self._custom_widget_frame)
        self.main_layout.addStretch()
        self.main_layout.addWidget(dividers.Divider())
        self.main_layout.addWidget(self._preview_buttons_frame)
        self.main_layout.addWidget(extra_buttons_frame)

    def setup_signals(self):
        self._menu_button.clicked.connect(self._on_show_menu)
        self._accept_button.clicked.connect(self._on_load)
        self._export_btn.clicked.connect(self._on_export)
        self._import_btn.clicked.connect(self._on_import)
        self._reference_btn.clicked.connect(self._on_reference)
        self._item_view.loadValueChanged.connect(self._on_item_value_changed)

    def resizeEvent(self, event):
        """
        Overrides base QWidget resizeEvent function
        :param event: QResizeEvent
        """

        self.update_thumbnail_size()

    def close(self):
        """
        Overrides base QWidget close function to disable script job when its is done
        """

        if self.form_widget():
            self.form_widget().save_persistent_values()

        super(BaseLoadWidget, self).close()

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def item(self):
        """
        Returns the library item to load
        :return:
        """

        return self._item_view.item

    def item_view(self):
        """
        Returns the library item view to load
        :return: LibraryItem
        """

        return self._item_view

    def form_widget(self):
        """
        Returns form widget instance
        :return: FormWidget
        """

        return self._form_widget

    def set_custom_widget(self, widget):
        """
        Sets custom widget to use when loading items
        :param widget: QQWidget
        """

        self._custom_widget_frame.layout().addWidget(widget)

    def update_thumbnail_size(self):
        """
        Updates the thumbnail button to teh size of the widget
        """

        width = self.width() - 10
        if width > 250:
            width = 250
        size = QSize(width, width)
        self._sequence_widget.setIconSize(size)
        self._sequence_widget.setMaximumSize(size)
        self._thumbnail_frame.setMaximumSize(size)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _update_version_info(self):
        item_view = self.item_view()
        if not item_view or not item_view.library_window():
            return

        library_window = item_view.library_window()
        if not library_window:
            return

        repository_type = library_window.get_repository_type()
        repository_path = library_window.get_repository_path()
        if not repository_type or not repository_path:
            return

        try:
            repository_type = int(repository_type)
        except Exception:
            repository_type = 0

        if repository_type == 0:
            repository_type = None
        elif repository_type == 1:
            repository_type = data_version.GitVersionControl

        self._versions_widget.set_version_control_class(repository_type)
        self._versions_widget.set_repository_path(repository_path)

        # If not valid version control is defined, we hide version control
        valid_version_control = self._versions_widget.set_directory(self.item().format_identifier())
        self._versions_widget.setVisible(valid_version_control)
        self._version_box.setVisible(valid_version_control)

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_show_menu(self):
        """
        Internal callback function that is called when menu button is clicked byu the user
        :return: QAction
        """

        menu = QMenu(self)
        self._item_view.context_edit_menu(menu)
        point = QCursor.pos()
        point.setX(point.x() + 3)
        point.setY(point.y() + 3)

        return menu.exec_(point)

    def _on_load(self):
        """
        Internal callback function that is called when Load button is pressed by the user
        """

        load_function = self.item().functionality().get('load')
        if not load_function:
            LOGGER.warning('Load functionality is not available for data: "{}"'.format(self.item()))
            return

        library_path = self.item().library.identifier
        if not library_path or not os.path.isfile(library_path):
            LOGGER.warning('Impossible to load data "{}" because its library does not exists: "{}"'.format(
                self.item(), library_path))
            return

        if self._client:
            self._client().load_data(library_path=library_path, data_path=self.item().format_identifier())
        else:
            load_function()

    def _on_export(self):
        """
        Internal callback function that is called when export button is pressed by the user
        """

        item = self.item()
        if not item:
            return

        library_window = self.item_view().library_window()
        if not library_window:
            return

        base_data.BaseDataItemView.show_export_widget(item.__class__, item.format_identifier(), library_window)

    def _on_import(self):
        """
        Internal callback function that is called when import button is pressed by the user
        """

        import_function = self.item().functionality().get('import_data')
        if not import_function:
            LOGGER.warning('Import functionality is not available for data: "{}"'.format(self.item()))
            return

        library_path = self.item().library.identifier
        if not library_path or not os.path.isfile(library_path):
            LOGGER.warning('Impossible to load data "{}" because its library does not exists: "{}"'.format(
                self.item(), library_path))
            return

        if self._client:
            self._client().import_data(library_path=library_path, data_path=self.item().format_identifier())
        else:
            import_function()

    def _on_reference(self):
        """
        Internal callback function that is called when reference button is pressed by the user
        """

        reference_function = self.item().functionality().get('reference_data')
        if not reference_function:
            LOGGER.warning('Reference functionality is not available for data: "{}"'.format(self.item()))
            return

        library_path = self.item().library.identifier
        if not library_path or not os.path.isfile(library_path):
            LOGGER.warning('Impossible to load data "{}" because its library does not exists: "{}"'.format(
                self.item(), library_path))
            return

        if self._client:
            self._client().reference_data(library_path=library_path, data_path=self.item().format_identifier())
        else:
            reference_function()

    def _on_item_value_changed(self, field, value):
        """
        Internal callback function that is called each time an item field value changes
        :param field: str
        :param value: object
        """

        self._form_widget.set_value(field, value)


@decorators.add_metaclass(_MetaLoadWidget)
class LoadWidget(object):
    pass
