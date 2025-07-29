# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import itertools

from ..nodes.LineSetNode import LineSetNode
from . import BrushSettingsNodePanel
from ..misc import GuiUtils
from ..misc.GuiUtils import layout_prop
from ..misc.AttrOverride import get_overrided_attr
from ..misc import DataUtils
from ..PencilNodeTree import PencilNodeTree
from ...i18n import Translation

def draw_objects_list(layout, node):
    GuiUtils.draw_object_material_list(layout, "Objects", "pcl4.object_list",
        node, "objects",
        PCL4_OT_LineSetAddObjects.bl_idname,
        PCL4_OT_LineSetRemoveObjects.bl_idname
    )

def draw_materials_list(layout, node):
    GuiUtils.draw_object_material_list(layout, "Materials", "pcl4.material_list",
        node, "materials",
        PCL4_OT_LineSetAddMaterials.bl_idname,
        PCL4_OT_LineSetRemoveMaterials.bl_idname
    )

class PCL4_PT_lineset_mixin:
    @classmethod
    def lineset_poll(cls, context):
        return cls.lineset_node(context) is not None and isinstance(cls.lineset_node(context), LineSetNode)

    @classmethod
    def lineset_node(cls, context):
        return context.active_node

    @classmethod
    def lineset_enabled(cls, context):
        return get_overrided_attr(cls.lineset_node(context), "is_on", context=context, default=False)


class PCL4_PT_lineset_base(PCL4_PT_lineset_mixin):
    bl_label = ""
    bl_translation_context = Translation.ctxt
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"
    bl_order = 101
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        return cls.lineset_poll(context)

    def draw_header(self, context):
        layout = self.layout
        node = self.lineset_node(context)

        split = layout.split(factor=0.5)
        layout_prop(context, split, node, "is_on", text=node.name, translate=False, text_ctxt=Translation.ctxt)

        split = split.split(factor=1.0)
        row = split.row()
        row.alignment = "RIGHT"
        layout_prop(context, row, node, "lineset_id", text="Line Set ID", text_ctxt=Translation.ctxt)
        row.label(text=" ", text_ctxt=Translation.ctxt)
        row.enabled = self.lineset_enabled(context)

        line_node_enabled_func = getattr(self, "line_enabled", None)
        layout.enabled = line_node_enabled_func is None or line_node_enabled_func(context)

    def draw(self, context):
        layout = self.layout
        node = self.lineset_node(context)
        tree = PencilNodeTree.tree_from_context(context)
        layout.enabled = tree.is_entity()

        col = layout.column()
        col.enabled = self.lineset_enabled(context)

        if self.show_lists():
            row = col.row()
            
            draw_objects_list(row.column(), node)
            draw_materials_list(row.column(), node)
            col.separator(factor=3.0)

        col = layout.column(align=True)

        row = col.row(align=True)
        row.alignment = "LEFT"
        button = row.operator(PCL4_OT_SHOW_VISIBLE_LINES.bl_idname,
            depress=tree.show_visible_lines, text="Visible Lines", text_ctxt=Translation.ctxt)
        button.show = True
        button = row.operator(PCL4_OT_SHOW_VISIBLE_LINES.bl_idname,
            depress=not tree.show_visible_lines, text="Hidden Lines", text_ctxt=Translation.ctxt)
        button.show = False

        row = col.row()
        row.scale_y = 0.1
        row.enabled = False
        row.label(text="." * 320)

    @classmethod
    def show_lists(cls):
        return True

