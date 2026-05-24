import pathlib
import runpy

_app_path = pathlib.Path(__file__).with_name("app_backup.py")
runpy.run_path(str(_app_path), run_name="__main__")
