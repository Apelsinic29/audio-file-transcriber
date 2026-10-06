#!/usr/bin/env python3
"""Omarchy tray item for audio-file-transcriber.

Left-click the icon (or "transcribe" in the tray menu) to pick an audio file to
transcribe. "History" in the tray menu opens the folder where previous
transcripts are kept. Transcription runs with a progress bar.

The tray icon uses com.github.apelsinic29.audioFileTranscriber as its D-Bus name
and exports a StatusNotifierItem plus a com.canonical.dbusmenu. The host (the
Omarchy status-notification watcher) draws the menu itself, so this item must
export a real dbusmenu.
"""
import os
import subprocess
import sys
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gio, GLib, Gtk, Gdk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAUNCH = os.path.join(SCRIPT_DIR, "launch")

HISTORY_DIR = os.path.expanduser("~/Documents/Transcripts")
LOGFILE = os.path.expanduser("~/.cache/audio-file-transcriber/tray.log")

BUS_NAME = "com.github.apelsinic29.audioFileTranscriber"
TRAY_ID = "audio-file-transcriber"
ICON_NAME = "audio-transcriber-symbolic"

SNI_XML = """
<node>
  <interface name='org.kde.StatusNotifierItem'>
    <property name='Category' type='s' access='read'/>
    <property name='Id' type='s' access='read'/>
    <property name='Title' type='s' access='read'/>
    <property name='Status' type='s' access='read'/>
    <property name='ItemIsMenu' type='b' access='read'/>
    <property name='IconName' type='s' access='read'/>
    <property name='ToolTip' type='(s(iiay)ss)' access='read'/>
    <property name='Menu' type='o' access='read'/>
    <method name='Activate'><arg name='x' type='i' direction='in'/><arg name='y' type='i' direction='in'/></method>
    <method name='SecondaryActivate'/>
  </interface>
</node>
"""

MENU_XML = """
<node>
  <interface name='com.canonical.dbusmenu'>
    <property name='Version' type='u' access='read'/>
    <property name='TextDirection' type='s' access='read'/>
    <property name='Status' type='s' access='read'/>
    <signal name='LayoutUpdated'><arg name='revision' type='u'/><arg name='parent' type='i'/></signal>
    <method name='GetLayout'><arg name='parentId' type='i' direction='in'/><arg name='recursionDepth' type='i' direction='in'/><arg name='propertyNames' type='as' direction='in'/><arg name='revision' type='u' direction='out'/><arg name='layout' type='(ia{sv}av)' direction='out'/></method>
    <method name='Event'><arg name='id' type='i' direction='in'/><arg name='eventId' type='s' direction='in'/><arg name='data' type='v' direction='in'/><arg name='timestamp' type='u' direction='in'/><arg name='id' type='i' direction='out'/></method>
    <method name='AboutToShow'><arg name='id' type='i' direction='in'/><arg name='needUpdate' type='b' direction='out'/></method>
  </interface>
</node>
"""

LAYOUT_TYPE = GLib.VariantType.new('(u(ia{sv}av))')


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
        with open(LOGFILE, 'a') as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass


