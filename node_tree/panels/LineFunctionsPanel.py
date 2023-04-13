# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
from ..misc import GuiUtils
from ..nodes.LineFunctionsNode import LineFunctionsContainerNode
from ...i18n import Translation

def get_line_functions_node(material: bpy.types.Material):
    return LineFunctionsContainerNode.get_line_functions_node(material)

def get_linked_line_functions_node(material: bpy.types.Material):
    return LineFunctionsContainerNode.get_linked_line_functions_node(material)


class PCL4_PT_LineFunctionsAddButtonPanel(bpy.types.Panel):
    bl_idname = "PCL4_PT_material_line_functions"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_label = "Pencil+ 4 Line Functions"
    bl_translation_context = Translation.ctxt
    bl_order = 100

    @classmethod
    def poll(cls, context):
        mat = context.material
        return mat and not mat.grease_pencil and not get_line_functions_node(mat)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.template_ID(context.material, "pcl4_line_functions", new="pcl4.add_line_functions")


class PCL4_PT_LineFunctionsReplaceLineColorPanel(bpy.types.Panel):
    bl_idname = "PCL4_PT_material_line_functions_replace_line_color"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_label = "Replace Line Color"
    bl_translation_context = Translation.ctxt
    bl_parent_id = "PCL4_PT_material_line_functions"
    bl_order = 101

    @classmethod
    def poll(cls, context):
        return get_linked_line_functions_node(context.material) is not None

    def draw(self, context):
        node = get_linked_line_functions_node(context.material)

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = False

        def draw_line_color(prop_name, prop_text):
            row = layout.row()
            split = row.split(factor=0.4)
            split.use_property_split = False

            split.prop(node, f"{prop_name}_on", text=prop_text, text_ctxt=Translation.ctxt)

            split = split.split(factor=1.0)
            row = split.row(align=True)
            row.enabled = getattr(node, f"{prop_name}_on", False)
            row.prop(node, f"{prop_name}_color", text="", text_ctxt=Translation.ctxt)
            row.prop(node, f"{prop_name}_amount", text="Amount", slider=True, text_ctxt=Translation.ctxt)

        draw_line_color("outline", "Outline")
        draw_line_color("object", "Object")
        draw_line_color("intersection", "Intersection")
        draw_line_color("smooth", "Smoothing Boundary")
        draw_line_color("material", "Material ID Boundary")
        draw_line_color("selected_edge", "Selected Edges")
        draw_line_color("normal_angle", "Normal Angle")
        draw_line_color("wireframe", "Wireframe")


class PCL4_PT_LineFunctionsEdgeDetection(bpy.types.Panel):
    bl_idname = "PCL4_PT_material_line_functions_edge_detection"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_label = "Edge Detection"
    bl_translation_context = Translation.ctxt
    bl_parent_id = "PCL4_PT_material_line_functions"
    bl_order = 102

    @classmethod
    def poll(cls, context):
        return get_linked_line_functions_node(context.material) is not None

    def draw(self, context):
        node = get_linked_line_functions_node(context.material)

        layout = self.layout
        col = layout.column()

        col.prop(node, "disable_intersection", text="Disable Intersection", text_ctxt=Translation.ctxt)
        col.prop(node, "draw_hidden_lines", text="Draw Hidden Lines as Visible Lines", text_ctxt=Translation.ctxt)

        col = layout.column()
        col.enabled = not getattr(node, "draw_hidden_lines", False)

        col.prop(node, "draw_hidden_lines_of_targets", text="Draw Hidden Lines of Targets as Visible Lines", text_ctxt=Translation.ctxt)
        row1 = col.row()

        col.prop(node, "mask_hidden_lines_of_targets", text="Mask Hidden Lines of Targets", text_ctxt=Translation.ctxt)
        row2 = col.row()

        def draw_list(row, str1, str2):
            row.separator_spacer()
            row.enabled = getattr(node, f"{str1}_hidden_lines_of_targets", False)
            GuiUtils.draw_object_material_list(row.column(), "Objects", f"pcl4.{str1}_hidden_lines_object_list",
                node, f"{str1}_hidden_lines_of_targets_objects",
                PCL4_OT_LineFunctionsAddObjects.bl_idname,
                PCL4_OT_LineFunctionsRemoveObjects.bl_idname
            )
            GuiUtils.draw_object_material_list(row.column(), "Materials", f"pcl4.{str1}_hidden_lines_material_list",
                node, f"{str1}_hidden_lines_of_targets_materials",
                PCL4_OT_LineFunctionsAddMaterials.bl_idname,
                PCL4_OT_LineFunctionsRemoveMaterials.bl_idname
            )
        draw_list(row1, "draw", "lf1")
        draw_list(row2, "mask", "lf2")


class PCL4_OT_AddLineFunctionsOperator(bpy.types.Operator):
    bl_idname = "pcl4.add_line_functions"
    bl_label = "Add Line Functions"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        line_func = bpy.data.materials.new(name=LineFunctionsContainerNode.bl_label)
        bpy.context.material.pcl4_line_functions = line_func

        line_func.use_nodes = True
        while (len(line_func.node_tree.nodes) > 0):
            line_func.node_tree.nodes.remove(line_func.node_tree.nodes[0])
        node = line_func.node_tree.nodes.new(type=LineFunctionsContainerNode.bl_idname)
        node.name = LineFunctionsContainerNode.bl_label
        line_func.use_nodes = False

        return {"FINISHED"}


class LineFunctionsAddRemoveOperatorMixin(GuiUtils.IDSelectAddRemoveOperatorMixin):
    bl_options = {"REGISTER", "UNDO"}

    def specify_data(self, context):
        return get_linked_line_functions_node(context.material)

class PCL4_OT_LineFunctionsAddMaterials(LineFunctionsAddRemoveOperatorMixin, bpy.types.Operator):
    bl_idname = "pcl4.line_funcions_add_materials"
    bl_label = "Add Materials"

class PCL4_OT_LineFunctionsRemoveMaterials(LineFunctionsAddRemoveOperatorMixin, bpy.types.Operator):
    bl_idname = "pcl4.line_funcions_remove_materials"
    bl_label = "Remove Materials"

class PCL4_OT_LineFunctionsAddObjects(LineFunctionsAddRemoveOperatorMixin, bpy.types.Operator):
    bl_idname = "pcl4.line_funcions_add_objects"
    bl_label = "Add Objects"

class PCL4_OT_LineFunctionsRemoveObjects(LineFunctionsAddRemoveOperatorMixin, bpy.types.Operator):
    bl_idname = "pcl4.line_funcions_remove_objects"
    bl_label = "Remove Objects"
