#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base library data item widget view implementation
"""

from __future__ import print_function, division, absolute_import

import os
import math

from Qt.QtCore import Qt, Signal, QObject, QRect, QSize, QThreadPool, QUrl
from Qt.QtWidgets import QApplication, QStyle, QTreeWidget, QTreeWidgetItem
from Qt.QtGui import QFontMetrics, QColor, QIcon, QPixmap, QPen, QBrush, QMovie

from tpDcc import dcc
from tpDcc.managers import resources
from tpDcc.libs.python import python, path as path_utils
from tpDcc.libs.resources.core import theme
from tpDcc.libs.qt.core import qtutils, image

from tpDcc.tools.datalibrary.core import consts


class LabelDisplayOption:

    Hide = "hide label"
    Over = "label over item"
    Under = "label under item"

    @staticmethod
    def values():
        return [
            LabelDisplayOption.Hide,
            LabelDisplayOption.Over,
            LabelDisplayOption.Under
        ]


class GlobalDataItemSignals(QObject, object):
    blendChanged = Signal(float)
    loadValueChanged = Signal(object, object)


@theme.mixin
class ItemView(QTreeWidgetItem):

    NAME = 'Item View'
    VERSION = 0
    PRIORITY = 0
    REPRESENTING = []           # List of data types this view can represent

    THREAD_POOL = QThreadPool()

    MAX_ICON_SIZE = consts.ITEM_DEFAULT_MAX_ICON_SIZE
    DEFAULT_FONT_SIZE = consts.ITEM_DEFAULT_FONT_SIZE
    DEFAULT_PLAYHEAD_COLOR = consts.ITEM_DEFAULT_PLAYHEAD_COLOR

    DEFAULT_THUMBNAIL_NAME = 'tpDcc.png'
    DEFAULT_THUMBNAIL_COLUMN = consts.ITEM_DEFAULT_THUMBNAIL_COLUMN
    ENABLE_THUMBNAIL_THREAD = consts.ITEM_DEFAULT_ENABLE_THUMBNAIL_THREAD

    PAINT_SLIDER = False
    _TYPE_PIXMAP_CACHE = dict()

    _globalSignals = GlobalDataItemSignals()
    blendChanged = _globalSignals.blendChanged
    loadValueChanged = _globalSignals.loadValueChanged

    def __init__(self, data_item, *args, **kwargs):
        super(ItemView, self).__init__(*args, **kwargs)

        self._size = None
        self._rect = None
        self._text_column_order = list()

        self._item = data_item

        self._icon = dict()
        self._thumbnail_icon = None
        self._fonts = dict()
        self._thread = None
        self._pixmap = dict()
        self._pixmap_rect = None
        self._pixmap_scaled = None
        self._type_pixmap = None

        self._mime_text = None
        self._drag_enabled = True
        self._under_mouse = False
        self._search_text = None
        self._info_widget = None
        self._viewer = None
        self._stretch_to_widget = None

        self._group_item = None
        self._group_column = 0

        self._image_sequence = None
        self._image_sequence_path = ''

        self._blend_down = False
        self._blend_value = 0.0
        self._blend_prev_value = 0.0
        self._blend_position = None
        self._blending_enabled = False

        self._worker = image.ImageWorker()
        self._worker.setAutoDelete(False)
        self._worker.signals.triggered.connect(self._on_thumbnail_from_image)
        self._worker_started = False

        self._icon_path = None

        icons_path = path_utils.join_path('icons', self.theme().name().lower())
        color_icons_path = path_utils.join_path('icons', 'color')

        icon_name = data_item.icon() if data_item else None
        if not icon_name:
            icon_name = self.DEFAULT_THUMBNAIL_NAME
        else:
            icon_name, icon_extension = os.path.splitext(icon_name)
            if not icon_extension:
                icon_name = '{}.png'.format(icon_name)

        dcc_name = dcc.client().get_name()
        type_icon = icon_name if icon_name == dcc_name + '.png' else None
        self._type_icon_path = resources.get(color_icons_path, type_icon) if type_icon else ''

        self._default_thumbnail_path = resources.get(
            icons_path, icon_name) or resources.get(icons_path, self.DEFAULT_THUMBNAIL_NAME)

    def __eq__(self, other):
        return id(other) == id(self)

    # Necessary for Python compatibility
    # https://stackoverflow.com/questions/1608842/types-that-define-eq-are-unhashable
    def __hash__(self):
        return id(self)

    def __ne__(self, other):
        return id(other) != id(self)

    def __del__(self):
        """
        When the object is deleted we make sure the sequence is stopped
        """

        self.stop()

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def item(self):
        return self._item

    # =================================================================================================================
    # OVERRIDES
    # =================================================================================================================

    def sizeHint(self, column=0):
        """
        Returns the current size of the item
        :param column: int
        :return: QSize
        """

        if self.stretch_to_widget():
            if self._size:
                size = self._size
            else:
                size = self.viewer().icon_size()
            w = self.stretch_to_widget().width()
            h = size.height()
            return QSize(w - 20, h)

        if self._size:
            return self._size
        else:
            icon_size = self.viewer().icon_size()
            if self.is_label_under_item():
                w = icon_size.width()
                h = icon_size.width() + self.text_height()
                icon_size = QSize(w, h)

            return icon_size

    def setHidden(self, value):
        """
        Overrides base QTreeWidgetItem.setHidden function
        Set the item hidden
        :param value: bool
        """

        super(ItemView, self).setHidden(value)
        row = self.treeWidget().index_from_item(self).row()
        self.viewer().list_view().setRowHidden(row, value)

    def backgroundColor(self):
        """
        Returns the background color for the item
        :return: QColor
        """

        return self.viewer().background_color()

    def icon(self, column):
        """
        Overrides base QTreeWidgetItem icon function
        Overrides icon to add support for thumbnail icon
        :param column: int
        :return: QIcon
        """

        item_icon = QTreeWidgetItem.icon(self, column)
        if not item_icon and column == self.DEFAULT_THUMBNAIL_COLUMN:
            item_icon = self.thumbnail_icon()

        return item_icon

    def setIcon(self, column, icon, color=None):
        """
        Overrides base QTreeWidgetItem setIcon function
        :param column: int or str
        :param icon: QIcon
        :param color: QColor or None
        """

        is_app_running = bool(QApplication.instance())
        if not is_app_running:
            return

        if python.is_string(icon):
            if not os.path.exists(icon):
                color = color or QColor(255, 255, 255, 20)
                icon = resources.icon('image', color=color)
            else:
                icon = QIcon(icon)
        if python.is_string(column):
            self._icon[column] = icon
        else:
            self._pixmap[column] = None
            super(ItemView, self).setIcon(column, icon)

        self.update_icon()

    def setFont(self, column, font):
        """
        Overrides base QTreeWidgetItem setFont function
        Sets the font for the given column
        :param column: int
        :param font: QFont
        """

        self._fonts[column] = font

    def textAlignment(self, column):
        """
        Returns the text alinment for the label in the given column
        :param column: int
        :return: QAlignmentFlag
        """

        if self.viewer().is_icon_view():
            return Qt.AlignCenter
        else:
            return QTreeWidgetItem.textAlignment(self, column)

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def name(self):
        """
        Returns item data name
        :return: str
        """

        return str(self.item.data.get('name'))

    def display_text(self, label):
        """
        Returns the sort data for the given column
        :param label: str
        :return: str
        """

        return str(self.item.data.get(label, ''))

    def sort_text(self, label):
        """
        Returns the sort data for the given column
        :param label: str
        :return: str
        """

        return str(self.item.data.get(label, ''))

    def stretch_to_widget(self):
        """
        Returns the stretch to widget widget
        :return: QWidget
        """

        return self._stretch_to_widget

    def set_stretch_to_widget(self, widget):
        """
        Sets the width of the item to the width of the given widget
        :param widget: QWidget
        """

        self._stretch_to_widget = widget

    def set_size(self, size):
        """
        Sets the size for the item
        :param size: QSize
        """

        self._size = size

    def pixmap(self, column):
        """
        Returns the pixmap for the given column
        :param column: int
        :return: QPixmap
        """

        if not self._pixmap.get(column):
            icon = self.icon(column)
            if icon:
                size = QSize(self.MAX_ICON_SIZE, self.MAX_ICON_SIZE)
                icon_size = icon.actualSize(size)
                self._pixmap[column] = icon.pixmap(icon_size)

        return self._pixmap.get(column)

    def set_pixmap(self, column, pixmap):
        """
        Sets the pixmap to be displayed in the given column
        :param column: int
        :param pixmap: QPixmap
        """

        self._pixmap[column] = pixmap

    def icon_path(self):
        """
        Returns icon path for current item
        :return: str
        """

        return self._icon_path

    def set_icon_path(self, path):
        """
        Sets icon path for the item
        :param path: str
        """

        self._icon_path = path

    def take_from_tree(self):
        """
        Takes this item from the tree
        """

        tree = self.treeWidget()
        parent = self.parent()
        if parent:
            parent.takeChild(parent.indexOfChild(self))
        else:
            tree.takeTopLevelItem(tree.indexOfTopLevelItem(self))

    def group_item(self):
        """
        Returns current group item
        :return: LibraryGroupItem
        """

        return self._group_item

    def set_group_item(self, group_item):
        """
        Sets current group item
        :param group_item: LibraryGroupItem
        """

        self._group_item = group_item

    def update_icon(self):
        """
        Clears the pixmap cache for the item
        """

        self.clear_cache()

    def clear_cache(self):
        """
        Clears the thumbnail cache
        """

        self._pixmap = dict()
        self._pixmap_rect = None
        self._pixmap_scaled = None
        self._thumbnail_icon = None

    def update(self):
        """
        Refresh teh visual state of the icon
        """

        self.update_icon()
        self.update_frame()

    def context_menu(self, menu, items=None):
        """
        Returns the context menu for the item
        This function must be implemented in a subclass to return a custom context menu for the item
        :param menu: QMenu
        :param items: list
        """

        pass

    # ============================================================================================================
    # MOUSE / KEYBOARD
    # ============================================================================================================

    def under_mouse(self):
        """
        Returns whether the items is under the mouse cursor or not
        :return: bool
        """

        return self._under_mouse

    def drop_event(self, event):
        """
        Reimplement in subclass to receive drop items for the item
        :param event: QDropEvent
        """

        pass

    def mouse_enter_event(self, event):
        """
        Reimplement in subclass to receive mouse enter events for the item
        :param event: QMouseEvent
        """

        self._under_mouse = True
        self.play()

    def mouse_leave_event(self, event):
        """
        Reimplement in subclass to receive mouse leave events for the item
        :param event: QMouseEvent
        """

        self._under_mouse = False
        self.stop()

    def mouse_move_event(self, event):
        """
        Reimplement in subclass to receive mouse move events for the item
        :param event: QMouseEvent
        """

        self.blending_event(event)
        self.image_sequence_event(event)

    def mouse_press_event(self, event):
        """
        Reimplement in subclass to receive mouse press events for the item
        :param event: QMouseEvent
        """

        if event.button() == Qt.MidButton:
            if self.is_blending_enabled():
                self.set_is_blending(True)
                self._blend_position = event.pos()

    def mouse_release_event(self, event):
        """
        Reimplement in subclass to receive mouse release events for the item
        :param event: QMouseEvent
        """

        if self.is_blending():
            self._blend_position = None
            self._blend_prev_value = self.blend_value()

    def key_press_event(self, event):
        """
        Reimplement in subclass to receive key press events for the item
        :param event: QKeyEvent
        """

        pass

    def key_release_event(self, event):
        """
        Reimplement in subclass to receive key release events for the item
        :param event: QKeyEvent
        """

        pass

    def clicked(self):
        """
        Triggered when an item is clicked
        """

        pass

    def double_clicked(self):
        """
        Triggered when an item is double clicked
        """

        pass

    def selection_changed(self):
        """
        Triggered when an item has been either selected or deselected
        """

        self.reset_blending()

    # ============================================================================================================
    # THUMBNAIL
    # ============================================================================================================

    def default_thumbnail_path(self):
        """
        Returns the default thumbnail path
        :return: str
        """
        return self._default_thumbnail_path

    def default_thumbnail_icon(self):
        """
        Returns the default thumbnail icon
        :return: QIcon
        """

        return QIcon(self.default_thumbnail_path())

    def type_icon_path(self):
        """
        Returns the type icon path on disk
        :return: str
        """

        if not self._type_icon_path:
            return self._icon_path

        return self._type_icon_path

    def is_default_thumbnail_path(self):
        """
        Returns whether or not current thumbnail path is the default one
        :return: bool
        """

        return self.thumbnail_path() == self._default_thumbnail_path

    def thumbnail_path(self):
        """
        Return the thumbnail path for the item on disk
        :return: str
        """

        item_path = self.item.format_identifier() if self.item else None
        if not item_path:
            return self._default_thumbnail_path

        thumbnail_path = os.path.dirname(item_path) if os.path.isfile(item_path) else item_path
        thumbnail_path = path_utils.join_path(thumbnail_path, consts.ITEM_DEFAULT_THUMBNAIL_NAME)
        if os.path.isfile(thumbnail_path):
            return thumbnail_path

        thumbnail_path = thumbnail_path.replace('.jpg', '.png')
        if os.path.isfile(thumbnail_path):
            return thumbnail_path

        return self._default_thumbnail_path

    def thumbnail_icon(self):
        """
        Returns the thumbnail icon
        :return: QIcon
        """

        thumbnail_path = self.thumbnail_path()
        if not self._thumbnail_icon:
            if self.ENABLE_THUMBNAIL_THREAD and not self._worker_started:
                self._worker_started = True
                self._worker.set_path(thumbnail_path)
                self.THREAD_POOL.start(self._worker)
                self._thumbnail_icon = self.default_thumbnail_icon()
            else:
                self._thumbnail_icon = QIcon(thumbnail_path)

        return self._thumbnail_icon

    # =================================================================================================================
    # SEQUENCE
    # =================================================================================================================

    def image_sequence(self):
        """
        Return ImageSequence of the item
        :return: image.ImageSequence or QMovie
        """

        return self._image_sequence

    def set_image_sequence(self, image_sequence):
        """
        Set the image sequence of the item
        :param image_sequence: image.ImageSequence or QMovie
        """

        self._image_sequence = image_sequence

    def image_sequence_path(self):
        """
        Return the path where image sequence is located on disk
        :return: str
        """

        return self._image_sequence_path

    def set_image_sequence_path(self, path):
        """
        Set the path where image sequence is located on disk
        :param path: str
        """

        self._image_sequence_path = path

    def reset_image_sequence(self):
        """
        Reset image sequence
        """

        self._image_sequence = None

    def play(self):
        """
        Start play image sequence
        """

        self.reset_image_sequence()
        path = self.image_sequence_path() or self.thumbnail_path()
        movie = None

        if not path:
            return

        if os.path.isfile(path) and path.lower().endswith('.gif'):
            movie = QMovie(path)
            movie.setCacheMode(QMovie.CacheAll)
            movie.frameChanged.connect(self._on_frame_changed)
        elif os.path.isdir(path):
            if not self.image_sequence():
                movie = image.ImageSequence(path)
                movie.frameChanged.connect(self._on_frame_changed)

        if movie:
            self.set_image_sequence(movie)
            self.image_sequence().start()

    def update_frame(self):
        """
        Function that updates the current frame
        """

        if self.image_sequence():
            pixmap = self.image_sequence().current_pixmap()
            self.setIcon(0, pixmap)

    def stop(self):
        """
        Stop play image sequence
        """

        if self._image_sequence:
            self._image_sequence.stop()

    def playhead_color(self):
        """
        Returns playehad color
        :return: QColor
        """

        return self.DEFAULT_PLAYHEAD_COLOR

    def image_sequence_event(self, event):
        """
        :param event: QEvent
        """

        if not self.image_sequence() or not qtutils.is_control_modifier() or not self.rect():
            return

        x = event.pos().x() - self.rect().x()
        width = self.rect().width()
        percent = 1.0 - (float(width - x) / float(width))
        frame = int(self.image_sequence().frameCount() * percent)
        self.image_sequence().jumpToFrame(frame)
        self.update_frame()

    # =================================================================================================================
    # DRAG & DROP
    # =================================================================================================================

    def drag_enabled(self):
        """
        Return whether the item can be dragged or not
        :return: bool
        """

        return self._drag_enabled

    def set_drag_enabled(self, flag):
        """
        Set whether item can be dragged or not
        :param flag: bool
        """

        self._drag_enabled = flag

    def mime_text(self):
        """
        Returns the mime text for drag and drop
        :return: str
        """

        return self._mime_text or self.text(0)

    def set_mime_text(self, text):
        """
        Sets the mime text for drag and drop
        :param text: str
        """

        self._mime_text = text

    def url(self):
        """
        Used by the mime data when dragging/droping the item
        :return: Qurl
        """

        if not self._url:
            self._url = QUrl(self.text(0))

        return self._url

    def set_url(self, url):
        """
        Sets the url object of the current item
        :param url: QUrl or None
        """

        self._url = url

    # =================================================================================================================
    # SEARCH
    # =================================================================================================================

    def search_text(self):
        """
        Returns the search string used for finding the item
        :return: str
        """

        if not self._search_text:
            self._search_text = str(self._data)

        return self._search_text

    # =================================================================================================================
    # VIEWER WIDGET
    # =================================================================================================================

    def viewer(self):
        """
        Returns the viewer widget that contains the item
        :return: libraryViewer
        """

        viewer_widget = None
        if self.treeWidget():
            viewer_widget = self.treeWidget().parent()

        return viewer_widget

    def dpi(self):
        """
        Return current dpi
        :return: int
        """

        if self.viewer():
            return self.viewer().dpi()

        return 1

    def padding(self):
        """
        Returns the padding/border size for the item
        :return: int
        """

        return self.viewer().padding()

    def text_height(self):
        """
        Returns the height of the text for the item
        :return: int
        """

        return self.viewer().item_text_height()

    def label_display_option(self):
        """
        Returns label display option of the item
        :return: LabelDisplayOption
        """

        return self.viewer().label_display_option()

    def is_text_visible(self):
        """
        Returns whether the text is visible or not
        :return: bool
        """

        return self.label_display_option() != LabelDisplayOption.Hide

    def is_label_over_item(self):
        """
        Returns whether or not item label should be displayed over the item
        :return: bool
        """

        return self.label_display_option() == LabelDisplayOption.Over

    def is_label_under_item(self):
        """
        Returns whether or not item label should be displayed under the item
        :return: bool
        """

        return self.label_display_option() == LabelDisplayOption.Under

    # =================================================================================================================
    # TREE WIDGET
    # =================================================================================================================

    def column_from_label(self, label):
        """
        Returns column fro mlabel
        :param label: str
        :return: str
        """

        if self.treeWidget():
            return self.treeWidget().column_from_label(label)

        return None

    def label_from_column(self, column):
        """
        Returns label of the given column
        :param column: int
        :return: str
        """

        if self.treeWidget():
            return self.treeWidget().label_from_column(column)

        return None

    # ============================================================================================================
    # PAINT
    # ============================================================================================================

    def type_pixmap(self):
        """
        Returns the type pixmap for the item data type
        :return: QPixmap
        """

        path = self.type_icon_path()
        pixmap = self._TYPE_PIXMAP_CACHE.get(path)
        if not pixmap and path and os.path.isfile(path):
            self._TYPE_PIXMAP_CACHE[path] = QPixmap(path)

        return self._TYPE_PIXMAP_CACHE.get(path)

    def font_size(self):
        """
        Returns the font size for the item
        :return: int
        """

        return self.DEFAULT_FONT_SIZE

    def font(self, column):
        """
        Returns the font for the given column
        :param column: int
        :return: QFont
        """

        default = QTreeWidgetItem.font(self, column)
        font = self._fonts.get(column, default)
        font.setPixelSize(self.font_size() * self.dpi())

        return font

    def set_font(self, column, font):
        """
        Sets the font used by the items in the given column
        :param column: int
        :param font: QFont
        """

        self._fonts[column] = font

    def text_width(self, column):
        """
        Returns the text width of the given column
        :param column: int
        :return: int
        """

        text = self.text(column)
        font = self.font(column)
        metrics = QFontMetrics(font)
        text_width = metrics.width(text)

        return text_width

    def text_color(self):
        """
        Returns the text color for the item
        :return: QColor
        """

        # TODO: change to use foreground role
        # return self.itemsWidget().palette().color(self.itemsWidget().foregroundRole())
        return self.viewer().text_color()

    def text_selected_color(self):
        """
        Returns the selected txt color for the item
        :return: QColor
        """

        return self.viewer().text_selected_color()

    def background_hover_color(self):
        """
        Returns the background color when the mouse is over the item
        :return: QColor
        """

        return self.viewer().background_hover_color()

    def background_selected_color(self):
        """
        Returns the background color when the item is selected
        :return: QColor
        """

        return self.viewer().background_selected_color()

    def rect(self):
        """
        Returns the rect for the current paint frame
        :return: QRect
        """

        return self._rect

    def set_rect(self, rect):
        """
        Sets the rect for the current paint frame
        :param rect: QRect
        """

        self._rect = rect

    def visual_rect(self, option):
        """
        Returns the visual rect for the item
        :param option: QStyleOptionViewItem
        :return: QRect
        """

        return QRect(option.rect)

    def icon_rect(self, option):
        """
        Returns the icon rect for the item
        :param option: QStyleOptionViewItem
        :return: QRect
        """

        padding = self.padding()
        rect = self.visual_rect(option)
        width = rect.width()
        height = rect.height()
        if self.is_label_under_item():
            height -= self.text_height()
        width -= padding
        height -= padding
        rect.setWidth(width)
        rect.setHeight(height)

        x = 0
        x += float(padding) / 2
        x += float((width - rect.width())) / 2

        y = float((height - rect.height())) / 2
        y += float(padding) / 2
        rect.translate(x, y)

        return rect

    def type_icon_rect(self, option):
        """
        Returns the type icon rect
        :param option:
        :return: QRect
        """

        padding = 2 * self.dpi()
        rect = self.icon_rect(option)
        x = rect.x() + padding
        y = rect.y() + padding
        rect = QRect(x, y, 13 * self.dpi(), 13 * self.dpi())

        return rect

    def paint_row(self, painter, option, index):
        """
        Paint performs low-level painting for the item
        :param painter: QPainter
        :param option: QStyleOptionViewItem
        :param index: QModelIndex
        """

        QTreeWidget.drawRow(self.treeWidget(), painter, option, index)

    def paint(self, painter, option, index):
        """
        Paint performs low-level painting for the item
        :param painter: QPainter
        :param option: QStyleOptionViewItem
        :param index: QModelIndex
        """

        self.set_rect(QRect(option.rect))
        painter.save()
        try:
            self.paint_background(painter, option, index)
            self.paint_icon(painter, option, index)
            if index.column() == 0 and self.blend_value() != 0:
                self.paint_blend_slider(painter, option, index)
            if self.is_text_visible():
                self.paint_text(painter, option, index)
            if index.column() == 0:
                self.paint_type_icon(painter, option)
            if index.column() == 0 and self.image_sequence():
                self.paint_playhead(painter, option)
        finally:
            painter.restore()

    def paint_background(self, painter, option, index):
        """
        Draw the background for the item
        :param painter: QPainter
        :param option: QStyleOptionViewItem
        :param index:QModelIndex
        """

        is_selected = option.state & QStyle.State_Selected
        is_mouse_over = option.state & QStyle.State_MouseOver
        painter.setPen(QPen(Qt.NoPen))
        visual_rect = self.visual_rect(option)
        if is_selected:
            color = self.background_selected_color()
        elif is_mouse_over:
            color = self.background_hover_color()
        else:
            color = self.backgroundColor()
        painter.setBrush(QBrush(color))

        if not self.viewer().is_icon_view():
            spacing = 1 * self.dpi()
            height = visual_rect.height() - spacing
            visual_rect.setHeight(height)

        painter.drawRect(visual_rect)

    def paint_icon(self, painter, option, index, align=None):
        """
        Draws the icon for the item
        :param painter: QPainter
        :param option: QStyleOptionViewItem
        :param index: int
        :param align: Qt.Align
        """

        column = index.column()
        pixmap = self.pixmap(column)
        if not pixmap:
            return

        rect = self.icon_rect(option)
        pixmap = self._scale_pixmap(pixmap, rect)
        pixmap_rect = QRect(rect)
        pixmap_rect.setWidth(pixmap.width())
        pixmap_rect.setHeight(pixmap.height())

        align = align or Qt.AlignHCenter | Qt.AlignVCenter

        x, y = 0, 0
        align_bottom_a = Qt.AlignBottom | Qt.AlignLeft
        align_bottom_b = align == Qt.AlignBottom | Qt.AlignHCenter or align == Qt.AlignBottom | Qt.AlignRight
        align_h_center_a = Qt.AlignHCenter or align == Qt.AlignCenter
        align_h_center_b = align == Qt.AlignHCenter | Qt.AlignBottom or align == Qt.AlignHCenter | Qt.AlignTop
        align_v_center_a = align == Qt.AlignVCenter | Qt.AlignLeft or align == Qt.AlignVCenter | Qt.AlignRight
        align_v_center_b = Qt.AlignVCenter or align == Qt.AlignCenter

        is_align_bottom = align == align_bottom_a or align_bottom_b
        is_align_h_center = align == align_h_center_a or align_h_center_b
        is_align_v_center = align == align_v_center_a or align_v_center_b
        if is_align_h_center:
            x += float(rect.width() - pixmap.width()) / 2
        elif is_align_v_center:
            y += float(rect.height() - pixmap.height()) / 2
        elif is_align_bottom:
            y += float(rect.height() - pixmap.height())

        pixmap_rect.translate(x, y)
        painter.drawPixmap(pixmap_rect, pixmap)

    def paint_text(self, painter, option, index):
        """
        Draws the text for the item
        :param painter: QPainter
        :param option: QStyleOptionViewItem
        :param index: int
        """

        column = index.column()
        if column == 0 and self.viewer().is_table_view():
            return

        self._paint_text(painter, option, column)

    def paint_type_icon(self, painter, option):
        """
        Draw the item type icon at the top left
        :param painter: QPainter
        :param option: QStyleOptionViewItem
        """

        rect = self.type_icon_rect(option)
        type_pixmap = self.type_pixmap()
        if type_pixmap:
            painter.setOpacity(0.5)
            painter.drawPixmap(rect, type_pixmap)
            painter.setOpacity(1)

    def paint_playhead(self, painter, option):
        """
        Pain the playhead if the item has an image sequence
        :param painter: QPainter
        :param option: QStyleOptionViewItem
        """

        image_sequence = self.image_sequence()
        if image_sequence and self.under_mouse():
            count = image_sequence.frame_count()
            current = image_sequence.current_frame_number()
            if count > 0:
                percent = float((count + current) + 1) / count - 1
            else:
                percent = 0

            icon_rect = self.icon_rect(option)
            playhead_color = self.playhead_color()

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(playhead_color))

            if percent <= 0:
                width = 0
            elif percent >= 1:
                width = icon_rect.width()
            else:
                width = (percent * icon_rect.width()) - 1

            height = 3 * self.dpi()
            y = icon_rect.y() + icon_rect.height() - (height - 1)

            painter.drawRect(icon_rect.x(), y, width, height)

    def paint_blend_slider(self, painter, option, index):
        if not self.PAINT_SLIDER or not self.viewer().is_icon_view():
            return

        painter.setPen(QPen(Qt.NoPen))
        rect = self.visual_rect(option)
        color = self.viewer().background_color().toRgb()
        color.setAlpha(75)
        painter.setBrush(QBrush(color))
        height = rect.height()
        ratio = self.blend_value()
        if ratio < 0:
            width = 0
        elif ratio > 100:
            width = rect.width()
        else:
            width = rect.width() * (float(ratio) / 100)
        rect.setWidth(width)
        rect.setHeight(height)

        rect = self.visual_rect(option)
        rect.setY(rect.y() + (4 * self.dpi()))
        color = self.viewer().text_color().toRgb()
        color.setAlpha(220)
        pen = QPen(color)
        align = Qt.AlignTop | Qt.AlignHCenter
        painter.setPen(pen)
        painter.drawText(rect, align, str(self.blend_value()) + "%")

    # =================================================================================================================
    # INTERNAL
    # =================================================================================================================

    def _thumbnail_from_image(self, image):
        """
        Called after the given image object has finished loading
        :param image: QImage
        """

        self.clear_cache()
        pixmap = QPixmap()
        pixmap.convertFromImage(image)
        icon = QIcon(pixmap)
        self._thumbnail_icon = icon
        if self.viewer():
            self.viewer().update()

    def _scale_pixmap(self, pixmap, rect):
        """
        Internal function that scales the given pixmap to given rect size
        The scaled pixmap is cached and its reused if its called with the same size
        :param pixmap: QPixmap
        :param rect: QRect
        :return: QPixmap
        """

        rect_changed = True

        if self._pixmap_rect:
            width_changed = self._pixmap_rect.width() != rect.width()
            height_changed = self._pixmap_rect.height() != rect.height()
            rect_changed = width_changed or height_changed

        if not self._pixmap_scaled or rect_changed:
            self._pixmap_scaled = pixmap.scaled(
                rect.width(), rect.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._pixmap_rect = rect

        return self._pixmap_scaled

    def _paint_text(self, painter, option, column):
        """
        Internal function used to paint the text
        :param painter: QPainter
        :param option: QStyleOption
        :param column: int
        """

        if self.viewer().is_icon_view():
            text = self.item.full_name() if self.item else self.name()
        else:
            label = self.label_from_column(column)
            text = self.display_text(label)

        color = self.text_color()
        is_selected = option.state & QStyle.State_Selected
        if is_selected:
            color = self.text_selected_color()

        visual_rect = self.visual_rect(option)
        width = visual_rect.width()
        height = visual_rect.height()
        padding = self.padding()
        x = padding / 2
        y = padding / 2
        visual_rect.translate(x, y)
        visual_rect.setWidth(width - padding)
        visual_rect.setHeight(height - padding)

        font = self.font(column)
        align = self.textAlignment(column)
        metrics = QFontMetrics(font)
        text_width = 1
        if text:
            text_width = metrics.width(text)
        if text_width > visual_rect.width() - padding:
            visual_width = visual_rect.width()
            text = metrics.elidedText(text, Qt.ElideMiddle, visual_width)
            align = Qt.AlignLeft

        align = align | Qt.AlignVCenter
        rect = QRect(visual_rect)

        if self.viewer().is_icon_view():
            if self.is_label_over_item() or self.is_label_under_item():
                padding = 8 if padding < 8 else padding
                height = metrics.height() + (padding / 2)
                y = (rect.y() + rect.height()) - height
                rect.setY(y)
                rect.setHeight(height)
            if self.is_label_over_item():
                color2 = self.viewer().background_color().toRgb()
                color2.setAlpha(200)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(color2))
                painter.drawRect(rect)

        pen = QPen(color)
        painter.setPen(pen)
        painter.setFont(font)
        painter.drawText(rect, align, text)

    # ============================================================================================================
    # BLENDING
    # ============================================================================================================

    def is_blending_enabled(self):
        """
        Returns whether blending is enabled or not
        :return: bool
        """

        return self._blending_enabled

    def set_blending_enabled(self, flag):
        """
        Sets whether blending is enabled or not
        :param flag: bool
        """

        self._blending_enabled = flag

    def is_blending(self):
        """
        Returns whether blending is playing or not
        :return: bool
        """

        return self._blend_down

    def set_is_blending(self, flag):
        """
        Called when the middle mouse button is released
        :return: QMouseEvent
        """

        self._blend_down = flag
        if not flag:
            self._blend_position = None
            self._blend_prev_value = self.blend_value()

    def blend_value(self):
        """
        Returns the current blend value
        :return: float
        """

        return self._blend_value

    def set_blend_value(self, blend):
        """
        Sets the current blend value
        :param blend: float
        """

        if self.is_blending_enabled():
            self._blend_value = blend
            if self.PAINT_SLIDER:
                self.update()
            self.blendChanged.emit(blend)
            if self.PAINT_SLIDER:
                self.update()

    def blend_previous_value(self):
        """
        Returns the blend previous current value
        :return: float
        """

        return self._blend_prev_value

    def blend_position(self):
        """
        Returns current blend position
        :return: QPoint
        """

        return self._blend_position

    def blending_event(self, event):
        """
        Function that is called when the mouse moves while the middle mouse button is held down
        :param event: QMouseEvent
        """

        if self.is_blending():
            value = math.ceil((event.pos().x() - self.blend_position().x()) * 1.5) + self.blend_previous_value()
            try:
                self.set_blend_value(value)
            except Exception:
                self.set_is_blending(False)

    def reset_blending(self):
        """
        Resets the blending value to zero
        """

        self._blend_value = 0.0
        self._blend_prev_value = 0.09

    # =================================================================================================================
    # CALLBACKS
    # =================================================================================================================

    def _on_thumbnail_from_image(self, image):
        """
        Internal callback function that is called when an image object has finished loading
        """

        self.clear_cache()
        pixmap = QPixmap()
        pixmap.convertFromImage(image)
        icon = QIcon(pixmap)
        self._thumbnail_icon = icon
        if self.viewer():
            self.viewer().update()

    def _on_frame_changed(self):
        """
        Internal callback function that is triggered when the movei object updates to the given
        frame
        :return:
        """

        if not qtutils.is_control_modifier():
            self.update_frame()
