# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy

from .PencilNodeMixin import PencilNodeMixin
from .PencilNodeSockets import *
from ..misc import GuiUtils
from ...i18n import Translation

BRUSH_DETAIL_SOCKET_ID = "brush_detail"
COLOR_MAP_SOCKET_ID = "color_map"
SIZE_MAP_SOCKET_ID = "size_map"


class BrushSettingsNode(bpy.types.Node, PencilNodeMixin):
    """Blush Settings Node"""
    bl_idname = "Pencil4BrushSettingsNodeType"
    bl_label = "Brush Settings"
    bl_icon = "GREASEPENCIL"

    new_node_offset_x = -160
    new_node_offset_y = -60
    new_node_step_y = -60

    brush_detail_node: bpy.props.StringProperty(
        default=BRUSH_DETAIL_SOCKET_ID,
        set=lambda self, val: None, get=lambda self: self.filtered_socket_id(BRUSH_DETAIL_SOCKET_ID))

    blend_amount: bpy.props.FloatProperty(
        subtype="FACTOR",
        default=1.0,
        min=0.0,
        max=1.0,
        override={'LIBRARY_OVERRIDABLE'})
    brush_color: bpy.props.FloatVectorProperty(
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=[0.0, 0.0, 0.0],
        override={'LIBRARY_OVERRIDABLE'})

    # color_map
    color_map_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    color_map_on_gui: bpy.props.BoolProperty(get=lambda self: self.color_map_on, set=lambda self, value: setattr(self, "color_map_on", value),
        update=lambda self, ctx: self.auto_create_node_when_property_on(ctx, COLOR_MAP_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    color_map: bpy.props.StringProperty(
        default=COLOR_MAP_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(COLOR_MAP_SOCKET_ID),
        set=lambda self, val: None)
    color_map_opacity: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0, subtype="FACTOR", override={'LIBRARY_OVERRIDABLE'})

    size: bpy.props.FloatProperty(default=1.0, min=0.001, max=100.0, soft_min=0.1, soft_max=20.0, subtype="PIXEL", override={'LIBRARY_OVERRIDABLE'})

    # size map
    size_map_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    size_map_on_gui: bpy.props.BoolProperty(get=lambda self: self.size_map_on, set=lambda self, value: setattr(self, "size_map_on", value),
        update=lambda self, ctx: self.auto_create_node_when_property_on(ctx, SIZE_MAP_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    size_map: bpy.props.StringProperty(
        default=SIZE_MAP_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(SIZE_MAP_SOCKET_ID),
        set=lambda self, val: None)
    size_map_amount: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0, subtype="FACTOR", override={'LIBRARY_OVERRIDABLE'})

    def init(self, context):
        super().init()
        self.outputs.new(BrushSettingsSocket.bl_idname, "Output")
        self.inputs.new(BrushDetailSocket.bl_idname, "Brush Detail", identifier=BRUSH_DETAIL_SOCKET_ID)
        self.inputs.new(TextureMapSocket.bl_idname, "Color Map", identifier=COLOR_MAP_SOCKET_ID)
        self.inputs.new(TextureMapSocket.bl_idname, "Size Map", identifier=SIZE_MAP_SOCKET_ID)

    def draw_buttons_ext(self, context, layout):
        pass

    def draw_socket(self, socket, context, layout, text):
        if socket.identifier in (COLOR_MAP_SOCKET_ID, SIZE_MAP_SOCKET_ID):
            GuiUtils.layout_prop(context, layout, self, socket.identifier + "_on_gui", text="")
        layout.label(text=socket.name, text_ctxt=Translation.ctxt)

    def calc_new_node_position(self, socket_index: int):
        if socket_index == 0:
            return [
                self.location[0] + super().new_node_offset_x,
                self.location[1] + super().new_node_offset_y
            ]
        else:
            return super().calc_new_node_position(socket_index - 1)
