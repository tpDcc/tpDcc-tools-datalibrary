#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains data library filter menu widget implementation
"""

from __future__ import print_function, division, absolute_import

from functools import partial

from Qt.QtCore import Qt
from Qt.QtWidgets import QFrame, QMenu, QWidgetAction
from Qt.QtGui import QCursor

from tpDcc.libs.qt.core import qtutils
from tpDcc.libs.qt.widgets import layouts, label, checkbox, action


class SortByMenu(QMenu):
    def __init__(self, *args, **kwargs):
        super(SortByMenu, self).__init__(*args, **kwargs)

        self._library = None

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def set_library(self, library):
        self._library = library


class GroupByMenu(QMenu):
    def __init__(self, *args, **kwargs):
        super(GroupByMenu, self).__init__(*args, **kwargs)

        self._library = None

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def set_library(self, library):
        self._library = library


class FilterByMenu(QMenu):
    def __init__(self, *args, **kwargs):
        super(FilterByMenu, self).__init__(*args, **kwargs)

        self._library = None
        self._facets = list()
        self._options = {'field': 'type'}
        self._settings = dict()

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def show(self, point=None):
        """
        Overrides base QMeu show function to allow to show it in a specific position
        :param point: QPoint or None
        """

        self.clear()

        field = self._options.get('field')
        queries = self.library().queries(exclude=self.name())
        self._facets = self.library().distinct(field, queries=queries)

        show_action = action.SeparatorAction('Show {}'.format(field.title()), self)
        self.addAction(show_action)

        show_all_action = action.LabelAction('Show All', self)
        self.addAction(show_all_action)
        show_all_action.setEnabled(not self.is_show_all_enabled())
        show_all_callback = partial(self._on_show_all_action_clicked)
        show_all_action.triggered.connect(show_all_callback)

        self.addSeparator()

        for facet in self._facets:
            name = facet.get('name', '')
            checked = self.settings().get(name, True)
            filter_by_action = FilterByAction(self)
            filter_by_action.set_facet(facet)
            filter_by_action.setChecked(checked)
            self.addAction(filter_by_action)
            callback = partial(self._on_action_checked, name, not checked)
            filter_by_action.triggered.connect(callback)

        point = point or QCursor.pos()

        self.exec_(point)

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

        if library == self._library:
            return

        if not library and self._library:
            try:
                qtutils.safe_disconnect_signal(self._library.searchStarted)
            except Exception as exc:
                pass

        self._library = library

        if self._library:
            self._library.searchStarted.connect(self._on_search_init)

    def name(self):
        """
        Returns the name of the fulter used by the library
        """

        return self._options.get('field') + 'FilterMenu'

    def is_active(self):
        """
        Returns whether are any filters currently active using the settings
        :return: bool
        """

        settings = self.settings()
        for name in settings:
            if not settings.get(name):
                return True

        return False

    def is_show_all_enabled(self):
        """
        Returns whether all current filters are enabled or not
        :return: bool
        """

        for facet in self._facets:
            if not self._settings.get(facet.get('name'), True):
                return False

        return True

    def set_all_enabled(self, enabled):
        """
        Set all the filters enabled
        :param enabled: bool
        """

        for facet in self._facets:
            self._settings[facet.get('name')] = enabled

    def set_options(self, options):
        """
        Sets the options to be used by the filters menu
        :param options: dict
        """

        self._options = options

    def settings(self):
        """
        Returns the settings for the filter menu
        :return: dict
        """

        return self._settings

    def set_settings(self, settings):
        """
        Set the settings for the filter menu
        :param settings: dict
        """

        self._settings = settings

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_search_init(self):
        """
        Internal callback function that is called before each search to update the filter men query
        """

        library = self.library()
        if not library:
            return

        filters = list()

        settings = self.settings()
        field = self._options.get('field')
        for name in settings:
            checked = settings.get(name, True)
            if not checked:
                filters.append((field, 'not', name))

        query = {
            'name': self.name(),
            'operator': 'and',
            'filters': filters
        }

        self.library().add_query(query)

    def _on_show_all_action_clicked(self):
        """
        Internal callback function that is triggered when the user clicks the show all action
        """

        self.set_all_enabled(True)
        self.library().search()

    def _on_action_checked(self, name, checked):
        """
        Internal callback function triggered when an action has been clicked
        :param name: str
        :param checked: bool
        """

        if qtutils.is_control_modifier():
            self.set_all_enabled(False)
            self._settings[name] = True
        else:
            self._settings[name] = checked

        self.library().search()


class FilterByAction(QWidgetAction, object):
    def __init__(self, parent=None):
        super(FilterByAction, self).__init__(parent)

        self._facet = None
        self._checked = False

    def setChecked(self, checked):
        """
        Overrides base QWidgetAction setChecked function
        :param checked: bool
        """

        self._checked = checked

    def set_facet(self, facet):
        """
        Sets action facet
        :param facet:
        """

        self._facet = facet

    def createWidget(self, menu):
        """
        Overrides base QWidgetAction createWidget function
        :param menu: QMenu
        :return: QWidget
        """

        widget = QFrame(self.parent())
        widget.setObjectName('filterByAction')
        facet = self._facet
        name = facet.get('name', '')
        count = str(facet.get('count', 0))
        title = name.replace('.', '').title()
        cbx = checkbox.BaseCheckBox(parent=widget)
        cbx.setAttribute(Qt.WA_TransparentForMouseEvents)
        cbx.setText(title)
        cbx.installEventFilter(self)
        cbx.setChecked(self._checked)
        label2 = label.BaseLabel(parent=widget)
        label2.setObjectName('actionCounter')
        label2.setText(count)
        layout = layouts.HorizontalLayout(spacing=0, margins=(0, 0, 0, 0))
        layout.addWidget(cbx, stretch=1)
        layout.addWidget(label2)
        widget.setLayout(layout)

        cbx.toggled.connect(self._on_triggered)

        return widget

    def _on_triggered(self, checked=None):
        """
        Triggered when teh checkbox value has changed
        :param checked: bool
        """

        self.triggered.emit()
        self.parent().close()
