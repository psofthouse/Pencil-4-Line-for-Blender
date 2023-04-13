# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy

from ..nodes.BrushSettingsNode import BrushSettingsNode
from ..misc import GuiUtils
from ..PencilNodeTree import PencilNodeTree
from ...i18n import Translation

class PCL4_PT_brush_settings_base:
    bl_label = "Brush"
    bl_translation_context = Translation.ctxt
    bl_options = {"HEADER_LAYOUT_EXPAND"}
    
    @classmethod
    def poll(cls, context):
        return context.active_node is not None and isinstance(context.active_node, BrushSettingsNode)
    
    def draw(self, context):
        layout = self.layout
        layout.enabled = PencilNodeTree.tree_from_context(context).is_entity()
        layout.use_property_split = True
        layout.use_property_decorate = False
        node = self.brush_settings_node(context)
        if node is None:
            return

        col = layout.column(align=True)

        def prop_pair(prop_name0, label_text0, prop_name1, label_text1):
            row = col.row(align=True)
            row.prop(node, prop_name0, text=label_text0, text_ctxt=Translation.ctxt)
            row.prop(node, prop_name1, text=label_text1, text_ctxt=Translation.ctxt)

        col.enabled = self.brush_settings_enabled(context)

        prop_pair("brush_color", "Color", "blend_amount", "Blend Amount")
        GuiUtils.map_property(col, node, "color_map", "Color Map",
                                         "color_map_opacity", "Opacity")

        col = layout.column(align=True)
        col.prop(node, "size", text="Size", text_ctxt=Translation.ctxt)
        GuiUtils.map_property(col, node, "size_map", "Size Map",
                                         "size_map_amount", "Amount")

        # 配下のBrushDetailのStretchとAngleを表示する
        brush_detail = next(x for x in node.inputs).get_connected_node()

        if brush_detail is None:
            return

        col = layout.column(align=True)
        col.prop(brush_detail, "stretch", text="Stretch", text_ctxt=Translation.ctxt)
        col.prop(brush_detail, "angle", text="Angle", text_ctxt=Translation.ctxt)

    @classmethod
    def brush_settings_node(cls, context):
        return context.active_node

    @classmethod
    def brush_settings_enabled(cls, context):
        return True

class PCL4_PT_brush_settings(PCL4_PT_brush_settings_base, bpy.types.Panel):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"
    bl_order = 100

    @classmethod
    def poll(cls, context):
        return super().poll(context) and PencilNodeTree.show_node_params(context)
