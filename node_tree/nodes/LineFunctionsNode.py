# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
from ..misc.DataUtils import *

class LineFunctionsContainerNode(bpy.types.Node):
    bl_idname = "Pencil4LineFunctionsContainerNodeType"
    bl_label = "Pencil+ 4 Line Functions"
    bl_icon = "GREASEPENCIL"

    def get_line_functions_node(material: bpy.types.Material):
        if material is None or material.node_tree is None:
            return None
        return next((x for x in material.node_tree.nodes if x.bl_idname==LineFunctionsContainerNode.bl_idname), None)

    def get_linked_line_functions_node(material: bpy.types.Material):
        if not material:
            return None
        return __class__.get_line_functions_node(material.pcl4_line_functions)
    
    # Replace Line Color
    outline_on: bpy.props.BoolProperty(default=False)
    outline_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=3, min=0.0, max=1.0, default=[0.0, 0.0, 0.0])
    outline_amount: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)

    object_on: bpy.props.BoolProperty(default=False)
    object_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=3, min=0.0, max=1.0, default=[0.0, 0.0, 0.0])
    object_amount: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)

    intersection_on: bpy.props.BoolProperty(default=False)
    intersection_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=3, min=0.0, max=1.0, default=[0.0, 0.0, 0.0])
    intersection_amount: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)

    smooth_on: bpy.props.BoolProperty(default=False)
    smooth_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=3, min=0.0, max=1.0, default=[0.0, 0.0, 0.0])
    smooth_amount: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)

    material_on: bpy.props.BoolProperty(default=False)
    material_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=3, min=0.0, max=1.0, default=[0.0, 0.0, 0.0])
    material_amount: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)

    selected_edge_on: bpy.props.BoolProperty(default=False)
    selected_edge_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=3, min=0.0, max=1.0, default=[0.0, 0.0, 0.0])
    selected_edge_amount: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)

    normal_angle_on: bpy.props.BoolProperty(default=False)
    normal_angle_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=3, min=0.0, max=1.0, default=[0.0, 0.0, 0.0])
    normal_angle_amount: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)

    wireframe_on: bpy.props.BoolProperty(default=False)
    wireframe_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=3, min=0.0, max=1.0, default=[0.0, 0.0, 0.0])
    wireframe_amount: bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0)

    # Edge Detection
    disable_intersection: bpy.props.BoolProperty(default=False)
    draw_hidden_lines: bpy.props.BoolProperty(default=False)

    draw_hidden_lines_of_targets: bpy.props.BoolProperty(default=False)
    draw_hidden_lines_of_targets_objects: bpy.props.CollectionProperty(type=ObjectElement)
    draw_hidden_lines_of_targets_objects_selected_index: bpy.props.IntProperty()
    draw_hidden_lines_of_targets_materials: bpy.props.CollectionProperty(type=MaterialElement)
    draw_hidden_lines_of_targets_materials_selected_index: bpy.props.IntProperty()

    mask_hidden_lines_of_targets: bpy.props.BoolProperty(default=False)
    mask_hidden_lines_of_targets_objects: bpy.props.CollectionProperty(type=ObjectElement)
    mask_hidden_lines_of_targets_objects_selected_index: bpy.props.IntProperty()
    mask_hidden_lines_of_targets_materials: bpy.props.CollectionProperty(type=MaterialElement)
    mask_hidden_lines_of_targets_materials_selected_index: bpy.props.IntProperty()