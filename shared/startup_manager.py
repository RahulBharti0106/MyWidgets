import os
import sys


class StartupManager:
    REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @staticmethod
    def enable(app_name: str, exe_path: str = None):
        try:
            import winreg

            exe = exe_path
            if exe is None:
                exe = (
                    sys.executable
                    if getattr(sys, "frozen", False)
                    else f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                )
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                StartupManager.REG_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe)
        except Exception:
            pass

    @staticmethod
    def disable(app_name: str):
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                StartupManager.REG_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, app_name)
        except Exception:
            pass

    @staticmethod
    def is_enabled(app_name: str) -> bool:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, StartupManager.REG_KEY
            ) as key:
                winreg.QueryValueEx(key, app_name)
            return True
        except Exception:
            return False
