# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

from cProfile import label
from cgitb import text
import bpy
from ..nodes.BrushDetailNode import BrushDetailNode
from ..PencilNodeTree import PencilNodeTree
from ..misc import GuiUtils
from ...i18n import Translation

def split2_property(layout, data, property: str, label:str, text: str, left_right: int=0):
    split = layout.split(factor=0.4)
    row = split.row()
    row.alignment = "RIGHT"
    row.label(text=label, text_ctxt=Translation.ctxt)
    split = split.split(factor=1.0)
    row = split.row(align=True)
    row.use_property_split = False

    def dummy():
        row1 = row.row()
        row1.enabled = False
        row1.operator("pcl4.activate_node", text="", emboss=False, text_ctxt=Translation.ctxt) # dummy

    if left_right != 0:
        dummy()
    row.prop(data, property, text=text, text_ctxt=Translation.ctxt)
    if left_right == 0:
        dummy()


class PCL4_PT_brush_detail_mixin:
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"

    @classmethod
    def poll(cls, context):
        return context.active_node is not None and isinstance(context.active_node, BrushDetailNode) and PencilNodeTree.show_node_params(context)


class PCL4_PT_brush_detail_brush_editor(PCL4_PT_brush_detail_mixin, bpy.types.Panel):
    bl_label = "Brush Editor"
    bl_translation_context = Translation.ctxt
    bl_order = 101
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = PencilNodeTree.tree_from_context(context).is_entity()
        node = context.active_node

        GuiUtils.enum_property(layout, node, "brush_type", BrushDetailNode.brush_type_items, text="Brush Type")
        type = getattr(node, "brush_type", "SIMPLE")

        def prop_pair(prop_name0, label_text0, prop_name1, label_text1):
            row = col.row(align=True)
            row.prop(node, prop_name0, text=label_text0, text_ctxt=Translation.ctxt)
            row.prop(node, prop_name1, text=label_text1, text_ctxt=Translation.ctxt)

        col = layout.column(align=True)
        col.enabled = type != "SIMPLE"
        GuiUtils.map_property(col, node, "brush_map", "Brush Map",
                                         "brush_map_opacity", "Opacity")
                                         
        col = layout.column(align=True)
        prop_pair("stretch", "Stretch", "stretch_random", "Random")
        prop_pair("angle", "Angle", "angle_random", "Random")

        col = layout.column(align=True)
        col.enabled = type != "SIMPLE"
        prop_pair("groove", "Groove", "groove_number", "Number")
        
        col = layout.column(align=True)
        col.enabled = type == "MULTIPLE"
        prop_pair("size", "Size", "size_random", "Random")
        split2_property(col, node, "antialiasing", label="Antialiasing", text="", left_right=0)
        prop_pair("horizontal_space", "Horizontal Space", "horizontal_space_random", "Random")
        prop_pair("vertical_space", "Vertical Space","vertical_space_random", "Random")

        row = layout.row()
        row.enabled = type != "SIMPLE"
        split = row.split(factor=0.4)
        split.use_property_split = False
        row = split.row(align=True)
        row.alignment = "RIGHT"
        row.label(text="Reduction", text_ctxt=Translation.ctxt)
        split = split.split(factor=1.0)
        row = split.row(align=True)
        row.prop(node, "reduction_start", text="Start", text_ctxt=Translation.ctxt)
        row.prop(node, "reduction_end", text="End", text_ctxt=Translation.ctxt)


class PCL4_PT_brush_detail_stroke(PCL4_PT_brush_detail_mixin, bpy.types.Panel):
    bl_label = "Stroke"
    bl_translation_context = Translation.ctxt
    bl_order = 102

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = PencilNodeTree.tree_from_context(context).is_entity()
        node = context.active_node

        def prop(prop_name, label_text):
            col.prop(node, prop_name, text=label_text, text_ctxt=Translation.ctxt)
        def prop_pair(prop_name0, label_text0, prop_name1, label_text1):
            row = col.row(align=True)
            row.prop(node, prop_name0, text=label_text0, text_ctxt=Translation.ctxt)
            row.prop(node, prop_name1, text=label_text1, text_ctxt=Translation.ctxt)

        col = layout.column(align=True)
        col.enabled = getattr(node, "brush_type", "SIMPLE") != "SIMPLE"
        GuiUtils.enum_property(col, node, "stroke_type", BrushDetailNode.stroke_type_items, text="Stroke Type")

        col = layout.column(align=True)
        GuiUtils.enum_property(col, node, "line_type", BrushDetailNode.line_type_items, text="Line Type")
        col = col.column(align=True)
        col.enabled = getattr(node, "line_type", "FULL") != "FULL"
        prop_pair("length", "Length", "length_random", "Random")
        prop_pair("space", "Space", "space_random", "Random")

        col = layout.column(align=True)
        split2_property(col, node, "stroke_size_random", label="Size", text="Random", left_right=1)
        prop_pair("extend", "Extend", "extend_random", "Random")
        prop_pair("line_copy", "Line Copy", "line_copy_random", "Random")
        prop_pair("normal_offset", "Normal Offset", "normal_offset_random", "Random")
        prop_pair("x_offset", "X Offset", "x_offset_random", "Random")
        prop_pair("y_offset", "Y Offset", "y_offset_random", "Random")

        col = layout.column(align=True)
        prop("line_split_angle", "Line Split Angle")
        prop("min_line_length", "Min Line Length")
        prop("line_link_length", "Line Link Length")
        prop("line_direction", "Line Direction (Angle)")
        GuiUtils.enum_property(col, node, "loop_direction_type", reversed(BrushDetailNode.loop_direction_items), text="Loop Direction")


