#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains search data library widget implementation
"""

from __future__ import print_function, division, absolute_import

import logging
from functools import partial

from Qt.QtCore import Qt, Signal, QSize
from Qt.QtWidgets import QStyle, QLineEdit, QMenu, QAction
from Qt.QtGui import QCursor

from tpDcc.managers import resources
from tpDcc.libs.qt.widgets import buttons

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class DataSearcherWidget(QLineEdit):

    SPACE_OPEARTOR = 'and'
    PLACEHOLDER_TEXT = 'Search'

    searchChanged = Signal()

    def __init__(self, parent=None):
        super(DataSearcherWidget, self).__init__(parent=parent)

        self._library = None
        self._space_operator = 'and'

        self._icon_btn = buttons.BaseButton(parent=self)
        self._icon_btn.setIcon(resources.icon('search'))
        self._icon_btn.setObjectName('searchButton')
        self._icon_btn.setIconSize(QSize(12, 12))
        self._icon_btn.clicked.connect(self._on_icon_clicked)
        self._clear_btn = buttons.BaseButton(parent=self)
        self._clear_btn.setIcon(resources.icon('delete'))
        self._clear_btn.setObjectName('clearButton')
        self._clear_btn.setIconSize(QSize(12, 12))
        self._clear_btn.setCursor(Qt.ArrowCursor)
        self._clear_btn.setToolTip('Clear all search text')
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        self.setPlaceholderText(self.PLACEHOLDER_TEXT)
        self.textChanged.connect(self._on_text_changed)
        self.update()

        tip = 'Search all current items.'
        self.setToolTip(tip)
        self.setStatusTip(tip)

        self._icon_btn.setStyleSheet('background-color: transparent')
        self._clear_btn.setStyleSheet('background-color: transparent')
        # self.setStyleSheet('border-radius: 13px; border: 2px;')

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def update(self):
        """
        Overrides base QLineEdit update function
        """

        self.update_clear_button()

    def resizeEvent(self, event):
        """
        Overrides base QLineEdit resizeEvent function
        :param event: QResizeEvent
        """

        super(DataSearcherWidget, self).resizeEvent(event)

        self.setTextMargins(self.height(), 0, 0, 0)
        size = QSize(self.height(), self.height())
        self._icon_btn.setIconSize(size)
        self._icon_btn.setFixedSize(size)
        self._clear_btn.setIconSize(size)
        x = self.width() - self.height()
        self._clear_btn.setGeometry(x, 0, self.height(), self.height())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.clear()
        super(DataSearcherWidget, self).keyPressEvent(event)

    def contextMenuEvent(self, event):
        self.show_context_menu()

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def library(self):
        """
        Returns the library model for the menu
        :return: Library
        """

        return self._library

    def set_library(self, library):
        """
        Set the library model for the menu
        :param library: Library
        """

        self._library = library

    def space_operator(self):
        """
        Returns the space operator for the search widget
        :return: str
        """

        return self._space_operator

    def set_space_operator(self, space_operator):
        """
        Sets the space operator
        :param space_operator: str
        """

        self._space_operator = space_operator
        self.search()

    def search(self):
        """
        Run the search query on the library
        """

        if self.library():
            self.library().add_query(self.query())
            self.library().search()
        else:
            LOGGER.info('No library found for the search widget')

        self.update_clear_button()
        self.searchChanged.emit()

    def query(self):
        """
        Returns the query used for the library
        :return: dict
        """

        text = str(self.text())
        filters = list()
        for filter_ in text.split(' '):
            if filter_.split():
                filters.append(('identifier', 'contains', filter_))
        unique_name = 'searchWidget' + str(id(self))

        return {'name': unique_name, 'operator': self.space_operator(), 'filters': filters}

    def update_clear_button(self):
        """
        Updates the clear button depending on the current text
        """

        text = self.text()
        if text:
            self._clear_btn.show()
        else:
            self._clear_btn.hide()

    # ============================================================================================================
    # MENU
    # ============================================================================================================

    def show_context_menu(self):
        """
        Creates and shows the context menu for the search widget
        :return: QAction
        """

        menu = QMenu(self)
        standard_menu = self.createStandardContextMenu()
        standard_menu.setTitle('Edit')
        menu.addMenu(standard_menu)

        sub_menu = QMenu(menu)
        sub_menu.setTitle('Space Operator')
        menu.addMenu(sub_menu)

        or_action = QAction('OR', menu)
        or_action.setCheckable(True)
        or_callback = partial(self.set_space_operator, 'or')
        or_action.triggered.connect(or_callback)
        if self.space_operator() == 'or':
            or_action.setChecked(True)
        sub_menu.addAction(or_action)

        and_action = QAction('AND', menu)
        and_action.setCheckable(True)
        and_callback = partial(self.set_space_operator, 'and')
        and_action.triggered.connect(and_callback)
        if self.space_operator() == 'and':
            and_action.setChecked(True)
        sub_menu.addAction(and_action)

        action = menu.exec_(QCursor.pos())

        return action

        # ============================================================================================================
    # SETTINGS
    # ============================================================================================================

    def settings(self):
        """
        Returns a dictionary of the current widget state
        :return: dict
        """

        settings = {
            'text': self.text(),
            'spaceOperator': self.space_operator()
        }

        return settings

    def set_settings(self, settings):
        """
        Restore the widget state from a settings dictonary
        :param settings: dict
        """

        text = settings.get('text', '')
        self.setText(text)
        space_operator = settings.get('spaceOperator')
        if space_operator:
            self.set_space_operator(space_operator)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _search_line_frame_width(self):
        return self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)

    def _clear_button_padded_width(self):
        return self._clear_btn.width() + self._search_line_frame_width() * 2

    def _clear_button_padded_height(self):
        return self._clear_btn.height() + self._search_line_frame_width() * 2

    def _search_button_padded_width(self):
        return self._icon_btn.width() + self._search_line_frame_width() * 2

    def _search_button_padded_height(self):
        return self._icon_btn.height() + self._search_line_frame_width() * 2

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_icon_clicked(self):
        """
        Internal callback function that is triggered when the user clcks on the search icon
        """

        if not self.hasFocus():
            self.setFocus()

    def _on_clear_clicked(self):
        """
        Internal callback function that is triggered when the user clicks the cross icon
        """

        self.setText('')
        self.setFocus()

    def _on_text_changed(self):
        """
        Internal callback function that is triggered when the text changes
        """

        self.search()
