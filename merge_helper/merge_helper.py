# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

if "bpy" in locals():
    import imp
    imp.reload(Translation)
else:
    from ..i18n import Translation

import bpy
from ..node_tree import PencilNodeTree


def link():
    for obj in (obj for obj in bpy.data.objects if obj.get("pencil4_node_trees") is not None):
        obj["pencil4_node_trees"] = PencilNodeTree.enumerate_entity_trees()

def unlink():
    for obj in (obj for obj in bpy.data.objects if obj.get("pencil4_node_trees") is not None):
        obj["pencil4_node_trees"] = []

class PCL4_OT_AddLineMergeHelper(bpy.types.Operator):
    bl_idname = "pcl4.add_line_merge_helper"
    bl_label = "Line Merge Helper"
    bl_options = {'REGISTER', 'UNDO'}
    bl_translation_context = Translation.ctxt

    def execute(self, context):
        ret = bpy.ops.object.empty_add()
        if ret != {'FINISHED'}:
            return ret

        new_object = bpy.context.active_object
        new_object.name = "Pencil+ 4 Line Merge Helper"
        new_object["pencil4_node_trees"] = []

        return {'FINISHED'}


class PCL4_MT_LineMergeHelper(bpy.types.Menu):
    bl_label = 'Pencil+ 4'
    bl_idname = 'PCL4_MT_LineMergeHelper'

    def draw(self, context):
        layout = self.layout
        layout.operator(PCL4_OT_AddLineMergeHelper.bl_idname)


def menu_fn(self, context):
    layout = self.layout
    layout.separator()
    self.layout.menu(PCL4_MT_LineMergeHelper.bl_idname)


def register_menu():
    bpy.types.VIEW3D_MT_add.append(menu_fn)


def unregister_menu():
    bpy.types.VIEW3D_MT_add.remove(menu_fn)    