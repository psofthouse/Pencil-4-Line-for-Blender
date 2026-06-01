# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import importlib
import platform
import sys
from types import ModuleType

import bpy


def _get_cpp_module_name() -> str:
    platform_names = {
        "Windows": "win64",
        "Darwin": "mac",
        "Linux": "linux",
    }

    platform_name = platform_names.get(platform.system())
    if platform_name is None:
        raise ImportError(f"Unsupported platform for Pencil+ 4 binary module: {platform.system()}")

    py_ver = (sys.version_info.major, sys.version_info.minor)
    if py_ver == (3, 9):
        python_suffix = "39"
    elif py_ver == (3, 10):
        python_suffix = "310"
    elif py_ver == (3, 11):
        if bpy.app.version < (4, 5, 0):
            python_suffix = "311"
        elif bpy.app.version < (5, 0, 0):
            python_suffix = "311_450"
        else:
            python_suffix = "311_500"
    elif py_ver == (3, 13):
        python_suffix = "313"
    else:
        raise ImportError(
            "Unsupported Python version for Pencil+ 4 binary module: "
            f"{sys.version_info.major}.{sys.version_info.minor}"
        )

    return f"pencil4line_for_blender_{platform_name}_{python_suffix}"


def load_cpp_module(package: str, bin_package: str = ".bin") -> ModuleType:
    module_name = _get_cpp_module_name()
    return importlib.import_module(f"{bin_package}.{module_name}", package=package)
