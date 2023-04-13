# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy

from ..nodes.TextureMapNode import TextureMapNode
from ..PencilNodeTree import PencilNodeTree
from ...i18n import Translation


class PCL4_PT_brush_detail_mixin:
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"
    bl_translation_context = Translation.ctxt

    @classmethod
    def poll(cls, context):
        return context.active_node is not None and isinstance(context.active_node, TextureMapNode) and PencilNodeTree.show_node_params(context)


class PCL4_PT_texture_map_type(PCL4_PT_brush_detail_mixin, bpy.types.Panel):
    bl_label = "Source Type"
    bl_order = 100
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.enabled = PencilNodeTree.tree_from_context(context).is_entity()
        node = context.active_node

        row = layout.row(align=True)
        row.prop_enum(node, "source_type", "IMAGE", text_ctxt=Translation.ctxt)
        row.prop_enum(node, "source_type", "OBJECTCOLOR", text_ctxt=Translation.ctxt)


class PCL4_PT_texture_map_image_uv(PCL4_PT_brush_detail_mixin, bpy.types.Panel):
    bl_label = "Image and UV"
    bl_order = 101
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        return super().poll(context) and context.active_node.source_type == "IMAGE"
        
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = PencilNodeTree.tree_from_context(context).is_entity()
        node = context.active_node

        col = layout.column(align=True)
        col.template_ID(node, "image", new="image.new", open="image.open")

        col = layout.column(align=True)
        col.prop(node, "wrap_mode_u", text="Wrap Mode U", text_ctxt=Translation.ctxt)
        col.prop(node, "wrap_mode_v", text="V", text_ctxt=Translation.ctxt)

        col = layout.column(align=True)
        col.prop(node, "filter_mode", text="Filter Mode", text_ctxt=Translation.ctxt)

        col = layout.column(align=True)
        col.prop(node, "uv_source", text="UV Source", text_ctxt=Translation.ctxt)

        row = col.row()
        row.enabled = node.uv_source == "OBJECTUV"
        row.prop(node, "uv_selection_mode", text="Selection Mode", text_ctxt=Translation.ctxt)
        row = col.row()
        row.enabled = node.uv_source == "OBJECTUV" and node.uv_selection_mode == "INDEX"
        row.prop(node, "uv_index", text="Index", text_ctxt=Translation.ctxt)
        row = col.row()
        row.enabled = node.uv_source == "OBJECTUV" and node.uv_selection_mode == "NAME"
        row.prop(node, "uv_name", text="Name", text_ctxt=Translation.ctxt)

        col = layout.column(align=True)
        col.prop(node, "tiling", index=0, text="Tiling U", text_ctxt=Translation.ctxt)
        col.prop(node, "tiling", index=1, text="V", text_ctxt=Translation.ctxt)

        col = layout.column(align=True)
        col.prop(node, "offset", index=0, text="Offset U", text_ctxt=Translation.ctxt)
        col.prop(node, "offset", index=1, text="V", text_ctxt=Translation.ctxt)


class PCL4_PT_texture_map_object_color(PCL4_PT_brush_detail_mixin, bpy.types.Panel):
    bl_label = "Color Attribute"
    bl_order = 102
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        return super().poll(context) and context.active_node.source_type == "OBJECTCOLOR"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = PencilNodeTree.tree_from_context(context).is_entity()
        node = context.active_node

        col = layout.column(align=True)
        col.prop(node, "object_color_selection_mode", text="Selection Mode", text_ctxt=Translation.ctxt)
        row = col.row()
        row.enabled = node.object_color_selection_mode == "INDEX"
        row.prop(node, "object_color_index", text="Index", text_ctxt=Translation.ctxt)
        row = col.row()
        row.enabled = node.object_color_selection_mode == "NAME"
        row.prop(node, "object_color_name", text="Name", text_ctxt=Translation.ctxt)
