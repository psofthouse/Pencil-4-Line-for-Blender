# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import math
import bpy
import itertools

from .PencilNodeMixin import PencilNodeMixin
from .PencilNodeSockets import *
from ..misc.DataUtils import *
from ..misc import GuiUtils
from ..misc import AttrOverride
from ...i18n import Translation

V_BRUSH_SOCKET_ID = "v_brush"
H_BRUSH_SOCKET_ID = "h_brush"
V_OUTLINE_SOCKET_ID = "v_outline_specific"
H_OUTLINE_SOCKET_ID = "h_outline_specific"
V_OBJECT_SOCKET_ID = "v_object_specific"
H_OBJECT_SOCKET_ID = "h_object_specific"
V_INTERSECTION_SOCKET_ID = "v_intersection_specific"
H_INTERSECTION_SOCKET_ID = "h_intersection_specific"
V_SMOOTH_SOCKET_ID = "v_smooth_specific"
H_SMOOTH_SOCKET_ID = "h_smooth_specific"
V_MATERIAL_SOCKET_ID = "v_material_specific"
H_MATERIAL_SOCKET_ID = "h_material_specific"
V_SELECTED_SOCKET_ID = "v_selected_specific"
H_SELECTED_SOCKET_ID = "h_selected_specific"
V_NORMAL_SOCKET_ID = "v_normal_angle_specific"
H_NORMAL_SOCKET_ID = "h_normal_angle_specific"
V_WIREFRAME_SOCKET_ID = "v_wireframe_specific"
H_WIREFRAME_SOCKET_ID = "h_wireframe_specific"

V_SIZE_REDUCTION_SOCKET_ID = "v_size_reduction"
H_SIZE_REDUCTION_SOCKET_ID = "h_size_reduction"
V_ALPHA_REDUCTION_SOCKET_ID = "v_alpha_reduction"
H_ALPHA_REDUCTION_SOCKET_ID = "h_alpha_reduction"


