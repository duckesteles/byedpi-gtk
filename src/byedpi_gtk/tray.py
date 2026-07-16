import os

from gi.repository import Gio, GLib, GObject

SNI_IFACE = 'org.kde.StatusNotifierItem'
MENU_IFACE = 'com.canonical.dbusmenu'
WATCHER_NAME = 'org.kde.StatusNotifierWatcher'
WATCHER_PATH = '/StatusNotifierWatcher'

ITEM_XML = '''
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <method name="Activate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/>
      <arg name="orientation" type="s" direction="in"/>
    </method>
    <signal name="NewIcon"/>
    <signal name="NewStatus">
      <arg name="status" type="s"/>
    </signal>
  </interface>
</node>
'''

MENU_XML = '''
<node>
  <interface name="com.canonical.dbusmenu">
    <property name="Version" type="u" access="read"/>
    <property name="Status" type="s" access="read"/>
    <method name="GetLayout">
      <arg name="parentId" type="i" direction="in"/>
      <arg name="recursionDepth" type="i" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="revision" type="u" direction="out"/>
      <arg name="layout" type="(ia{sv}av)" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="properties" type="a(ia{sv})" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg name="id" type="i" direction="in"/>
      <arg name="name" type="s" direction="in"/>
      <arg name="value" type="v" direction="out"/>
    </method>
    <method name="Event">
      <arg name="id" type="i" direction="in"/>
      <arg name="eventId" type="s" direction="in"/>
      <arg name="data" type="v" direction="in"/>
      <arg name="timestamp" type="u" direction="in"/>
    </method>
    <method name="AboutToShow">
      <arg name="id" type="i" direction="in"/>
      <arg name="needUpdate" type="b" direction="out"/>
    </method>
    <signal name="LayoutUpdated">
      <arg name="revision" type="u"/>
      <arg name="parent" type="i"/>
    </signal>
    <signal name="ItemsPropertiesUpdated">
      <arg name="updatedProps" type="a(ia{sv})"/>
      <arg name="removedProps" type="a(ias)"/>
    </signal>
  </interface>
</node>
'''


