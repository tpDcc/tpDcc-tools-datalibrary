#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base save widget for data items
"""

from __future__ import print_function, division, absolute_import

import os
import logging
import traceback

from Qt.QtCore import Signal, QSize
from Qt.QtWidgets import QSizePolicy, QFrame, QDialogButtonBox, QFileDialog

from tpDcc import dcc
from tpDcc.managers import resources
from tpDcc.libs.resources.core import theme
from tpDcc.libs.python import decorators
from tpDcc.libs.qt.core import base, qtutils
from tpDcc.libs.qt.widgets import layouts, label, buttons, formwidget, messagebox, snapshot

from tpDcc.tools.datalibrary.core import utils
from tpDcc.tools.datalibrary.widgets import sequence

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class _MetaSaveWidget(type):

    def __call__(self, *args, **kwargs):
        as_class = kwargs.get('as_class', False)
        if dcc.client().is_maya():
            from tpDcc.tools.datalibrary.dccs.maya.widgets import save
            if as_class:
                return save.MayaSaveWidget
            else:
                return type.__call__(save.MayaSaveWidget, *args, **kwargs)
        else:
            if as_class:
                return BaseSaveWidget
            else:
                return type.__call__(BaseSaveWidget, *args, **kwargs)


@theme.mixin
class BaseSaveWidget(base.BaseWidget, object):

    cancelled = Signal()
    saved = Signal()

    ENABLE_THUMBNAIL_CAPTURE = True

    def __init__(self, item_view, client=None, *args, **kwargs):

        self._item_view = item_view
        self._client = client
        self._form_widget = None
        self._sequence_widget = None

        super(BaseSaveWidget, self).__init__(*args, **kwargs)

        self.setObjectName('LibrarySaveWidget')

        self._create_sequence_widget()
        self.update_thumbnail_size()
        self.set_item_view(item_view)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def get_main_layout(self):
        return layouts.VerticalLayout(spacing=4, margins=(0, 0, 0, 0))

    def ui(self):
        super(BaseSaveWidget, self).ui()

        self.setWindowTitle('Save Item')

        title_frame = QFrame(self)
        title_frame_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        title_frame.setLayout(title_frame_layout)
        title_widget = QFrame(self)
        title_layout = layouts.VerticalLayout(spacing=0, margins=(0, 0, 0, 0))
        title_widget.setLayout(title_layout)
        title_buttons_layout = layouts.HorizontalLayout(spacing=0, margins=(0, 0, 0, 0))
        title_layout.addLayout(title_buttons_layout)
        title_icon = label.BaseLabel(parent=self)
        title_button = label.BaseLabel(self.item().menu_name(), parent=self)
        title_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._menu_button = buttons.BaseButton(parent=self)
        self._menu_button.setIcon(resources.icon('menu_dots'))
        self._menu_button.setVisible(False)     # Hide by default
        title_buttons_layout.addWidget(title_icon)
        title_buttons_layout.addSpacing(5)
        title_buttons_layout.addWidget(title_button)
        title_buttons_layout.addWidget(self._menu_button)
        title_frame_layout.addWidget(title_widget)

        item_icon_name = self.item().icon() or 'tpDcc'
        item_icon = resources.icon(item_icon_name)
        if not item_icon:
            item_icon = resources.icon('tpDcc')
        title_icon.setPixmap(item_icon.pixmap(QSize(20, 20)))

        thumbnail_layout = layouts.HorizontalLayout(spacing=0, margins=(0, 0, 0, 0))
        self._thumbnail_frame = QFrame(self)
        thumbnail_frame_layout = layouts.VerticalLayout(spacing=0, margins=(0, 2, 0, 2))
        self._thumbnail_frame.setLayout(thumbnail_frame_layout)
        thumbnail_layout.addWidget(self._thumbnail_frame)

        self._options_frame = QFrame(self)
        options_frame_layout = layouts.VerticalLayout(spacing=0, margins=(4, 2, 4, 2))
        self._options_frame.setLayout(options_frame_layout)

        preview_buttons_frame = QFrame(self)
        self._preview_buttons_layout = layouts.HorizontalLayout(spacing=0, margins=(4, 2, 4, 2))
        preview_buttons_frame.setLayout(self._preview_buttons_layout)
        self._save_button = buttons.BaseButton('Save', parent=self)
        self._save_button.setIcon(resources.icon('save'))
        self._cancel_button = buttons.BaseButton('Cancel', parent=self)
        self._cancel_button.setIcon(resources.icon('cancel'))
        self._preview_buttons_layout.addStretch()
        self._preview_buttons_layout.addWidget(self._save_button)
        self._preview_buttons_layout.addStretch()
        self._preview_buttons_layout.addWidget(self._cancel_button)
        self._preview_buttons_layout.addStretch()

        self.main_layout.addWidget(title_frame)
        self.main_layout.addLayout(thumbnail_layout)
        self.main_layout.addWidget(self._options_frame)
        self.main_layout.addWidget(preview_buttons_frame)

    def setup_signals(self):
        self._menu_button.clicked.connect(self._on_show_menu)
        self._save_button.clicked.connect(self._on_save)
        self._cancel_button.clicked.connect(self._on_cancel)

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

        if self._form_widget:
            self._form_widget.save_persistent_values()

        super(BaseSaveWidget, self).close()

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def folder_path(self):
        """
        Returns the folder path
        :return: str
        """

        return self.form_widget().value('folder')

    def set_folder_path(self, path):
        """
        Sets the destination folder path
        :param path: str
        """

        self.form_widget().set_value('folder', path)

    def set_thumbnail_path(self, path):
        """
        Sets the path to the thumbnail image or the image sequence directory
        :param path: str
        """

        file_name, extension = os.path.splitext(path)
        target = utils.temp_path('thumbnail{}'.format(extension))
        utils.copy_path(path, target, force=True)

        self._sequence_widget.set_path(target)

    def library_window(self):
        """
        Returns library widget window for the item
        :return: LibraryWindow
        """

        return self.item_view().library_window()

    def set_library_window(self, library_window):
        """
        Sets the library widget for the item
        :param library_window: LibraryWindow
        """

        self.item_view().set_library_window(library_window)

    def form_widget(self):
        """
        Returns the form widget instance
        :return: FormWidget
        """

        return self._form_widget

    def item(self):
        """
        Returns current item
        :return:
        """

        return self.item_view().item

    def item_view(self):
        """
        Returns the current item view
        :return: LibraryItem
        """

        return self._item_view

    def set_item_view(self, item_view):
        """
        Sets the base item to be created
        :param item_view: LibraryItem
        """

        self._item_view = item_view

        if os.path.exists(item_view.image_sequence_path()):
            self.set_thumbnail_path(item_view.image_sequence_path())
        elif not item_view.is_default_thumbnail_path():
            self.set_thumbnail_path(item_view.thumbnail_path())

        schema = self.item().save_schema()
        if schema:
            form_widget = formwidget.FormWidget(self)
            form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            form_widget.set_schema(schema)
            form_widget.set_validator(self.item().save_validator)
            # item_name = os.path.basename(item.path())
            # form_widget.set_values({'name': item_name})
            self._options_frame.layout().addWidget(form_widget)
            form_widget.validate()
            self._form_widget = form_widget
        else:
            self._options_frame.setVisible(False)

    def update_thumbnail_size(self):
        """
        Updates the thumbnail button to teh size of the widget
        """

        width = self.width() - 10
        if width > 250:
            width = 250
        size = QSize(width, width)
        if self._sequence_widget:
            self._sequence_widget.setIconSize(size)
            self._sequence_widget.setMaximumSize(size)
        self._thumbnail_frame.setMaximumSize(size)

    def show_thumbnail_capture_dialog(self):
        """
        Asks the user if they would like to capture a thumbnail
        :return: int
        """

        buttons = QDialogButtonBox.Yes | QDialogButtonBox.Ignore | QDialogButtonBox.Cancel
        parent = self.item_view().library_window()
        btn = messagebox.MessageBox.question(
            parent, 'Create a thumbnail', 'Would you like to capture a thumbnail?', buttons=buttons)
        if btn == QDialogButtonBox.Yes:
            self.thumbnail_capture()

        return btn

    def show_by_frame_dialog(self):
        """
        Show the by frame dialog
        """

        help_text = """
        To help speed up the playblast you can set the "by frame" to another greater than 1.
        For example if the "by frame" is set to 2 it will playblast every second frame
        """

        result = None
        options = self.form_widget().values()
        by_frame = options.get('byFrame', 1)
        start_frame, end_frame = options.get('frameRange', [None, None])

        duration = end_frame - start_frame if start_frame is not None and end_frame is not None else 1
        if duration > 100 and by_frame == 1:
            buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            result = messagebox.MessageBox.question(
                self.library_window(), title='Tip', text=help_text, buttons=buttons, enable_dont_show_checkbox=True
            )

        return result

    def thumbnail_capture(self, show=False):
        """
        Captures a playblast and saves it to the temporal thumbnail path
        :param show: bool
        """

        options = self.form_widget().values()
        start_frame, end_frame = options.get('frameRange', [None, None])
        step = options.get('byFrame', 1)

        if not qtutils.is_control_modifier():
            result = self.show_by_frame_dialog()
            if result == QDialogButtonBox.Cancel:
                return

        path = utils.temp_path('sequence', 'thumbnail.jpg')

        try:
            snapshot.SnapshotWindow(path=path, on_save=self._on_thumbnail_captured)
            # thumbnail.ThumbnailCaptureDialog.thumbnail_capture(
            #     path=self._temp_path,
            #     show=show,
            #     start_frame=start_frame,
            #     end_frame=end_frame,
            #     step=step,
            #     clear_cache=False,
            #     captured=self._on_thumbnail_captured
            # )
        except Exception as e:
            messagebox.MessageBox.critical(self.library_window(), 'Error while capturing thumbnail', str(e))
            LOGGER.error(traceback.format_exc())

    def save(self, path, thumbnail):
        """
        Saves the item with the given objects to the given disk location path
        :param path: str
        :param thumbnail: str
        """

        kwargs = self.form_widget().values()
        sequence_path = self._sequence_widget.dirname()
        item_view = self.item_view()
        item_view.item_view.path = path
        library_window = self.library_window()
        valid_save = item_view.safe_save(thumbnail=thumbnail, sequence_path=sequence_path, **kwargs)
        if valid_save:
            if library_window:
                library_window.refresh()
                library_window.select_folder_path(path)
            self.saved.emit()
        self.close()

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _create_sequence_widget(self):
        """
        Internal function that creates a sequence widget to replace the static thumbnail widget
        """

        self._sequence_widget = sequence.ImageSequenceWidget(self)
        self._sequence_widget.setObjectName('thumbnailButton')
        self._thumbnail_frame.layout().insertWidget(0, self._sequence_widget)
        self._sequence_widget.clicked.connect(self._on_thumbnail_capture)
        self._sequence_widget.setToolTip(
            'Click to capture a thumbnail from the current model panel.\n'
            'CTRL + Click to show the capture window for better framing.')

        camera_icon = resources.get('icons', self.theme().style(), 'camera.png')
        expand_icon = resources.get('icons', self.theme().style(), 'full_screen.png')
        folder_icon = resources.get('icons', self.theme().style(), 'folder.png')

        self._sequence_widget.addAction(
            camera_icon, 'Capture new image', 'Capture new image', self._on_thumbnail_capture)
        self._sequence_widget.addAction(
            expand_icon, 'Show Capture window', 'Show Capture window', self._on_show_capture_window)
        self._sequence_widget.addAction(
            folder_icon, 'Load image from disk', 'Load image from disk', self._on_show_browse_image_dialog)

        self._sequence_widget.setIcon(resources.icon('tpdcc'))

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_show_menu(self):
        """
        Internal callback function that is called when menu button is clicked byu the user
        :return: QAction
        """

        pass

    def _on_save(self):
        if not self.library_window():
            return False

        library = self.library_window().library()
        if not library:
            return False

        try:
            self.form_widget().validate()
            if self.form_widget().has_errors():
                raise Exception('\n'.join(self.form_widget().errors()))
            has_frames = self._sequence_widget.has_frames()
            if not has_frames and self.ENABLE_THUMBNAIL_CAPTURE:
                button = self.show_thumbnail_capture_dialog()
                if button == QDialogButtonBox.Cancel:
                    return False
            name = self.form_widget().value('name')
            folder = self.form_widget().value('folder')
            comment = self.form_widget().value('comment') or ''

            extension = self.item().extension()
            if extension and not name.endswith(extension):
                name = '{}{}'.format(name, extension)

            path = folder + '/' + name
            thumbnail = self._sequence_widget.first_frame()

            save_item = library.get(path, only_extension=True)
            save_function = save_item.functionality().get('save')
            if not save_function:
                LOGGER.warning('Item "{}" does not supports save operation'.format(save_item))
                return False

            library_path = self.item().library.identifier
            if not library_path or not os.path.isfile(library_path):
                LOGGER.warning('Impossible to save data "{}" because its library does not exists: "{}"'.format(
                    self.item(), library_path))
                return

            values = self.form_widget().values()
            try:
                if self._client:
                    success, message, dependencies = self._client().save_data(
                        library_path=library_path, data_path=path, values=values)
                    if not success:
                        messagebox.MessageBox.critical(self.library_window(), 'Error while saving', str(message))
                        LOGGER.error(str(message))
                        return False
                else:
                    dependencies = save_function(**values)
            except Exception as exc:
                messagebox.MessageBox.critical(self.library_window(), 'Error while saving', str(exc))
                LOGGER.error(traceback.format_exc())
                return False

        except Exception as exc:
            messagebox.MessageBox.critical(self.library_window(), 'Error while saving', str(exc))
            LOGGER.error(traceback.format_exc())
            raise

        new_item_path = save_item.format_identifier()
        if not new_item_path or not os.path.isfile(new_item_path):
            LOGGER.warning('Although saving process for item "{}" was completed, '
                           'it seems no new data has been generated!'.format(save_item))
            self.saved.emit()
            return False

        save_item.library.add(new_item_path)

        # # TODO: Instead of creating a local version, we will use a git system to upload our data to our project repo
        # # TODO: Should we save new versions of dependencies too?
        # valid = save_item.create_version(comment=comment)
        # if not valid:
        #     LOGGER.warning('Impossible to store new version for data "{}"'.format(save_item))

        if thumbnail and os.path.isfile(thumbnail):
            save_item.store_thumbnail(thumbnail)

        self.library_window().sync()

        save_item.update_dependencies(dependencies=dependencies)

        self.saved.emit()

        return True

    def _on_cancel(self):
        self.cancelled.emit()
        self.close()

    def _on_thumbnail_capture(self):
        """
        Internal callback function that is called when a thumbnail capture must be done
        """

        self.thumbnail_capture(show=False)

    def _on_thumbnail_captured(self, captured_path):
        """
        Internal callback function that is called when thumbnail is captured
        :param captured_path: str
        """

        thumb_path = os.path.dirname(captured_path)
        self.set_thumbnail_path(thumb_path)

    def _on_show_capture_window(self):
        """
        Internal callback function that shows the capture window for framing
        """

        self.thumbnail_capture(show=True)

    def _on_show_browse_image_dialog(self):
        """
        Internal callback function that shows a file dialog for choosing an image from disk
        """

        file_dialog = QFileDialog(self, caption='Open Image', filter='Image Files (*.png *.jpg)')
        file_dialog.fileSelected.connect(self.set_thumbnail_path)
        file_dialog.exec_()


@decorators.add_metaclass(_MetaSaveWidget)
class SaveWidget(object):
    pass
