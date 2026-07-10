# MyWidgets

A Windows desktop productivity suite built with Python and PyQt6.

This repository contains two desktop widgets:

- `DesktopTodo`: a frameless, always-on-bottom to-do widget with due dates, reminders, categories, and a system tray menu.
- `DesktopCalendar`: a desktop calendar widget that displays badge counts for due tasks and supports day popups, navigation, and startup launch.

## Key Features

- Frameless, translucent desktop widgets that stay below other windows
- Drag to move widgets and resize them freely
- System tray integration for quick access, restore, and exit
- Persistent local settings for position, size, opacity, and startup behavior
- Optional Windows toast reminders for due and upcoming tasks (`winotify`)
- Calendar badge counts from pending To-Do due dates
- Support for task categories and important tasks

## Repository Layout

- `launch_all.py` - start both widgets together
- `todo/` - Desktop Todo app source
  - `todo/todo_widget.py` - main to-do widget
  - `todo/todo_ui.py` - to-do UI components and task list layout
  - `todo/todo_modal.py` - add task modal dialog
  - `todo/todo_logic.py` - task filtering and reminder logic
  - `todo/todo_data.py` - storage management for tasks and settings
  - `todo/todo_theme.py` - theme constants and styles
- `cal/` - Desktop Calendar app source
  - `cal/cal_widget.py` - main calendar widget
  - `cal/cal_ui.py` - calendar UI components and grid layout
  - `cal/cal_day_popup.py` - popup for day task details
  - `cal/cal_data.py` - calendar settings and due task count loader
  - `cal/cal_theme.py` - calendar theme styling
- `shared/` - shared utilities
  - `shared/startup_manager.py` - Windows startup registry helper
- `assets/` - icon and asset files
- `DesktopTodo.spec`, `MyWidgets.spec` - PyInstaller spec files

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- Required packages:
  - `PyQt6`
- Optional packages:
  - `winotify` (for Windows toast notifications)
  - `pyinstaller` (for building Windows executables)

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install PyQt6
pip install winotify  # optional
pip install pyinstaller  # optional
```

## Running the App

Start both widgets together:

```powershell
python launch_all.py
```

Start only the To-Do widget:

```powershell
python todo/todo_widget.py
```

Start only the Calendar widget:

```powershell
python cal/cal_widget.py
```

## Windows Startup Support

Both widgets can register themselves to run at Windows startup using the shared `StartupManager` utility in `shared/startup_manager.py`.

Startup entries are managed via the Windows registry key:

- `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`

## Auto-start on Windows boot 
To launch MyWidgets automatically when Windows starts:
1. Press Win + R, type shell:startup, press Enter
2. Right-click inside the folder → New → Shortcut
3. Point it to MyWidgets.exe inside the extracted folder
4. Click Finish

## Data Storage

User data is stored under `%APPDATA%`:

- `%APPDATA%\DesktopTodo\tasks.json`
- `%APPDATA%\DesktopTodo\settings.json`
- `%APPDATA%\DesktopCalendar\settings.json`

The calendar widget also reads due tasks from the To-Do storage to display badge counts.

## Release

Download the latest release from GitHub Releases:

- <https://github.com/RahulBharti0106/MyWidgets/releases/tag/V2.0>

---

If you want, I can also add a `requirements.txt` and a short user guide for the task creation workflow.