class TrayIcon(GObject.Object):
    __gsignals__ = {
        'activate': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'menu-item': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, app_id, title):
        super().__init__()
        self._app_id = app_id
        self._title = title
        self._icon_name = app_id
        self._icon_pixmap = []
        self._object_path = '/StatusNotifierItem'
        self._menu_path = '/MenuBar'
        self._items = []
        self._menu_revision = 1
        self._bus = None
        self._item_reg = 0
        self._menu_reg = 0
        self._bus_owner_id = 0
        self._sni_name = None
        self._active = False

    def set_menu(self, items):
        self._items = items
        self._menu_revision += 1
        if self._bus is not None:
            self._bus.emit_signal(
                None, self._menu_path, MENU_IFACE, 'LayoutUpdated',
                GLib.Variant('(ui)', (self._menu_revision, 0)),
            )

    def set_icon(self, icon_name):
        self._icon_name = icon_name
        if self._bus is not None:
            self._bus.emit_signal(
                None, self._object_path, SNI_IFACE, 'NewIcon', None
            )

    def set_icon_pixmap(self, pixmaps):
        self._icon_pixmap = pixmaps
        if self._bus is not None:
            self._bus.emit_signal(
                None, self._object_path, SNI_IFACE, 'NewIcon', None
            )

    def start(self):
        pid = os.getpid()
        self._sni_name = 'org.kde.StatusNotifierItem-{}-1'.format(pid)
        self._bus_owner_id = Gio.bus_own_name(
            Gio.BusType.SESSION, self._sni_name,
            Gio.BusNameOwnerFlags.NONE,
            self._on_bus_acquired, None, self._on_name_lost,
        )

    def _on_name_lost(self, connection, name):
        self._active = False

    def stop(self):
        if self._item_reg and self._bus is not None:
            self._bus.unregister_object(self._item_reg)
            self._item_reg = 0
        if self._menu_reg and self._bus is not None:
            self._bus.unregister_object(self._menu_reg)
            self._menu_reg = 0
        if self._bus_owner_id:
            Gio.bus_unown_name(self._bus_owner_id)
            self._bus_owner_id = 0
        self._active = False

    def is_active(self):
        return self._active

    def _on_bus_acquired(self, connection, name):
        self._bus = connection
        item_info = Gio.DBusNodeInfo.new_for_xml(ITEM_XML).interfaces[0]
        menu_info = Gio.DBusNodeInfo.new_for_xml(MENU_XML).interfaces[0]
        try:
            self._item_reg = connection.register_object(
                self._object_path, item_info,
                self._item_method, self._item_get_property, None,
            )
            self._menu_reg = connection.register_object(
                self._menu_path, menu_info,
                self._menu_method, self._menu_get_property, None,
            )
        except GLib.Error:
            return
        self._register_with_watcher(connection)

    def _register_with_watcher(self, connection):
        connection.call(
            WATCHER_NAME, WATCHER_PATH, WATCHER_NAME,
            'RegisterStatusNotifierItem',
            GLib.Variant('(s)', (self._sni_name,)),
            None, Gio.DBusCallFlags.NONE, 2000, None,
            self._on_registered,
        )

    def _on_registered(self, source, result):
        try:
            source.call_finish(result)
            self._active = True
        except GLib.Error:
            self._active = False

    def _item_get_property(self, connection, sender, path, iface, prop):
        values = {
            'Category': GLib.Variant('s', 'ApplicationStatus'),
            'Id': GLib.Variant('s', self._app_id),
            'Title': GLib.Variant('s', self._title),
            'Status': GLib.Variant('s', 'Active'),
            'IconName': GLib.Variant('s', self._icon_name),
            'IconPixmap': GLib.Variant('a(iiay)', self._icon_pixmap),
            'Menu': GLib.Variant('o', self._menu_path),
            'ItemIsMenu': GLib.Variant('b', False),
        }
        return values.get(prop)

    def _item_method(self, connection, sender, path, iface, method, params,
                     invocation):
        if method == 'Activate':
            self.emit('activate')
            invocation.return_value(None)
        elif method == 'SecondaryActivate':
            self.emit('activate')
            invocation.return_value(None)
        elif method == 'Scroll':
            invocation.return_value(None)
        else:
            invocation.return_value(None)

    def _menu_get_property(self, connection, sender, path, iface, prop):
        if prop == 'Version':
            return GLib.Variant('u', 3)
        if prop == 'Status':
            return GLib.Variant('s', 'normal')
        return None

    def _item_node(self, item):
        if item.get('type') == 'separator':
            props = {
                'type': GLib.Variant('s', 'separator'),
                'visible': GLib.Variant('b', True),
            }
        else:
            props = {
                'label': GLib.Variant('s', item['label']),
                'enabled': GLib.Variant('b', item.get('enabled', True)),
                'visible': GLib.Variant('b', True),
            }
        return GLib.Variant('(ia{sv}av)', (item['id'], props, []))

    def _menu_method(self, connection, sender, path, iface, method, params,
                     invocation):
        if method == 'GetLayout':
            children = [self._item_node(i) for i in self._items]
            invocation.return_value(GLib.Variant('(u(ia{sv}av))', (
                self._menu_revision, (0, {}, children),
            )))
        elif method == 'GetGroupProperties':
            entries = []
            for item in self._items:
                if item.get('type') == 'separator':
                    props = {'type': GLib.Variant('s', 'separator')}
                else:
                    props = {
                        'label': GLib.Variant('s', item['label']),
                        'enabled': GLib.Variant(
                            'b', item.get('enabled', True)
                        ),
                        'visible': GLib.Variant('b', True),
                    }
                entries.append((item['id'], props))
            invocation.return_value(
                GLib.Variant('(a(ia{sv}))', (entries,))
            )
        elif method == 'GetProperty':
            invocation.return_value(GLib.Variant('(v)', (
                GLib.Variant('s', ''),
            )))
        elif method == 'Event':
            values = params.unpack()
            item_id, event_id = values[0], values[1]
            if event_id == 'clicked':
                for item in self._items:
                    if item['id'] == item_id and 'action' in item:
                        self.emit('menu-item', item['action'])
                        break
            invocation.return_value(None)
        elif method == 'AboutToShow':
            invocation.return_value(GLib.Variant('(b)', (False,)))
        else:
            invocation.return_value(None)
