#!/usr/bin/env python3
"""GUI interface for audio-file-transcriber.

Opens a file browser to select an audio file, then transcribes it.
"""
import os
import subprocess
import sys
import tempfile
import time

# First check if we have a valid input file argument
if len(sys.argv) > 1:
    input_file = sys.argv[1]
else:
    input_file = None

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GLib, Gdk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python")
TRANSPILE = os.path.join(SCRIPT_DIR, "transcribe")


class TranscriberApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Audio File Transcriber")
        self.set_default_size(400, 200)
        self.set_resizable(False)
        
        # CSS for dark theme
        css = b"""
        window { background-color: #1c1f26; }
        .card { background-color: #232732; border-radius: 10px; border: 1px solid #444; }
        .title { color: #c0caf5; font-weight: bold; font-size: 18px; }
        .subtitle { color: #898da9; font-size: 13px; margin-top: 5px; }
        button { min-height: 40px; margin: 8px; }
        """
        prov = Gtk.CssProvider()
        prov.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_border_width(20)
        self.add(main_box)
        
        # Title
        title = Gtk.Label(label="Audio File Transcriber")
        title.get_style_context().add_class("title")
        main_box.pack_start(title, False, False, 0)
        
        subtitle = Gtk.Label(label="Select an audio file to transcribe")
        subtitle.get_style_context().add_class("subtitle")
        main_box.pack_start(subtitle, False, False, 0)
        
        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        btn_browse = Gtk.Button(label="Browse Files...")
        btn_browse.connect("clicked", self.on_browse)
        btn_box.pack_start(btn_browse, True, True, 0)
        
        btn_folder = Gtk.Button(label="Open Folder")
        btn_folder.connect("clicked", self.on_open_folder)
        btn_box.pack_start(btn_folder, True, True, 0)
        
        main_box.pack_start(btn_box, False, False, 0)
        
        # Status bar
        self.status = Gtk.Label(label="Ready")
        self.status.get_style_context().add_class("subtitle")
        main_box.pack_start(self.status, False, False, 0)
        
        self.show_all()
    
    def on_browse(self, button):
        """Open file selection dialog."""
        dialog = Gtk.FileChooserDialog(
            "Select audio file",
            self,
            Gtk.FileChooserAction.OPEN,
            ("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.ACCEPT))
        
        # Add file filters
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
        
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filepath = dialog.get_filename()
            self.transcribe_file(filepath)
        dialog.destroy()
    
    def on_open_folder(self, button):
        """Open file selection dialog for folder."""
        dialog = Gtk.FileChooserDialog(
            "Select folder with audio files",
            self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            ("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.ACCEPT))
        
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            folder = dialog.get_filename()
            # List audio files and let user select
            self.select_from_folder(folder)
        dialog.destroy()
    
    def select_from_folder(self, folder):
        """List audio files in folder and let user select one."""
        try:
            files = sorted([f for f in os.listdir(folder) 
                          if f.lower().endswith(('.m4a', '.wav', '.mp3', '.ogg', '.flac'))])
        except OSError:
            files = []
        
        if not files:
            dialog = Gtk.MessageDialog(
                self, 0, Gtk.MessageType.INFO,
                Gtk.ButtonsType.OK, "No audio files found in this folder.")
            dialog.run()
            dialog.destroy()
            return
        
        # Create selection dialog
        list_model = Gtk.ListStore(str, str)  # filename, fullpath
        for f in files:
            list_model.append([f, os.path.join(folder, f)])
        
        dialog = Gtk.Dialog("Select file", self, Gtk.DialogFlags.MODAL, 
                          (Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                           Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        dialog.set_default_size(400, 300)
        
        # Tree view
        tree = Gtk.TreeView(model=list_model)
        col = Gtk.TreeViewColumn("Audio Files", Gtk.CellRendererText(), text=0)
        tree.append_column(col)
        dialog.get_content_area().pack_start(tree)
        
        dialog.show_all()
        
        # Handle selection
        selection = tree.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        
        def on_ok(btn):
            model, iter = selection.get_selected()
            if iter:
                filepath = model[iter][1]
                dialog.response(Gtk.ResponseType.ACCEPT)
                self.transcribe_file(filepath)
            else:
                dialog.response(Gtk.ResponseType.REJECT)
        
        dialog.connect("response", lambda d, r: d.destroy() if r != Gtk.ResponseType.ACCEPT else None)
        dialog.connect("key_press_event", lambda w, e: dialog.response(Gtk.ResponseType.CANCEL) if e.keyval == Gdk.KEY_Escape else None)
        
        dialog.show_all()
    
    def transcribe_file(self, filepath):
        """Run the transcription."""
        self.status.set_text(f"Transcribing: {os.path.basename(filepath)}...")
        self.get_window().force_relocate()
        Gtk.main_iteration()
        
        try:
            result = subprocess.run(
                [PYTHON, TRANSPILE, filepath],
                capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Success - show notification with preview
                output_file = os.path.splitext(filepath)[0] + ".docx"
                if os.path.exists(output_file):
                    self.status.set_text(f"Done! Created: {os.path.basename(output_file)}")
                else:
                    self.status.set_text("Transcription complete!")
                
                # Show result in a dialog
                dlg = Gtk.MessageDialog(
                    self, Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK, "Transcription Complete!")
                dlg.format_secondary_text(f"File: {os.path.basename(filepath)}\nOutput: {os.path.basename(output_file)}")
                dlg.run()
                dlg.destroy()
            else:
                self.status.set_text(f"Error: {result.stderr[:100]}")
        
        except subprocess.TimeoutExpired:
            self.status.set_text("Error: Transcription timed out")
        except Exception as e:
            self.status.set_text(f"Error: {str(e)}")


def main():
    app = TranscriberApp()
    app.connect("destroy", Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    main()