class PCL4_PT_brush_detail_distortion(PCL4_PT_brush_detail_mixin, bpy.types.Panel):
    bl_label = ""
    bl_translation_context = Translation.ctxt
    bl_order = 103

    def draw_header(self, context):
        layout = self.layout
        node = context.active_node
        layout.prop(node, "distortion_enabled", text="Distortion", text_ctxt=Translation.ctxt)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = PencilNodeTree.tree_from_context(context).is_entity()
        node = context.active_node

        def prop_pair(prop_name0, label_text0, prop_name1, label_text1):
            row = col.row(align=True)
            row.prop(node, prop_name0, text=label_text0, text_ctxt=Translation.ctxt)
            row.prop(node, prop_name1, text=label_text1, text_ctxt=Translation.ctxt)

        col = layout.column(align=True)
        col.enabled = getattr(node, "distortion_enabled", False)

        GuiUtils.map_property(col, node, "distortion_map", "Distortion Map",
                                         "distortion_map_amount", "Amount")

        col = layout.column(align=True)
        prop_pair("distortion_amount", "Amount", "distortion_random", "Random")
        prop_pair("distortion_cycles", "Cycles", "distortion_cycles_random", "Random")
        prop_pair("distortion_phase", "Phase", "distortion_phase_random", "Random")


class PCL4_PT_brush_detail_size_reduction(PCL4_PT_brush_detail_mixin, bpy.types.Panel):
    bl_label = ""
    bl_translation_context = Translation.ctxt
    bl_order = 104

    def draw_header(self, context):
        layout = self.layout
        node = context.active_node
        layout.prop(node, "size_reduction_enabled", text="Stroke Size Reduction Settings", text_ctxt=Translation.ctxt)

    def draw(self, context):
        layout = self.layout
        node = context.active_node
        layout.enabled = getattr(node, "size_reduction_enabled", False) and\
                PencilNodeTree.tree_from_context(context).is_entity()

        data = node.get_curve_data(node.size_reduction_curve)
        if data is not None:
            layout.template_curve_mapping(data, "mapping")


class PCL4_PT_brush_detail_alpha_reduction(PCL4_PT_brush_detail_mixin, bpy.types.Panel):
    bl_label = ""
    bl_translation_context = Translation.ctxt
    bl_order = 105

    def draw_header(self, context):
        layout = self.layout
        node = context.active_node
        layout.prop(node, "alpha_reduction_enabled", text="Stroke Alpha Reduction Settings", text_ctxt=Translation.ctxt)

    def draw(self, context):
        layout = self.layout
        node = context.active_node
        layout.enabled = getattr(node, "alpha_reduction_enabled", False) and\
                PencilNodeTree.tree_from_context(context).is_entity()

        data = node.get_curve_data(node.alpha_reduction_curve)
        if data is not None:
            layout.template_curve_mapping(data, "mapping")


class PCL4_PT_brush_detail_color_range(PCL4_PT_brush_detail_mixin, bpy.types.Panel):
    bl_label = "Color Range"
    bl_translation_context = Translation.ctxt
    bl_order = 106

    def draw(self, context):
        layout = self.layout
        layout.enabled = PencilNodeTree.tree_from_context(context).is_entity()
        node = context.active_node

        col = layout.column(align=True)

        row = col.row()
        row.prop(node, "color_space_type", expand=True)

        def prop(prop_name, label_text):
            row.prop(node, prop_name, text=label_text, text_ctxt=Translation.ctxt)
        row = col.row(align=True)
        if node.color_space_type == "RGB":
            prop("color_space_red", "R")
            prop("color_space_green", "G")
            prop("color_space_blue", "B")
        else:
            prop("color_space_hue", "H")
            prop("color_space_saturation", "S")
            prop("color_space_value", "V")