class LineSetNode(bpy.types.Node, PencilNodeMixin):
    """Pencil line set node"""
    bl_idname = "Pencil4LineSetNodeType"
    bl_label = "Line Set"
    bl_icon = "GREASEPENCIL"

    new_node_offset_x = -340
    new_node_step_y = -20

    def specific_on_changed(self, context, socket_identifier):
        brush_settings = self.auto_create_node_and_return_when_property_on(context, socket_identifier)
        if brush_settings is not None:
            brush_settings.create_new_node(0, context.space_data.edit_tree)
        GuiUtils.update_view3d_area(context.screen)

    node_name: bpy.props.StringProperty(get=lambda self: self.name, override={'LIBRARY_OVERRIDABLE'})

    is_on: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    lineset_id: bpy.props.IntProperty(default=1, min=1, max=8, override={'LIBRARY_OVERRIDABLE'})

    # objects
    objects: bpy.props.CollectionProperty(type=ObjectElement, override={'LIBRARY_OVERRIDABLE'})
    objects_selected_index: bpy.props.IntProperty(override={'LIBRARY_OVERRIDABLE'})

    # materials
    materials: bpy.props.CollectionProperty(type=MaterialElement, override={'LIBRARY_OVERRIDABLE'})
    materials_selected_index: bpy.props.IntProperty(override={'LIBRARY_OVERRIDABLE'})

    is_weld_edges: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    is_mask_hidden_lines: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})

    # v brush settings
    v_brush_settings: bpy.props.StringProperty(
        default=V_BRUSH_SOCKET_ID,
        set=lambda self, val: None)

    # v outline
    v_outline_on: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    v_outline_open: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    v_outline_merge_groups: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_outline_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_outline_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.v_outline_specific_on, set=lambda self, value: setattr(self, "v_outline_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, V_OUTLINE_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    v_outline_brush_settings: bpy.props.StringProperty(
        default=V_OUTLINE_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(V_OUTLINE_SOCKET_ID),
        set=lambda self, val: None)

    # v object
    v_object_on: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    v_object_open: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    v_object_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_object_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.v_object_specific_on, set=lambda self, value: setattr(self, "v_object_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, V_OBJECT_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    v_object_brush_settings: bpy.props.StringProperty(
        default=V_OBJECT_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(V_OBJECT_SOCKET_ID),
        set=lambda self, val: None)

    # v intersection
    v_intersection_on: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    v_intersection_self: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    v_intersection_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_intersection_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.v_intersection_specific_on, set=lambda self, value: setattr(self, "v_intersection_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, V_INTERSECTION_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    v_intersection_brush_settings: bpy.props.StringProperty(
        default=V_INTERSECTION_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(V_INTERSECTION_SOCKET_ID),
        set=lambda self, val: None)

    # v smooth
    v_smooth_on: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    v_smooth_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_smooth_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.v_smooth_specific_on, set=lambda self, value: setattr(self, "v_smooth_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, V_SMOOTH_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    v_smooth_brush_settings: bpy.props.StringProperty(
        default=V_SMOOTH_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(V_SMOOTH_SOCKET_ID),
        set=lambda self, val: None)

    # v material
    v_material_on: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    v_material_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_material_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.v_material_specific_on, set=lambda self, value: setattr(self, "v_material_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, V_MATERIAL_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    v_material_brush_settings: bpy.props.StringProperty(
        default=V_MATERIAL_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(V_MATERIAL_SOCKET_ID),
        set=lambda self, val: None)

    # v selected
    v_selected_on: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    v_selected_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_selected_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.v_selected_specific_on, set=lambda self, value: setattr(self, "v_selected_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, V_SELECTED_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    v_selected_brush_settings: bpy.props.StringProperty(
        default=V_SELECTED_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(V_SELECTED_SOCKET_ID),
        set=lambda self, val: None)

    # v normal angle
    v_normal_angle_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_normal_angle_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_normal_angle_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.v_normal_angle_specific_on, set=lambda self, value: setattr(self, "v_normal_angle_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, V_NORMAL_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    v_normal_angle_brush_settings: bpy.props.StringProperty(
        default=V_NORMAL_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(V_NORMAL_SOCKET_ID),
        set=lambda self, val: None)
    v_normal_angle_min: bpy.props.FloatProperty(default=0.25 * math.pi, min=0.0, max=math.pi, subtype="ANGLE", override={'LIBRARY_OVERRIDABLE'})
    v_normal_angle_max: bpy.props.FloatProperty(default=math.pi, min=0.0, max=math.pi, subtype="ANGLE", override={'LIBRARY_OVERRIDABLE'})

    # v wireframe
    v_wireframe_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_wireframe_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_wireframe_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.v_wireframe_specific_on, set=lambda self, value: setattr(self, "v_wireframe_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, V_WIREFRAME_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    v_wireframe_brush_settings: bpy.props.StringProperty(
        default=V_WIREFRAME_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(V_WIREFRAME_SOCKET_ID),
        set=lambda self, val: None)

    # v size reduction
    v_size_reduction_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_size_reduction_on_gui: bpy.props.BoolProperty(get=lambda self: self.v_size_reduction_on, set=lambda self, value: setattr(self, "v_size_reduction_on", value),
        update=lambda self, ctx: self.auto_create_node_when_property_on(ctx, V_SIZE_REDUCTION_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    v_size_reduction_settings: bpy.props.StringProperty(
        default=V_SIZE_REDUCTION_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(V_SIZE_REDUCTION_SOCKET_ID),
        set=lambda self, val: None)

    # v alpha reduction
    v_alpha_reduction_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    v_alpha_reduction_on_gui: bpy.props.BoolProperty(get=lambda self: self.v_alpha_reduction_on, set=lambda self, value: setattr(self, "v_alpha_reduction_on", value),
        update=lambda self, ctx: self.auto_create_node_when_property_on(ctx, V_ALPHA_REDUCTION_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    v_alpha_reduction_settings: bpy.props.StringProperty(
        default=V_ALPHA_REDUCTION_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(V_ALPHA_REDUCTION_SOCKET_ID),
        set=lambda self, val: None)

    # h brush settings
    h_brush_settings: bpy.props.StringProperty(
        default=H_BRUSH_SOCKET_ID,
        set=lambda self, val: None)

    # h outline
    h_outline_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_outline_open: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    h_outline_merge_groups: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_outline_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_outline_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.h_outline_specific_on, set=lambda self, value: setattr(self, "h_outline_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, H_OUTLINE_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    h_outline_brush_settings: bpy.props.StringProperty(
        default=H_OUTLINE_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(H_OUTLINE_SOCKET_ID),
        set=lambda self, val: None)

    # h object
    h_object_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_object_open: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    h_object_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_object_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.h_object_specific_on, set=lambda self, value: setattr(self, "h_object_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, H_OBJECT_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    h_object_brush_settings: bpy.props.StringProperty(
        default=H_OBJECT_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(H_OBJECT_SOCKET_ID),
        set=lambda self, val: None)

    # h intersection
    h_intersection_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_intersection_self: bpy.props.BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    h_intersection_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_intersection_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.h_intersection_specific_on, set=lambda self, value: setattr(self, "h_intersection_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, H_INTERSECTION_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    h_intersection_brush_settings: bpy.props.StringProperty(
        default=H_INTERSECTION_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(H_INTERSECTION_SOCKET_ID),
        set=lambda self, val: None)

    # h smooth
    h_smooth_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_smooth_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_smooth_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.h_smooth_specific_on, set=lambda self, value: setattr(self, "h_smooth_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, H_SMOOTH_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    h_smooth_brush_settings: bpy.props.StringProperty(
        default=H_SMOOTH_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(H_SMOOTH_SOCKET_ID),
        set=lambda self, val: None)

    # h material
    h_material_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_material_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_material_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.h_material_specific_on, set=lambda self, value: setattr(self, "h_material_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, H_MATERIAL_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    h_material_brush_settings: bpy.props.StringProperty(
        default=H_MATERIAL_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(H_MATERIAL_SOCKET_ID),
        set=lambda self, val: None)

    # h selected
    h_selected_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_selected_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_selected_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.h_selected_specific_on, set=lambda self, value: setattr(self, "h_selected_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, H_SELECTED_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    h_selected_brush_settings: bpy.props.StringProperty(
        default=H_SELECTED_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(H_SELECTED_SOCKET_ID),
        set=lambda self, val: None)

    # h normal angle
    h_normal_angle_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_normal_angle_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_normal_angle_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.h_normal_angle_specific_on, set=lambda self, value: setattr(self, "h_normal_angle_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, H_NORMAL_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    h_normal_angle_brush_settings: bpy.props.StringProperty(
        default=H_NORMAL_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(H_NORMAL_SOCKET_ID),
        set=lambda self, val: None)
    h_normal_angle_min: bpy.props.FloatProperty(default=0.25 * math.pi, min=0.0, max=math.pi, subtype="ANGLE", override={'LIBRARY_OVERRIDABLE'})
    h_normal_angle_max: bpy.props.FloatProperty(default=math.pi, min=0.0, max=math.pi, subtype="ANGLE", override={'LIBRARY_OVERRIDABLE'})

    # h wireframe
    h_wireframe_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_wireframe_specific_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_wireframe_specific_on_gui: bpy.props.BoolProperty(get=lambda self: self.h_wireframe_specific_on, set=lambda self, value: setattr(self, "h_wireframe_specific_on", value),
        update=lambda self, ctx: self.specific_on_changed(ctx, H_WIREFRAME_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    h_wireframe_brush_settings: bpy.props.StringProperty(
        default=H_WIREFRAME_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(H_WIREFRAME_SOCKET_ID),
        set=lambda self, val: None)

    # h size reduction
    h_size_reduction_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_size_reduction_on_gui: bpy.props.BoolProperty(get=lambda self: self.h_size_reduction_on, set=lambda self, value: setattr(self, "h_size_reduction_on", value),
        update=lambda self, ctx: self.auto_create_node_when_property_on(ctx, H_SIZE_REDUCTION_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    h_size_reduction_settings: bpy.props.StringProperty(
        default=H_SIZE_REDUCTION_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(H_SIZE_REDUCTION_SOCKET_ID),
        set=lambda self, val: None)

    # h alpha reduction
    h_alpha_reduction_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    h_alpha_reduction_on_gui: bpy.props.BoolProperty(get=lambda self: self.h_alpha_reduction_on, set=lambda self, value: setattr(self, "h_alpha_reduction_on", value),
        update=lambda self, ctx: self.auto_create_node_when_property_on(ctx, H_ALPHA_REDUCTION_SOCKET_ID),
        override={'LIBRARY_OVERRIDABLE'})
    h_alpha_reduction_settings: bpy.props.StringProperty(
        default=H_ALPHA_REDUCTION_SOCKET_ID,
        get=lambda self: self.filtered_socket_id(H_ALPHA_REDUCTION_SOCKET_ID),
        set=lambda self, val: None)

    #
    user_defined_color: bpy.props.FloatVectorProperty(
        subtype="COLOR",
        get=lambda self: self.color if self.use_custom_color else [0] * 3)

    def init(self, context):
        super().init()
        self.outputs.new(LineSetSocket.bl_idname, "Output")

        self.inputs.new(BrushSettingsSocket.bl_idname, "V Brush Settings", identifier=V_BRUSH_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "V Outline", identifier=V_OUTLINE_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "V Object", identifier=V_OBJECT_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "V Intersection", identifier=V_INTERSECTION_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "V Smoothing", identifier=V_SMOOTH_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "V Material ID", identifier=V_MATERIAL_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "V Selected Edges", identifier=V_SELECTED_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "V Normal Angle", identifier=V_NORMAL_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "V Wireframe", identifier=V_WIREFRAME_SOCKET_ID)

        self.inputs.new(ReductionSettingsSocket.bl_idname, "V Size Reduction", identifier=V_SIZE_REDUCTION_SOCKET_ID)
        self.inputs.new(ReductionSettingsSocket.bl_idname, "V Alpha Reduction", identifier=V_ALPHA_REDUCTION_SOCKET_ID)

        self.inputs.new(BrushSettingsSocket.bl_idname, "H Brush Settings", identifier=H_BRUSH_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "H Outline", identifier=H_OUTLINE_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "H Object", identifier=H_OBJECT_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "H Intersection", identifier=H_INTERSECTION_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "H Smoothing", identifier=H_SMOOTH_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "H Material ID", identifier=H_MATERIAL_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "H Selected Edges", identifier=H_SELECTED_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "H Normal Angle", identifier=H_NORMAL_SOCKET_ID)
        self.inputs.new(BrushSettingsSocket.bl_idname, "H Wireframe", identifier=H_WIREFRAME_SOCKET_ID)

        self.inputs.new(ReductionSettingsSocket.bl_idname, "H Size Reduction", identifier=H_SIZE_REDUCTION_SOCKET_ID)
        self.inputs.new(ReductionSettingsSocket.bl_idname, "H Alpha Reduction", identifier=H_ALPHA_REDUCTION_SOCKET_ID)

        for input in self.inputs:
            if input.identifier.endswith("specific") or input.identifier.endswith("reduction"):
                input.hide = True

    def draw_buttons(self, context, layout):
        GuiUtils.layout_prop(context, layout.row(), self, "is_on", text="On")

    def draw_buttons_ext(self, context, layout):
        return

    def draw_socket(self, socket, context, layout, text):
        layout.enabled = AttrOverride.get_overrided_attr(self, "is_on", context=context)
        if socket.is_output:
            # to Line Node
            layout.label(text=socket.name, text_ctxt=Translation.ctxt)
        else:
            # from Brush Settings Node
            if socket.identifier.endswith("specific") or socket.identifier.endswith("reduction"):
                GuiUtils.layout_prop(context, layout, self, socket.identifier + "_on_gui", text="")
            layout.label(text=socket.name, text_ctxt=Translation.ctxt)

    def update(self):
        pass
        # self.objects.clear()
        # objs = (obj for obj in bpy.data.objects if obj.type == "MESH")
        # for obj in objs:
        #     new_obj = self.objects.add()
        #     new_obj.obj = obj

    def filtered_socket_id(self, id, context=None, depsgraph=None):
        if id.endswith("_specific") and not AttrOverride.get_overrided_attr(self, id.removesuffix("_specific") + "_on", True, context=context, depsgraph=depsgraph):
            return ""
        return super().filtered_socket_id(id, context=context, depsgraph=depsgraph)

    def calc_new_node_position(self, socket_index: int):
        ret = super().calc_new_node_position(socket_index)
        identifier = self.inputs[socket_index].identifier
        if identifier != V_BRUSH_SOCKET_ID and identifier != H_BRUSH_SOCKET_ID:
            if "reduction" in identifier:
                ret[0] += 180
                ret[1] += 120 if identifier == V_SIZE_REDUCTION_SOCKET_ID or identifier == H_SIZE_REDUCTION_SOCKET_ID else 80
            else:
                ret[0] -= 660 + 20 * (socket_index % (len(self.inputs) / 2))
        return ret