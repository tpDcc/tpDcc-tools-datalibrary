#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base export widget for data items
"""

from __future__ import print_function, division, absolute_import

import os
import logging
import traceback

from Qt.QtWidgets import QSizePolicy

from tpDcc.managers import resources
from tpDcc.libs.python import decorators
from tpDcc.libs.qt.widgets import layouts, buttons, formwidget, messagebox

from tpDcc.tools.datalibrary.widgets import save

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class _MetaExportWidget(type):
    def __call__(self, *args, **kwargs):
        as_class = kwargs.get('as_class', False)
        if as_class:
            return BaseExportWidget
        else:
            return type.__call__(BaseExportWidget, *args, **kwargs)


class BaseExportWidget(save.SaveWidget(as_class=True)):

    ENABLE_THUMBNAIL_CAPTURE = False

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def get_main_layout(self):
        return layouts.VerticalLayout(spacing=4, margins=(0, 0, 0, 0))

    def ui(self):
        super(BaseExportWidget, self).ui()

        self.setWindowTitle('Export Item')

        self._export_button = buttons.BaseButton('Export', parent=self)
        self._export_button.setIcon(resources.icon('export'))
        self._preview_buttons_layout.insertWidget(1, self._export_button)

        self._save_button.setVisible(False)
        self._thumbnail_frame.setVisible(False)

    def setup_signals(self):
        super(BaseExportWidget, self).setup_signals()

        self._export_button.clicked.connect(self._on_export)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def set_item_view(self, item_view):
        """
        Sets the base item to be created
        :param item_view: LibraryItem
        """

        self._item_view = item_view

        schema = self.item().export_schema()
        if schema:
            form_widget = formwidget.FormWidget(self)
            form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            form_widget.set_schema(schema)
            form_widget.set_validator(self.item().save_validator)
            item_name = os.path.basename(self.item().format_identifier())
            item_folder = os.path.dirname(self.item().format_identifier())
            form_widget.set_values({'name': item_name, 'folder': item_folder})
            self._options_frame.layout().addWidget(form_widget)
            form_widget.validate()
            self._form_widget = form_widget
        else:
            self._options_frame.setVisible(False)

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_export(self):
        if not self.library_window():
            return False

        library = self.library_window().library()
        if not library:
            return False

        try:
            self.form_widget().validate()
            if self.form_widget().has_errors():
                raise Exception('\n'.join(self.form_widget().errors()))
            name = self.form_widget().value('name')
            folder = self.form_widget().value('folder')
            comment = self.form_widget().value('comment') or ''

            extension = self.item().extension()
            if extension and not name.endswith(extension):
                name = '{}{}'.format(name, extension)

            path = folder + '/' + name

            export_item = library.get(path, only_extension=True)
            export_function = export_item.functionality().get('export_data')
            if not export_function:
                LOGGER.warning('Item "{}" does not supports export operation'.format(export_item))
                return False

            library_path = self.item().library.identifier
            if not library_path or not os.path.isfile(library_path):
                LOGGER.warning('Impossible to save data "{}" because its library does not exists: "{}"'.format(
                    self.item(), library_path))
                return

            values = self.form_widget().values()
            try:
                if self._client:
                    _, _, dependencies = self._client().export_data(
                        library_path=library_path, data_path=path, values=values)
                else:
                    dependencies = export_function(**values)
            except Exception as exc:
                messagebox.MessageBox.critical(self.library_window(), 'Error while exporting', str(exc))
                LOGGER.error(traceback.format_exc())
                return False

        except Exception as exc:
            messagebox.MessageBox.critical(self.library_window(), 'Error while exporting', str(exc))
            LOGGER.error(traceback.format_exc())
            raise

        item_path = export_item.format_identifier()
        if not item_path or not os.path.isfile(item_path):
            LOGGER.warning('Although exporting process for item "{}" was completed, '
                           'it seems data was not exported successfully!'.format(export_item))
            self.saved.emit()
            return False

        # # TODO: Instead of creating a local version, we will use a git system to upload our data to our project repo
        # valid = export_item.create_version(comment=comment)
        # if not valid:
        #     LOGGER.warning('Impossible to store new version for data "{}"'.format(export_item))

        self.library_window().sync()

        if dependencies:
            export_item.update_dependencies(dependencies=dependencies)

        self.saved.emit()

        return True


@decorators.add_metaclass(_MetaExportWidget)
class ExportWidget(object):
    pass
