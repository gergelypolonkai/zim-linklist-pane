# -*- coding: utf-8 -*-

# Copyright 2016 Gergely Polonkai <gergely@polonkai.eu>

from __future__ import with_statement

import gtk
import pango

from zim.plugins import PluginClass, extends, WindowExtension
from zim.gui.widgets import RIGHT_PANE, PANE_POSITIONS, BrowserTreeView, \
    populate_popup_add_separator
from zim.index import LINK_DIR_FORWARD


class LinksListPanePlugin(PluginClass):
    plugin_info = {
        'name': _('LinksList Pane'),  # T: plugin name
        'description': _('''\
This plugin adds an extra widget showing a list of pages linked from
the current page.
'''),  # T: plugin description
        'author': 'Gergely Polonkai',
        'help': 'Plugins:LinksList Pane',
    }

    plugin_preferences = (
        # key, type, label, default
        ('pane',
         'choice',
         _('Position in the window'),  # T: option for plugin preferences
         RIGHT_PANE,
         PANE_POSITIONS),
    )


@extends('MainWindow')
class MainWindowExtension(WindowExtension):
    def __init__(self, plugin, window):
        WindowExtension.__init__(self, plugin, window)

        opener = self.window.get_resource_opener()
        self.widget = LinksListWidget(opener)

        if self.window.ui.page:
            ui = self.window.ui
            page = self.window.ui.page
            self.on_open_page(ui, page, page)

        self.connectto(self.window.ui, 'open-page')
        self.on_preferences_changed(plugin.preferences)
        self.connectto(plugin.preferences,
                       'changed',
                       self.on_preferences_changed)

    def on_preferences_changed(self, preferences):
        if self.widget is None:
            return

        try:
            self.window.remove(self.widget)
        except ValueError:
            pass

        self.window.add_tab(_('Link list'),  # T: widget label
                            self.widget,
                            preferences['pane'])
        self.widget.show_all()
        self.widget.show_all()

    def on_open_page(self, ui, page, path):
        self.widget.set_page(self.window.ui.notebook, page)

    def teardown(self):
        self.window.remove(self.widget)
        self.widget.destroy()
        self.widget = None


PAGE_COL = 0
TEXT_COL = 1


class LinksListWidget(gtk.ScrolledWindow):
    def __init__(self, opener):
        gtk.ScrolledWindow.__init__(self)

        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_IN)

        self.opener = opener

        self.treeview = LinksTreeView()
        self.add(self.treeview)
        self.treeview.connect('row-activated', self.on_link_activated)
        self.treeview.connect('populate-popup', self.on_populate_popup)

    def set_page(self, notebook, page):
        model = self.treeview.get_model()

        model.clear()

        links = notebook.index.list_links(page, LINK_DIR_FORWARD)

        for link in links:
            href = notebook.relative_link(link.source, link.href)
            href = href.lstrip(':')
            model.append((link.source, href))

    def on_link_activated(self, treeview, path, column):
        model = treeview.get_model()
        path = model[path][PAGE_COL]

        self.opener.open_page(path)

    def on_populate_popup(self, treeview, menu):
        populate_popup_add_separator(menu)

        item = gtk.MenuItem(_('Open in New _Window'))
        item.connect('activate', self.on_open_new_window, treeview)
        menu.append(item)

        # Other per page menu items do not really apply here...

    def on_open_new_window(self, o, treeview):
        model, iter = treeview.get_selection().get_selected()

        if model and iter:
            path = model[iter][PAGE_COL]
            self.opener.open_page(path, new_window=True)


class LinksTreeView(BrowserTreeView):
    def __init__(self):
        BrowserTreeView.__init__(self, LinksTreeModel())

        self.set_headers_visible(False)

        cell_renderer = gtk.CellRendererText()
        cell_renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        column = gtk.TreeViewColumn('_page_', cell_renderer, text=TEXT_COL)
        self.append_column(column)

        if gtk.gtk_version >= (2, 12, 0) and \
           gtk.pygtk_version >= (2, 12, 0):
            self.set_tooltip_column(TEXT_COL)


class LinksTreeModel(gtk.ListStore):
    def __init__(self):
        gtk.ListStore.__init__(self, object, str)  # PAGE_COL, TEXT_COL
