# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

bl_info = {
    "name": "PSOFT Pencil+ 4 Line",
    "author": "P SOFTHOUSE",
    "description": "High-quality lines in Blender [f1d867f1]",
    "blender": (3, 0, 0),
    "version": (4, 0, 6),
    "location": "",
    "warning": "",
    "category": "Generic",
    "doc_url": "https://github.com/psofthouse/Pencil-4-Line-for-Blender"
}

if "bpy" in locals():
    import imp
    imp.reload(pencil4_handler)
    imp.reload(pencil4_compositing)
    imp.reload(pencil4_render_images)
    imp.reload(PencilLineMergeGroup)
    imp.reload(Translation)
    imp.reload(merge_helper)
    imp.reload(pencil4_viewport)
    imp.reload(pencil4_preferences)
else:
    from . import pencil4_handler
    from . import pencil4_compositing
    from . import pencil4_render_images
    from . import pencil4_viewport
    from .node_tree import PencilLineMergeGroup
    from .i18n import Translation
    from .merge_helper import merge_helper
    from . import pencil4_preferences


import bpy
import os.path
import platform

from . import auto_load
from . import node_tree

auto_load.init()

def update_after_addon_loaded():
    for tree in (t for t in bpy.data.node_groups if isinstance(t, node_tree.PencilNodeTree) and t.first_update):
        tree.update()

def register():
    bpy.app.translations.register(__name__, Translation.translation_dict)
    auto_load.register()
    node_tree.register()
    pencil4_handler.append()
    pencil4_compositing.register_menu()
    PencilLineMergeGroup.register_props()
    pencil4_render_images.register_props()
    merge_helper.register_menu()
    pencil4_viewport.register_props()

    if not os.path.isfile(bpy.context.preferences.addons[__package__].preferences.render_app_path):
        bpy.context.preferences.addons[__package__].preferences.render_app_path = ""
    if bpy.context.preferences.addons[__package__].preferences.render_app_path == "":
        data = None
        regtype = None
        if platform.system() == "Windows":
            try:
                import winreg
                key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, r"SOFTWARE\PSOFT\Pencil+ 4 Render App")
                data, regtype = winreg.QueryValueEx(key, "RenderApp")
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass
            finally:
                if data is not None and regtype == winreg.REG_SZ:
                    bpy.context.preferences.addons[__package__].preferences.render_app_path = data

    if not bpy.app.background:
        bpy.app.timers.register(update_after_addon_loaded, first_interval=0.0)

def unregister():
    pencil4_viewport.unregister_props()
    merge_helper.unregister_menu()
    pencil4_render_images.unregister_props()
    PencilLineMergeGroup.unregister_props()
    pencil4_compositing.unregister_menu()
    pencil4_handler.remove()
    node_tree.unregister()
    auto_load.unregister()
    bpy.app.translations.unregister(__name__)

if __name__ == "__main__":
    register()
