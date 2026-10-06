# Audio File Transcriber

Local transcription of audio files (m4a, wav, mp3, etc.) using faster-whisper.

## Usage

### Command Line

```bash
# Navigate to app directory
cd ~/DEVELOPMENT/audio-file-transcriber

# Activate virtual environment
source .venv/bin/activate

# Transcribe an audio file (creates .docx by default)
python transcribe "/path/to/file.m4a"

# Specify output format explicitly
python transcribe input.m4a output.txt   # Plain text
python transcribe input.m4a output.docx  # Word document

# Use smaller/faster model
python transcribe input.m4a --model tiny

# Auto-detect language
python transcribe input.m4a --lang auto
```

### With Launcher (File Picker)

```bash
./launch --pick           # Opens file selection dialog, creates .docx
./launch input.m4a        # Transcribes specific file
./launch input.m4a output.txt  # With explicit output
```

## Models

Set `AFT_MODEL` environment variable or `--model` flag:
- `tiny` - Fastest, poor quality (smoke test)
- `base` - Default, ~10x realtime on CPU
- `small` - Noticeably better quality, ~3x slower

## Language

Set `AFT_LANG` environment variable or `--lang` flag:
- `en`, `es`, `fr`, etc. - Specific language
- `auto` - Auto-detect

## Output Format

By default, creates a **Word document (.docx)** with properly formatted paragraphs (4 sentences per paragraph).

To get plain text instead:
```bash
python transcribe input.m4a output.txt
```

## System Tray Integration

Drag the `audio-file-transcriber.desktop` file to your panel/top tray for quick access. This provides:
- Right-click menu with "Transcribe File..." option
- File browser to locate M4A files
- Automatic Word document output

To install the desktop entry:
```bash
cp /home/bigzo/DEVELOPMENT/audio-file-transcriber/audio-file-transcriber.desktop ~/.local/share/applications/
```

Then right-click the tray icon and "Add to Panel" or "Keep in System Tray".

## Hotkey Binding (Omarchy)

Add to `~/.config/hypr/bindings.lua`:

```lua
# Transcribe with file picker
bind = SUPER, V, exec, "$HOME/DEVELOPMENT/audio-file-transcriber/launch --pick"
```

## Output Locations

- Word documents: Same directory as input file with `.docx` extension
- Plain text: Same directory as input file with `.txt` extension  
- Log file: `~/.cache/audio-file-transcriber/transcribe.log`
- Transcript printed to stdout

## Dependencies

- Python 3.13+
- faster-whisper
- numpy
- ffmpeg
- python-docx (for Word output)