class PCL4_PT_lineset(PCL4_PT_lineset_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset"

    @classmethod
    def poll(cls, context):
        return super().poll(context) and PencilNodeTree.show_node_params(context)


class PCL4_PT_lineset_brush_base(PCL4_PT_lineset_mixin, BrushSettingsNodePanel.PCL4_PT_brush_settings_base):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_label = ""
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return True

    def draw_header(self, context):
        layout = self.layout

        layout.label(text="Brush", text_ctxt=Translation.ctxt)

        brush_settings = self.brush_settings_node(context)
        brush_detail = next(x for x in brush_settings.inputs).get_connected_node() if brush_settings is not None else None
        if brush_detail is None:
            return

        row = layout.row()
        row.alignment = "RIGHT"
        button = row.operator("pcl4.activate_node", text="Brush Detail", icon="TRACKING", text_ctxt=Translation.ctxt)
        button.node.set(brush_detail)
        button.preferred_parent_node.set(brush_settings)
        row.enabled = self.brush_settings_enabled(context)

        row.label(text=" ", text_ctxt=Translation.ctxt)

    @classmethod
    def brush_settings_node(cls, context):
        node = cls.lineset_node(context)
        tree = PencilNodeTree.tree_from_context(context)

        brush_settings_socket_name = "v_brush" if tree.show_visible_lines else "h_brush"

        brush_settings = \
            next(x for x in node.inputs if x.identifier == brush_settings_socket_name) \
            .get_connected_node()

        return brush_settings

    @classmethod
    def brush_settings_enabled(cls, context):
        return cls.lineset_enabled(context)

class PCL4_PT_lineset_brush(PCL4_PT_lineset_brush_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_brush"
    bl_parent_id = "PCL4_PT_lineset"


class PCL4_PT_lineset_edge_base(PCL4_PT_lineset_mixin):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_label = "Edge"
    bl_translation_context = Translation.ctxt
    bl_order = 2

    __prop_def = [
        (("outline", "Outline"), [("outline_open", "Open Edge"), ("outline_merge_groups", "Merge Groups")]),
        (("object", "Object"), [("object_open", "Open Edge")]),
        (("intersection", "Intersection"), [("intersection_self", "Self-Intersection")]),
        (("smooth", "Smoothing Boundary"), []),
        (("material", "Material ID Boundary"), []),
        (("selected", "Selected Edges"), []),
        (("normal_angle", "Normal Angle"), [("normal_angle_min", "Min"), ("normal_angle_max", "Max")]),
        (("wireframe", "Wireframe"), []),
    ]

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        node = self.lineset_node(context)
        tree = PencilNodeTree.tree_from_context(context)
        layout.enabled = tree.is_entity()

        col = layout.column()
        col.enabled = self.lineset_enabled(context)

        prefix = "v_" if tree.show_visible_lines else "h_"

        def prop(prop_name, label_text):
            layout_prop(context, box_col, node, prefix + prop_name, text=label_text, text_ctxt=Translation.ctxt)
        
        for d in __class__.__prop_def:
            on_prop = prefix + d[0][0] + "_on"
            layout_prop(context, col, node, on_prop, text=d[0][1], text_ctxt=Translation.ctxt)
            box_col = GuiUtils.indented_box_column(col, algin=True)
            box_col.enabled = get_overrided_attr(node, on_prop, context=context, default=False)
            for param in d[1]:
                prop(param[0], param[1])

            row = box_col.row()
            s_on_prop = prefix + d[0][0] + "_specific_on_gui"
            layout_prop(context, row, node, s_on_prop, text="Specific Brush Settings", text_ctxt=Translation.ctxt,
                        preserve_icon_space=True, preserve_icon_space_emboss=False)

            specific_node = node.find_connected_from_node(prefix + d[0][0] + "_specific")
            row = row.row()
            row.enabled = get_overrided_attr(node, s_on_prop, context=context, default=False)
            button = row.operator("pcl4.activate_node",
                text=specific_node.name if specific_node is not None else "None",
                icon= "TRACKING" if specific_node is not None else "NONE")
            button.node.set(specific_node)
            button.preferred_parent_node.set(node)

        def prop(prop_name, label_text):
            layout_prop(context, col, node, prop_name, text=label_text, text_ctxt=Translation.ctxt)

        col.separator(factor=3.0)
        prop("is_weld_edges", "Weld Edges Between Objects")
        prop("is_mask_hidden_lines", "Mask Hidden Lines of Other Line Sets")

class PCL4_PT_lineset_edge(PCL4_PT_lineset_edge_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_edge"
    bl_parent_id = "PCL4_PT_lineset"


class PCL4_PT_lineset_reduction_base(PCL4_PT_lineset_mixin):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_label = "Reduction"
    bl_translation_context = Translation.ctxt
    bl_order = 3

    __prop_def = [
        ("size_reduction", "Size Reduction"),
        ("alpha_reduction", "Alpha Reduction"),
    ]

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        node = self.lineset_node(context)
        tree = PencilNodeTree.tree_from_context(context)
        layout.enabled = tree.is_entity()

        col = layout.column()
        col.enabled = self.lineset_enabled(context)

        prefix = "v_" if tree.show_visible_lines else "h_"

        for d in __class__.__prop_def:
            row = col.row()
            on_prop = prefix + d[0] + "_on_gui"
            layout_prop(context, row, node, on_prop, text=d[1], text_ctxt=Translation.ctxt,
                        preserve_icon_space=True, preserve_icon_space_emboss=False)

            target_node = node.find_connected_from_node(prefix + d[0])
            row = row.row()
            row.enabled = get_overrided_attr(node, on_prop, context=context, default=False)
            button = row.operator("pcl4.activate_node",
                text=target_node.name if target_node is not None else "None",
                icon= "TRACKING" if target_node is not None else "NONE")
            button.node.set(target_node)
            button.preferred_parent_node.set(node)


class PCL4_PT_lineset_reduction(PCL4_PT_lineset_reduction_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_reduction"
    bl_parent_id = "PCL4_PT_lineset"


class LineSetAddRemoveOperatorMixin(GuiUtils.IDSelectAddRemoveOperatorMixin):
    bl_options = {"REGISTER", "UNDO"}

    def specify_data(self, context):
        node_tree = context.space_data.edit_tree
        data_ptr = int(self.data_ptr)
        return next(x for x in node_tree.nodes if x.as_pointer() == data_ptr)

    def additional_excludes(self, context):
        data = self.specify_data(context)
        if self.select_type == "ADD":
            # 属するLineの配下のLineSetへ既に接続されている要素は除外する
            lines = [x.to_node for x in data.outputs[0].links]
            linesets = [x.get_connected_node() for x in itertools.chain.from_iterable(x.inputs for x in lines if x is not None)]
            linesets = [x for x in linesets if x is not None]
            return set(itertools.chain.from_iterable(DataUtils.enumerate_ids_from_collection(lineset, self.propname) for lineset in linesets))
        elif self.select_type == "REMOVE":
            # ライブラリオーバーライドされているとき、元から存在する要素は除外する
            node_tree = context.space_data.edit_tree
            if node_tree.override_library is not None:
                src_tree = node_tree.override_library.reference
                if data.name in src_tree.nodes:
                    src_data = node_tree.override_library.reference.nodes[data.name]
                    return set(DataUtils.enumerate_ids_from_collection(src_data, self.propname))
        return set()

class PCL4_OT_LineSetAddMaterials(LineSetAddRemoveOperatorMixin, bpy.types.Operator):
    bl_idname = "pcl4.line_set_add_materials"
    bl_label = "Add Materials"

class PCL4_OT_LineSetRemoveMaterials(LineSetAddRemoveOperatorMixin, bpy.types.Operator):
    bl_idname = "pcl4.line_set_remove_materials"
    bl_label = "Remove Materials"

class PCL4_OT_LineSetAddObjects(LineSetAddRemoveOperatorMixin, bpy.types.Operator):
    bl_idname = "pcl4.line_set_add_objects"
    bl_label = "Add Objects"

class PCL4_OT_LineSetRemoveObjects(LineSetAddRemoveOperatorMixin, bpy.types.Operator):
    bl_idname = "pcl4.line_set_remove_objects"
    bl_label = "Remove Objects"


class PCL4_OT_SHOW_VISIBLE_LINES(bpy.types.Operator):
    bl_idname = "pcl4.show_visible_lines"
    bl_label = "Show Visible Lines"

    show: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        tree = PencilNodeTree.tree_from_context(context)
        if tree is None:
            return {"CANCELLED"}
        tree.show_visible_lines = self.show
        return {"FINISHED"}
