#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains history version widget for tpDcc-tools-datalibrary
"""

from __future__ import print_function, division, absolute_import

import os

from Qt.QtCore import Qt
from Qt.QtWidgets import QSizePolicy, QTreeWidgetItem, QMessageBox

from tpDcc.managers import resources
from tpDcc.libs.qt.core import qtutils, base
from tpDcc.libs.qt.widgets import layouts, buttons, treewidgets


class VersionHistoryTreeWidget(treewidgets.TreeWidget):

    HEADER_LABELS = ['Version', 'Comment', 'User', 'Date', 'Commit']

    def __init__(self, parent=None):
        super(VersionHistoryTreeWidget, self).__init__(parent=parent)

        self.setHeaderLabels(self.HEADER_LABELS)

        if qtutils.is_pyside() or qtutils.is_pyside2():
            self.sortByColumn(0, Qt.SortOrder.DescendingOrder)

        self.setColumnWidth(0, 70)
        self.setColumnWidth(1, 200)
        self.setColumnWidth(2, 70)
        self.setColumnWidth(3, 70)
        self.setColumnWidth(4, 70)
        self._padding = 1

    def update_versions_from_commits_data(self, commits_data, current_commit_data=None):
        self.clear()
        if not commits_data:
            return

        # https://stackoverflow.com/questions/42896141/how-to-lazily-iterate-on-reverse-order-of-keys-in-ordereddict/42896182#42896182
        for i, (commit, commit_data) in enumerate(
                ((commit, commits_data[commit]) for commit in reversed(commits_data))):
            item = QTreeWidgetItem()
            item.setText(0, str(i + 1))
            item.setText(1, commit_data.get('message', ''))
            item.setText(2, commit_data.get('author', ''))
            item.setText(3, commit_data.get('date', ''))
            item.setText(4, commit)
            self.addTopLevelItem(item)

            if current_commit_data:
                for current_commit in list(current_commit_data.keys()):
                    if current_commit == commit:
                        item.setBackgroundColor(0, Qt.green)


class VersionHistoryWidget(base.DirectoryWidget):
    def __init__(self, parent=None):
        super(VersionHistoryWidget, self).__init__(parent=parent)

        self._repository_path = None
        self._repository_type_class = None

    def ui(self):
        super(VersionHistoryWidget, self).ui()

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self._btn_layout = layouts.HorizontalLayout()
        self._sync_btn = buttons.BaseButton('Sync', parent=self)
        self._sync_btn.setIcon(resources.icon('sync'))
        self._sync_btn.setMaximumWidth(100)
        self._sync_btn.setEnabled(False)
        self._btn_layout.addWidget(self._sync_btn)
        self._versions_tree = VersionHistoryTreeWidget(parent=self)
        self.main_layout.addWidget(self._versions_tree)
        self.main_layout.addLayout(self._btn_layout)

    def setup_signals(self):
        self._sync_btn.clicked.connect(self.sync_version)
        self._versions_tree.itemSelectionChanged.connect(self._on_update_selection)

    def set_directory(self, directory):
        super(VersionHistoryWidget, self).set_directory(directory)
        return self.refresh_versions()

    def set_repository_path(self, repository_path, refresh=False):
        self._repository_path = repository_path
        if refresh:
            return self.refresh_versions()

        return True

    def set_version_control_class(self, version_control_class, refresh=False):
        self._repository_type_class = version_control_class
        if refresh:
            return self.refresh_versions()

        return True

    def refresh_versions(self):
        self._versions_tree.clear()
        if not self._repository_type_class or not self._repository_path or not self.directory or not os.path.isdir(
                self._repository_path) or not os.path.isfile(self.directory):
            return False

        if not self._repository_type_class.is_valid_repository_directory(self._repository_path):
            return False

        commits_data = self._repository_type_class.get_commits_that_modified_a_file(
            self._repository_path, self.directory)
        if not commits_data:
            return False

        self._versions_tree.update_versions_from_commits_data(commits_data)

        return True

    def sync_version(self):
        """
        Opens selected version
        Override functionality for specific data
        """

        if not self._repository_type_class:
            return

        items = self._versions_tree.selectedItems()
        if not items:
            return
        item = items[0]

        item_commit = item.text(4)
        if not item_commit:
            return

        res = qtutils.show_question(
            self, 'Syncing File', 'Are you sure you want to synchronize this file?.'
                                  '\nCurrent local file will be overwriten!')
        if res != QMessageBox.Yes:
            return

        self._repository_type_class.sync_file(self._repository_path, self.directory, item_commit)

        # TODO: Dependencies should be checked (by checkding DB) and also, should be updated to commit
        # if that dependency was edited in the commit

    # =================================================================================================================
    # CALLBACKS
    # =================================================================================================================

    def _on_update_selection(self):
        items = self._versions_tree.selectedItems()
        if not items:
            self._sync_btn.setEnabled(False)
        else:
            self._sync_btn.setEnabled(True)