def open_history_folder():
    """Open the folder where previous transcripts are kept."""
    try:
        subprocess.Popen(["xdg-open", HISTORY_DIR],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        log(f"history folder opened: {HISTORY_DIR}")
    except Exception as e:
        log(f"history folder open failed: {e}")


def open_file_picker():
    """Open a GTK file selection dialog for audio files.

    On selection, launch the progress-bar transcription window (a separate
    process) rather than transcribing directly here, so the progress bar can
    run independently of the tray's D-Bus handlers.
    """
    try:
        win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        win.set_skip_taskbar_hint(True)
        win.set_skip_pager_hint(True)
        win.set_focus_on_map(False)
        win.set_keep_above(True)
        win.show_all()

        dialog = Gtk.FileChooserDialog(
            title="Select audio file", parent=win,
            action=Gtk.FileChooserAction.OPEN)
        dialog.add_button("Open", Gtk.ResponseType.ACCEPT)
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        filter_audio = Gtk.FileFilter()
        filter_audio.set_name("Audio Files")
        filter_audio.add_mime_type("audio/*")
        dialog.add_filter(filter_audio)
        filter_m4a = Gtk.FileFilter()
        filter_m4a.set_name("M4A Files")
        filter_m4a.add_pattern("*.m4a")
        dialog.add_filter(filter_m4a)
        filter_wav = Gtk.FileFilter()
        filter_wav.set_name("WAV Files")
        filter_wav.add_pattern("*.wav")
        dialog.add_filter(filter_wav)
        filter_mp3 = Gtk.FileFilter()
        filter_mp3.set_name("MP3 Files")
        filter_mp3.add_pattern("*.mp3")
        dialog.add_filter(filter_mp3)
        filter_ogg = Gtk.FileFilter()
        filter_ogg.set_name("OGG Files")
        filter_ogg.add_pattern("*.ogg")
        dialog.add_filter(filter_ogg)
        filter_flac = Gtk.FileFilter()
        filter_flac.set_name("FLAC Files")
        filter_flac.add_pattern("*.flac")
        dialog.add_filter(filter_flac)

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filepath = dialog.get_filename()
            if filepath:
                prog = os.path.join(SCRIPT_DIR, "transcribe_progress.py")
                # Keep it detached so the progress window survives the tray's exit.
                subprocess.Popen(["/usr/bin/python3", prog, filepath],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 start_new_session=True)
                log(f"transcription started for {filepath}")
        dialog.destroy()
        win.destroy()
    except Exception as e:
        log(f"file picker failed: {e}")


class Tray:
    def __init__(self):
        self.conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.revision = 1

        sni = Gio.DBusNodeInfo.new_for_xml(SNI_XML)
        self.conn.register_object('/StatusNotifierItem', sni.interfaces[0],
                                  self._sni_call, self._sni_prop, None)
        menu = Gio.DBusNodeInfo.new_for_xml(MENU_XML)
        self.conn.register_object('/MenuBar', menu.interfaces[0],
                                  self._menu_call, self._menu_prop, None)

        self._own_bus_name()
        GLib.timeout_add(4000, self._ensure_registered)
        log('tray started')

    def _own_bus_name(self):
        try:
            Gio.bus_own_name_on_connection(self.conn, BUS_NAME,
                                           Gio.BusNameOwnerFlags.NONE, None)
        except Exception as e:
            log(f'bus_own_name failed: {e}')

    def _ensure_registered(self):
        try:
            reply = self.conn.call_sync(
                "org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher",
                "org.freedesktop.DBus.Properties", "Get",
                GLib.Variant("(ss)", ("org.kde.StatusNotifierWatcher",
                                      "RegisteredStatusNotifierItems")),
                None, Gio.DBusCallFlags.NONE, 4000, None)
            items = [str(v) for v in reply.unpack()[0]]
        except Exception:
            return True
        if not any(BUS_NAME in i for i in items):
            try:
                self.conn.call_sync(
                    "org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher",
                    "org.kde.StatusNotifierWatcher", "RegisterStatusNotifierItem",
                    GLib.Variant("(s)", (BUS_NAME,)), None,
                    Gio.DBusCallFlags.NONE, 4000, None)
                log('registered with tray watcher')
            except Exception as e:
                log(f'register failed: {e}')
        return True

    def _sni_prop(self, _conn, _sender, _path, _iface, prop):
        try:
            if prop == "Category":
                return GLib.Variant("s", "AudioVideo")
            if prop == "Id":
                return GLib.Variant("s", TRAY_ID)
            if prop == "Title":
                return GLib.Variant("s", "Transcribe")
            if prop == "Status":
                return GLib.Variant("s", "Active")
            if prop == "ItemIsMenu":
                return GLib.Variant("b", True)
            if prop == "IconName":
                return GLib.Variant("s", ICON_NAME)
            if prop == "Menu":
                return GLib.Variant("o", "/MenuBar")
            if prop == "ToolTip":
                n = len(os.listdir(HISTORY_DIR)) if os.path.isdir(HISTORY_DIR) else 0
                return GLib.Variant("(s(iiay)ss)",
                                    ("Transcribe", (0, 0, b""),
                                     "Audio File Transcriber", f"{n} saved"))
        except Exception as e:
            log(f"prop {prop} failed: {e}")
        return None

    def _sni_call(self, _conn, _sender, _path, _iface, method, params, invocation):
        try:
            if method == 'Activate':
                GLib.idle_add(open_file_picker)
            invocation.return_value(None)
        except Exception as e:
            log(f'{method} handler failed: {e}')
            try:
                invocation.return_value(None)
            except Exception:
                pass

    def _menu_prop(self, _conn, _sender, _path, _iface, prop):
        if prop == "Version":
            return GLib.Variant("u", 3)
        if prop == "TextDirection":
            return GLib.Variant("s", "ltr")
        if prop == "Status":
            return GLib.Variant("s", "normal")
        return None

    def _menu_call(self, _conn, _sender, _path, _iface, method, params,
                   invocation):
        try:
            if method == 'GetLayout':
                parts = []
                for rid, label in ((1, "transcribe"), (2, "History")):
                    props = [
                        '"label": <"{label}">'.format(label=self._esc(label)),
                        '"enabled": <true>',
                        '"visible": <true>',
                    ]
                    parts.append("<(%d, @a{sv} {%s}, @av [])>" % (rid, ", ".join(props)))
                layout = "(1, (0, @a{sv} {}, @av [%s]))" % ", ".join(parts)
                variant = GLib.Variant.parse(LAYOUT_TYPE, layout, None, None)
                invocation.return_value(variant)
            elif method == 'Event':
                try:
                    args = params.unpack()
                    rid, event_id = args[0], args[1]
                    if event_id in ("clicked", "pressed"):
                        if rid == 1:
                            GLib.idle_add(open_file_picker)
                        elif rid == 2:
                            GLib.idle_add(open_history_folder)
                    invocation.return_value(GLib.Variant("(i)", (rid,)))
                except Exception as e:
                    log(f"event unpack failed: {e}")
                    invocation.return_value(GLib.Variant("(i)", (0,)))
            elif method == 'AboutToShow':
                invocation.return_value(GLib.Variant("(b)", (False,)))
            else:
                invocation.return_value(None)
        except Exception as e:
            log(f"{method} handler failed: {type(e).__name__}: {e}")
            try:
                invocation.return_value(None)
            except Exception:
                pass

    @staticmethod
    def _esc(s):
        return s.replace("\\", "\\\\").replace('"', "\\\"")


def main():
    app = Gtk.Application(application_id=BUS_NAME,
                           flags=Gio.ApplicationFlags.NON_UNIQUE)
    app.connect('activate', lambda a: (Tray(), a.hold()))
    return app.run([])


if __name__ == '__main__':
    sys.exit(main())
