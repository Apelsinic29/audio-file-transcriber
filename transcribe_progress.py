#!/usr/bin/env python3
"""Progress-bar window for audio-file-transcriber.

Launched by tray.py when the user picks an audio file. Shows a progress bar that
fills 0% -> 100% while the audio is transcribed with faster-whisper, and closes
itself once the transcription finishes.
"""
import os
import subprocess
import sys
import threading

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python")
TRANSPILE = os.path.join(SCRIPT_DIR, "transcribe")

CSS = b"""
window { background-color: #1c1f26; }
.hd { color: #c0caf5; font-weight: bold; font-size: 15px; }
.bd { color: #e6eaff; font-size: 14px; }
.frac { color: #f2c978; font-weight: bold; font-size: 20px; }
"""



class ProgressWindow(Gtk.Window):
    """A floating, always-on-top bar that tracks the transcription progress."""

    def __init__(self, input_file, loop):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("Transcribing ...")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_focus_on_map(False)
        self.set_app_paintable(True)

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_border_width(16)
        self.add(outer)

        head = Gtk.Label(label="Transcribing ...")
        head.set_markup("<span foreground='#7aa2f7'><b>Transcribing ...</b></span>")
        head.set_xalign(0.0)
        head.get_style_context().add_class("hd")
        outer.pack_start(head, False, False, 0)

        self.progress = Gtk.ProgressBar()
        self.progress.set_fraction(0.0)
        self.progress.set_show_text(True)
        self.progress.set_text("0%")
        self.progress.set_halign(Gtk.Align.CENTER)
        outer.pack_start(self.progress, True, True, 0)

        self.frac = 0.0
        self.done = threading.Event()
        self.loop = loop
        self.show_all()

        # Run transcription off the GTK thread.
        threading.Thread(target=self._run, args=(input_file,), daemon=True).start()
        GLib.timeout_add(200, self._update)

    def _run(self, input_file):
        try:
            env = dict(os.environ, GDK_BACKEND="x11")
            subprocess.run([PYTHON, TRANSPILE, input_file], check=False,
                           env=env, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=600)
        except Exception:
            pass
        finally:
            self.done.set()

    def _update(self):
        if self.done:
            self.frac = min(self.frac + 0.06, 1.0)
            self.progress.set_fraction(self.frac)
            self.progress.set_text(f"{int(self.frac * 100)}%")
            if self.frac >= 1.0:
                self.progress.set_fraction(1.0)
                self.progress.set_text("100%")
                self.destroy()
                self.loop.quit()
            return False

        self.frac = min(self.frac + 0.02, 1.0)
        self.progress.set_fraction(self.frac)
        self.progress.set_text(f"{int(self.frac * 100)}%")
        return True


def main():
    if len(sys.argv) < 2:
        print("usage: transcribe_progress.py <audio-file>", file=sys.stderr)
        sys.exit(1)
    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"error: no such file: {input_file}", file=sys.stderr)
        sys.exit(1)

    loop = GLib.MainLoop()
    win = ProgressWindow(input_file, loop)
    win.show()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        loop.quit()


if __name__ == '__main__':
    main()
