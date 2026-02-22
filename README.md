# MyWidgets

Desktop productivity widgets for Windows built with Python and PyQt6:

- `DesktopTodo`: a desktop to-do widget with due dates, reminders, tray support, and startup option
- `DesktopCalendar`: a desktop calendar widget that reads due dates from to-do tasks and shows indicator dots

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
- Python 3.10+
- Packages:
  - `PyQt6`
  - `winotify` (optional, for toast reminders)
  - `pyinstaller` (optional, only for building `.exe`)

## Setup

```powershell
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

- `%APPDATA%\DesktopTodo\tasks.json`
- `%APPDATA%\DesktopTodo\settings.json`
- `%APPDATA%\DesktopCalendar\settings.json`

## Build Executable (Optional)

```powershell
pyinstaller DesktopTodo.spec
```

Output executable:

- `dist\DesktopTodo.exe`

- Add DesktopTodo.exe in Shell:Startup folder to run it automatically

## GitHub

- Repository: https://github.com/RahulBharti0106/MyWidgets
- Download v1.0.0 (.exe): https://github.com/RahulBharti0106/MyWidgets/releases/tag/v1.0.0
