# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

if "bpy" in locals():
    import imp
    imp.reload(Translation)
else:
    from ..i18n import Translation

import bpy

class PCL4_PT_LineMergeGroupPanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "collection"
    bl_label = "Pencil+ 4 Line Group"
    bl_translation_context = Translation.ctxt

    bl_order = 10000

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        collection = context.collection

        layout.prop(collection, "pcl4_line_merge_group", text="On")

def register_props():
    bpy.types.Collection.pcl4_line_merge_group = bpy.props.BoolProperty()

def unregister_props():
    pass