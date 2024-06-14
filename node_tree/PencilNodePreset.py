# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import os
import shutil
from bl_operators.presets import AddPresetBase
from ..i18n import Translation
from .misc import AttrOverride


brush_preset_props = (
    "brush_type",
    "brush_map_on_gui",
    "brush_map_opacity",
    "stretch",
    "stretch_random",
    "angle",
    "angle_random",
    "groove",
    "groove_number",
    "size",
    "size_random",
    "antialiasing",
    "horizontal_space",
    "horizontal_space_random",
    "vertical_space",
    "vertical_space_random",
    "reduction_start",
    "reduction_end",
)

stroke_preset_props = (
    "stroke_type",
    "line_type",
    "length",
    "length_random",
    "space",
    "space_random",
    "stroke_size_random",
    "extend",
    "extend_random",
    "line_copy",
    "line_copy_random",
    "normal_offset",
    "normal_offset_random",
    "x_offset",
    "x_offset_random",
    "y_offset",
    "y_offset_random",
    "line_split_angle",
    "min_line_length",
    "line_link_length",
    "line_direction",
    "loop_direction_type",
    "distortion_enabled",
    "distortion_map_on_gui",
    "distortion_map_amount",
    "distortion_amount",
    "distortion_random",
    "distortion_cycles",
    "distortion_cycles_random",
    "distortion_phase",
    "distortion_phase_random",
    "size_reduction_enabled",
    "size_reduction_curve_data_str",
    "alpha_reduction_enabled",
    "alpha_reduction_curve_data_str",
    "color_space_type",
    "color_space_red",
    "color_space_green",
    "color_space_blue",
    "color_space_hue",
    "color_space_saturation",
    "color_space_value",
)


class PCL4_MT_brush_presets(bpy.types.Menu):
    bl_label = ""
    preset_subdir = "Pencil+ 4 Line/brush"
    preset_operator = "pcl4.execute_brush_preset"
    draw = bpy.types.Menu.draw_preset

class PCL4_MT_stroke_presets(bpy.types.Menu):
    bl_label = ""
    preset_subdir = "Pencil+ 4 Line/stroke"
    preset_operator = "pcl4.execute_stroke_preset"
    draw = bpy.types.Menu.draw_preset

class AddPresetMixin(AddPresetBase):
    bl_translation_context = Translation.ctxt
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        node = bpy.context.space_data.edit_tree.nodes.active
        if not self.remove_active:
            for prop in self.preset_props:
                if AttrOverride.is_overrided(node, prop, context=context):
                    setattr(node, prop, AttrOverride.get_overrided_attr(node, prop, context=context))
        ret = super().execute(context)
        if self.remove_active:
            preset_menu_class = getattr(bpy.types, self.preset_menu)
            preset_menu_class.bl_label = ""
        return ret

    preset_defines = [
        "node = bpy.context.space_data.edit_tree.nodes.active"
    ]

    @property
    def preset_values(self) -> list:
        return [f"node.{prop}" for prop in self.preset_props]

class AddPresetBrush(AddPresetMixin, bpy.types.Operator):
    bl_idname = "pcl4.brush_preset_add"
    bl_label = "Add Pencil+ 4 Brush Preset"
    preset_menu = "PCL4_MT_brush_presets"
    preset_subdir = PCL4_MT_brush_presets.preset_subdir
    preset_props = brush_preset_props

class AddPresetStroke(AddPresetMixin, bpy.types.Operator):
    bl_idname = "pcl4.stroke_preset_add"
    bl_label = "Add Pencil+ 4 Stroke Preset"
    preset_menu = "PCL4_MT_stroke_presets"
    preset_subdir = PCL4_MT_stroke_presets.preset_subdir
    preset_props = stroke_preset_props


def __layout_preset(layout, label_text, menu_class, add_operator_class, default_operater_class):
    box = layout.box()
    col = box.column(align=True)
    col.label(text=label_text, text_ctxt=Translation.ctxt)

    split = col.split(factor=0.7)

    row = split.row(align=True)
    row.menu(menu_class.__name__, text=menu_class.bl_label, translate=False)
    row.operator(add_operator_class.bl_idname, text="", icon='ADD')
    row.operator(add_operator_class.bl_idname, text="", icon='REMOVE').remove_active = True

    row = split.row(align=True)
    row.operator(default_operater_class.bl_idname, text="Default", icon='LOOP_BACK', text_ctxt=Translation.ctxt)

    layout.separator(factor=2.0)

def layout_brush_preset(layout):
    __layout_preset(layout, "Brush Presets", PCL4_MT_brush_presets, AddPresetBrush, PCL4_OT_DefaultBrushPreset)

def layout_stroke_preset(layout):
    __layout_preset(layout, "Stroke Presets", PCL4_MT_stroke_presets, AddPresetStroke, PCL4_OT_DefaultStrokePreset)


class ExecutePresetMixin:
    bl_label = "Execute a Python Preset"
    bl_options = {"REGISTER", "UNDO"}
    filepath: bpy.props.StringProperty(
        subtype='FILE_PATH',
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        node = bpy.context.space_data.edit_tree.nodes.active
        ret = bpy.ops.script.execute_preset('INVOKE_DEFAULT', filepath=self.filepath, menu_idname=self.menu_idname)
        for prop in self.preset_props:
            if AttrOverride.is_overrided(node, prop, context=context):
                source, source_prop = AttrOverride.get_override_source(node, prop, context)
                source[source_prop] = getattr(node, prop)
        return ret

class PCL4_OT_ExecuteBrushPreset(ExecutePresetMixin, bpy.types.Operator):
    bl_idname = "pcl4.execute_brush_preset"
    menu_idname="PCL4_MT_brush_presets"
    preset_props = brush_preset_props

class PCL4_OT_ExecuteStrokePreset(ExecutePresetMixin, bpy.types.Operator):
    bl_idname = "pcl4.execute_stroke_preset"
    menu_idname="PCL4_MT_stroke_presets"
    preset_props = stroke_preset_props


class DefaultPresetMixin:
    bl_label = "Set Default Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        node = context.space_data.edit_tree.nodes.active
        for prop in self.preset_props:
            setattr(node, prop, node.bl_rna.properties[prop].default)
        self.menu_class.bl_label = ""
        return {"FINISHED"}

class PCL4_OT_DefaultBrushPreset(DefaultPresetMixin, bpy.types.Operator):
    bl_idname = "pcl4.default_brush_preset"
    preset_props = brush_preset_props
    menu_class = PCL4_MT_brush_presets

class PCL4_OT_DefaultStrokePreset(DefaultPresetMixin, bpy.types.Operator):
    bl_idname = "pcl4.default_stroke_preset"
    preset_props = stroke_preset_props
    menu_class = PCL4_MT_stroke_presets


def is_preset_installed(folder_path):
    if not os.path.exists(folder_path):
        return False
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.endswith('.py'):
            return True
    return False

def register():
    for type in ("brush", "stroke"):
        preset_folder = bpy.utils.user_resource('SCRIPTS', path=f"presets/Pencil+ 4 Line/{type}")
        if not is_preset_installed(preset_folder):
            try:
                shutil.copytree(os.path.join(os.path.dirname(__file__), f"../resources/presets/{type}"), preset_folder, dirs_exist_ok=True)
            except:
                pass
