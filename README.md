# MyWidgets

Desktop productivity widgets for Windows built with Python and PyQt6:

- `DesktopTodo`: a desktop to-do widget with due dates, reminders, tray support, and startup option
- `DesktopCalendar`: a desktop calendar widget that reads due dates from to-do tasks and shows indicator dots

## 🚀 Latest Release

### v1.0.0 - Initial Release

**Download**: [MyWidgets v1.0.0 Executable (.exe)](https://github.com/RahulBharti0106/MyWidgets/releases/tag/v1.0.0)

The first stable release of MyWidgets is now available for download. Simply download the `.exe` file and run it directly—no installation or Python knowledge required.

**What's Included**:

- ✨ Desktop To-Do widget with task management
- 📅 Calendar widget with visual task indicators
- 🎨 Dark and light theme support
- 🔔 Windows toast reminders for due tasks
- ⚙️ Customizable settings (position, size, opacity, theme)
- 🚀 Startup support (auto-run on Windows boot)
- 🎯 Frameless, always-on-top widgets that stay in the background

**Quick Start for Users**:

1. Download `DesktopTodo.exe` from the [releases page](https://github.com/RahulBharti0106/MyWidgets/releases/tag/v1.0.0)
2. Run the executable
3. Both To-Do and Calendar widgets will launch automatically
4. Right-click or drag widgets to customize them

[View Full Release Notes](https://github.com/RahulBharti0106/MyWidgets/releases/tag/v1.0.0)

## Features

- Frameless desktop widgets that stay in the background layer
- Drag to move and resize support
- Persistent settings (position, size, opacity, theme, startup)
- Dark and light mode through a shared theme config
- Optional Windows toast reminders for due tasks (To-Do widget)

## Project Structure

- `desktop_widget.py`: main To-Do widget
- `calendar_widget.py`: main Calendar widget
- `launch_all.py`: starts both widgets in one process
- `theme_config.py`: shared visual and behavior config
- `assets/icon.ico`: icon asset used for packaging
- `DesktopTodo.spec`: PyInstaller build spec (for executable build)

## Requirements

- Windows 10/11
- Python 3.10+ (only required for development/running from source)
- Packages (for development):
  - `PyQt6`
  - `winotify` (optional, for toast reminders)
  - `pyinstaller` (optional, only for building `.exe`)

## Setup

### For Users (Using Executable)

Simply download and run `DesktopTodo.exe` from the [latest release](https://github.com/RahulBharti0106/MyWidgets/releases/tag/v1.0.0). No installation steps needed!

### For Developers (From Source)

```powershell
git clone https://github.com/RahulBharti0106/MyWidgets.git
cd MyWidgets
python -m venv .venv
.venv\Scripts\activate
pip install PyQt6 winotify pyinstaller
```

## Run

Run both widgets:

```powershell
python launch_all.py
```

Run only To-Do:

```powershell
python desktop_widget.py
```

Run only Calendar:

```powershell
python calendar_widget.py
```

## Data Storage

Runtime data is stored in `%APPDATA%` (not in this repo):

- `%APPDATA%\MyWidgets\tasks.json`
- `%APPDATA%\MyWidgets\settings.json`
- `%APPDATA%\MyWidgets\calendar_settings.json`

## Build Executable (Optional)

To build the standalone executable yourself:

```powershell
pyinstaller MyWidgets.spec
```

Output executable:

- `dist\MyWidgets.exe`

**To run automatically on Windows startup**:

- Add `MyWidgets.exe` to your Windows Startup folder (`Shell:Startup`), or
- Use the app's built-in startup option in settings
