# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import math
import bpy

from .PencilNodeMixin import PencilNodeMixin
from .PencilNodeSockets import *
from ..misc.PencilCurves import *
from ...i18n import Translation

BRUSH_MAP_SOCKET_ID = "brush_map"
DISTORTION_MAP_SOCKET_ID = "distortion_map"

class BrushDetailNode(bpy.types.Node, PencilNodeMixin):
    """Blush Detail Node"""
    bl_idname = "Pencil4BrushDetailNodeType"
    bl_label = "Brush Detail"
    bl_icon = "GREASEPENCIL"

    new_node_offset_x = -160
    new_node_offset_y = -60
    new_node_step_y = -60

    brush_type_items = (
        ("NORMAL", "Normal", "Normal", 0),
        ("MULTIPLE", "Multiple", "Multiple", 1),
        ("SIMPLE", "Simple", "Simple", 2)
    )

    stroke_type_items = (
        ("NORMAL", "Normal", "Normal", 0),
        ("RAKE", "Rake", "Rake", 1),
        ("RANDOM", "Random", "Random", 2),
    )

    line_type_items = (
        ("FULL", "Full", "Full", 0),
        ("DASHED", "Dashed", "Dashed", 1)
    )

    loop_direction_items = (
        ("CLOCKWISE", "Clockwise", "Clockwise", 0),
        ("ANTICLOCKWISE", "Anticlockwise", "Anticlockwise", 1),
    )

    color_space_items = (
        ("RGB", "RGB", "RGB", 0),
        ("HSV", "HSV", "HSV", 1)
    )

    # Brush Editor
    brush_type: bpy.props.EnumProperty(items=brush_type_items, default="SIMPLE")
    brush_map_on: bpy.props.BoolProperty(default=False)
    brush_map_on_gui: bpy.props.BoolProperty(get=lambda self: self.brush_map_on, set=lambda self, value: setattr(self, "brush_map_on", value),
        update=lambda self, ctx: self.auto_create_node_when_property_on(ctx, BRUSH_MAP_SOCKET_ID))
    # brush_map
    brush_map: bpy.props.StringProperty(
        default=BRUSH_MAP_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(BRUSH_MAP_SOCKET_ID) if self.brush_type != "SIMPLE" else "",
        set=lambda self, val: None)
    brush_map_opacity: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)
    stretch: bpy.props.FloatProperty(default=0.0, min=-1.0, max=1.0)
    stretch_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=100.0, subtype="PERCENTAGE")
    angle: bpy.props.FloatProperty(default=0.0, min=-20*math.pi, max=20*math.pi, subtype="ANGLE")
    angle_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=2*math.pi, subtype="ANGLE")

    groove: bpy.props.FloatProperty(default=0.0, min=0.0, max=1.0)
    groove_number: bpy.props.IntProperty(default=5, min=3, max=20)
    size: bpy.props.FloatProperty(default=16.0, min=0.1, max=100.0)
    size_random: bpy.props.FloatProperty(default=80.0, min=0.0, max=100.0, subtype="PERCENTAGE")
    antialiasing: bpy.props.FloatProperty(default=0.5, min=0.0, max=10.0)
    horizontal_space: bpy.props.FloatProperty(default=0.1, min=0.0, max=1.0)
    horizontal_space_random: bpy.props.FloatProperty(default=100.0, min=0.0, max=100.0, subtype="PERCENTAGE")
    vertical_space: bpy.props.FloatProperty(default=0.1, min=0.0, max=1.0)
    vertical_space_random: bpy.props.FloatProperty(default=100.0, min=0.0, max=100.0, subtype="PERCENTAGE")

    reduction_start: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)
    reduction_end: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)

    # Stroke
    stroke_type: bpy.props.EnumProperty(items=stroke_type_items, default="NORMAL")

    line_type: bpy.props.EnumProperty(items=line_type_items, default="FULL")
    length: bpy.props.FloatProperty(default=5.0, min=0.001, max=10000.0, subtype="PIXEL")
    length_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=100.0, subtype="PERCENTAGE")
    space: bpy.props.FloatProperty(default=5.0, min=1.0, max=10000.0, subtype="PIXEL")
    space_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=100.0, subtype="PERCENTAGE")

    stroke_size_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=100.0, subtype="PERCENTAGE")
    extend: bpy.props.FloatProperty(default=0.0, min=0.0, max=10000.0, subtype="PIXEL")
    extend_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=100.0, subtype="PERCENTAGE")
    line_copy: bpy.props.IntProperty(default=1, min=1, max=10)
    line_copy_random: bpy.props.IntProperty(default=0, min=0, max=10)
    normal_offset: bpy.props.FloatProperty(default=0.0, min=-1000.0, max=1000.0, subtype="PIXEL")
    normal_offset_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=1000.0, subtype="PIXEL")
    x_offset: bpy.props.FloatProperty(default=0.0, min=-1000.0, max=1000.0, subtype="PIXEL")
    x_offset_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=1000.0, subtype="PIXEL")
    y_offset: bpy.props.FloatProperty(default=0.0, min=-1000.0, max=1000.0, subtype="PIXEL")
    y_offset_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=1000.0, subtype="PIXEL")

    line_split_angle: bpy.props.FloatProperty(default=0.5*math.pi, min=0.0, max=math.pi, subtype="ANGLE")
    min_line_length: bpy.props.FloatProperty(default=0.0, min=0.0, max=100.0, subtype="PIXEL")
    line_link_length: bpy.props.FloatProperty(default=2.0, min=0.0, max=100.0, subtype="PIXEL")
    line_direction: bpy.props.FloatProperty(default=-math.pi/6, min=-math.pi, max=math.pi, subtype="ANGLE")
    loop_direction_type: bpy.props.EnumProperty(items=loop_direction_items, default="CLOCKWISE")

    # Distortion
    distortion_enabled: bpy.props.BoolProperty(default=False)
    distortion_map_on: bpy.props.BoolProperty(default=False)
    distortion_map_on_gui: bpy.props.BoolProperty(get=lambda self: self.distortion_map_on, set=lambda self, value: setattr(self, "distortion_map_on", value),
        update=lambda self, ctx: self.auto_create_node_when_property_on(ctx, DISTORTION_MAP_SOCKET_ID))
    # distortion map
    distortion_map: bpy.props.StringProperty(
        default=DISTORTION_MAP_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(DISTORTION_MAP_SOCKET_ID) if self.distortion_enabled else "",
        set=lambda self, val: None)
    distortion_map_amount: bpy.props.FloatProperty(default=5.0, min=0.0, max=1000.0, subtype="PIXEL")
    distortion_amount: bpy.props.FloatProperty(default=5.0, min=0.0, max=1000.0, subtype="PIXEL")
    distortion_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=100.0, subtype="PERCENTAGE")
    distortion_cycles: bpy.props.FloatProperty(default=100.0, min=5.0, max=1000.0, subtype="PIXEL")
    distortion_cycles_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=100.0, subtype="PERCENTAGE")
    distortion_phase: bpy.props.FloatProperty(default=0.0, min=-30*math.pi, max=30*math.pi, subtype="ANGLE")
    distortion_phase_random: bpy.props.FloatProperty(default=0.0, min=0.0, max=1.0)

    # Size Reduction
    size_reduction_enabled: bpy.props.BoolProperty(default=False)
    size_reduction_curve: bpy.props.StringProperty(default="")

    # Alpha Reduction
    alpha_reduction_enabled: bpy.props.BoolProperty(default=False)
    alpha_reduction_curve: bpy.props.StringProperty(default="")

    color_space_type: bpy.props.EnumProperty(items=color_space_items, default="RGB")
    color_space_red: bpy.props.FloatProperty(default=0.0, min=0.0, max=1.0)
    color_space_green: bpy.props.FloatProperty(default=0.0, min=0.0, max=1.0)
    color_space_blue: bpy.props.FloatProperty(default=0.0, min=0.0, max=1.0)
    color_space_hue: bpy.props.FloatProperty(default=0.0, min=0.0, max=1.0)
    color_space_saturation: bpy.props.FloatProperty(default=0.0, min=0.0, max=1.0)
    color_space_value: bpy.props.FloatProperty(default=0.0, min=0.0, max=1.0)

    def init(self, context):
        super().init()
        self.outputs.new(BrushDetailSocket.bl_idname, "Output")
        self.inputs.new(TextureMapSocket.bl_idname, "Brush Map", identifier=BRUSH_MAP_SOCKET_ID)
        self.inputs.new(TextureMapSocket.bl_idname, "Distortion Map", identifier=DISTORTION_MAP_SOCKET_ID)
        self.size_reduction_curve = self.create_curve_data([[0.0, 0.25], [0.5, 1.0], [1.0, 0.25]])
        self.alpha_reduction_curve = self.create_curve_data([[0.0, 0.25], [0.5, 1.0], [1.0, 0.25]])

    def free(self):
        self.delete_curve_data("size_reduction_curve")
        self.delete_curve_data("alpha_reduction_curve")

    def draw_buttons_ext(self, context, layout):
        pass

    def draw_socket(self, socket, context, layout, text):
        if socket.identifier in [BRUSH_MAP_SOCKET_ID, DISTORTION_MAP_SOCKET_ID]:
            layout.prop(self, socket.identifier + "_on_gui", text="")
        layout.label(text=socket.name, text_ctxt=Translation.ctxt)