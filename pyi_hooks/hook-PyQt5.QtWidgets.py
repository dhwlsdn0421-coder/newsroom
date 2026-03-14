# Custom hook: use PyQt5.__file__ for plugin path (avoids ??? with non-ASCII user paths on Windows)
import os
import PyQt5
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils import misc

hiddenimports = collect_submodules("PyQt5.QtWidgets")

binaries = []
plugins_src = os.path.join(os.path.dirname(PyQt5.__file__), "Qt5", "plugins", "platforms")
plugin_dst = os.path.join("PyQt5", "Qt5", "plugins", "platforms")
if os.path.isdir(plugins_src):
    for f in misc.dlls_in_dir(plugins_src):
        if not (os.path.basename(f).lower().endswith("d.dll")):  # skip debug
            binaries.append((f, plugin_dst))

datas = []
