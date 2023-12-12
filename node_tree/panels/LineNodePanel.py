# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import itertools

from ..nodes.LineNode import LineNode
from ..nodes.LineSetNode import LineSetNode
from ..nodes.BrushSettingsNode import BrushSettingsNode
from ..nodes.BrushDetailNode import BrushDetailNode
from . import LineSetNodePanel
from ..PencilNodeTree import PencilNodeTree
from ..nodes.LineSetNode import V_BRUSH_SOCKET_ID
from ..nodes.LineSetNode import H_BRUSH_SOCKET_ID
from ..misc.GuiUtils import layout_prop
from ..misc.AttrOverride import get_overrided_attr
from ...i18n import Translation


class PCL4_UL_LineSetsListView(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        node = item.get_connected_node()
        row = layout.row(align=True)
        if node is not None:
            layout_prop(context, row, node, "name", text="", emboss=False, translate=False)
        else:
            row.label(text="None", translate=True, text_ctxt=Translation.ctxt)

    def draw_filter(self, context, layout):
        pass

    def filter_items(self, context, data, propname):
        inputs = getattr(data, propname)

        flt_flags = list((self.bitflag_filter_item if x.get_connected_node() is not None else 0) for x in inputs)
        flt_neworder = list(range(len(inputs)))
        
        return flt_flags, flt_neworder        


class PCL4_OT_Line_Mixin:
    node_name: bpy.props.StringProperty()
    index: bpy.props.IntProperty(default=-1)

    def get_node(self, context):
        for n in context.space_data.edit_tree.nodes:
            if n.name == self.node_name:
                return n


class PCL4_OT_LineSetsListMoveItemOperator(PCL4_OT_Line_Mixin, bpy.types.Operator):
    bl_idname = "pcl4.line_sets_list_move_item"
    bl_label = "Move Item"
    bl_options = {"REGISTER", "UNDO"}

    button_type: bpy.props.StringProperty(default="UP")

    def execute(self, context):
        line = self.get_node(context)
        step = -1 if self.button_type == "UP" else (1 if self.button_type == "DOWN" else 0)
        if line is None or self.index < 0 or step == 0:
            return {"CANCELLED"}

        target_index = self.index + step
        while True:
            if target_index < 0 or len(line.inputs) <= target_index: 
                return {"CANCELLED"}
            if line.inputs[target_index].is_linked:
                break
            target_index += step
        
        line.swap_input(self.index, target_index)

        return {"FINISHED"}


class PCL4_OT_NewLineSetOperator(PCL4_OT_Line_Mixin, bpy.types.Operator):
    bl_idname = "pcl4.new_line_set"
    bl_label = "New Line Set"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        node_tree = context.space_data.edit_tree

        line = self.get_node(context)
        if line is None or len(line.inputs) == 0:
            return {"CANCELLED"}

        for node in node_tree.nodes:
            node.select = False

        if self.index < 0:
            line.inputs.move(len(line.inputs) - 1, 0)   # 末尾に存在する未接続のソケットを移動する
            self.index = 0

        # LineSetを生成
        line_set = line.create_new_node(self.index, node_tree)
        line.lineset_selected_index = self.index

        # BrushSettings, BrushDetailsを生成
        v_brush_settings = line_set.create_new_node(line_set.find_input_socket_index(V_BRUSH_SOCKET_ID), node_tree)
        v_brush_detail = v_brush_settings.create_new_node(0, node_tree)
        h_brush_settings = line_set.create_new_node(line_set.find_input_socket_index(H_BRUSH_SOCKET_ID), node_tree)
        h_brush_detail = h_brush_settings.create_new_node(0, node_tree)

        return {"FINISHED"}

class PCL4_OT_RemoveLineSetOperator(PCL4_OT_Line_Mixin, bpy.types.Operator):
    bl_idname = "pcl4.remove_line_set"
    bl_label = "Remove Line Set"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        node_tree = context.space_data.edit_tree

        line = self.get_node(context)
        remove_socket = line.inputs[self.index] if line is not None else None
        if remove_socket is None:
            return {"CANCELLED"}
        remove_node = remove_socket.get_connected_node()

        selected_index = line.lineset_selected_index
        line.inputs.remove(remove_socket)
        line.lineset_selected_index = min(selected_index, len(line.inputs) - 2)

        if remove_node is not None:
            remove_node.delete_if_unused(node_tree)

        line.update()

        return {"FINISHED"}

class PCL4_OT_ShrinkLineSetOperator(PCL4_OT_Line_Mixin, bpy.types.Operator):
    bl_idname = "pcl4.shrink_line_set"
    bl_label = "Shrink Line Set"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        line = self.get_node(context)
        if line is None or len(line.inputs) == 0:
            return {"CANCELLED"}

        selected_index = self.index
        for i in range(len(line.inputs) - 1, -1, -1):
            if not line.inputs[i].is_linked:
                line.inputs.remove(line.inputs[i])
        line.lineset_selected_index = min(selected_index, len(line.inputs) - 2)

        line.update()

        return {"FINISHED"}

class PCL4_OT_InsertSocketOperator(PCL4_OT_Line_Mixin, bpy.types.Operator):
    bl_idname = "pcl4.insert_socket"
    bl_label = "Insert scocket"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        line = self.get_node(context)
        if line is None or self.index < 0 or len(line.inputs) <= self.index:
            return {"CANCELLED"}

        line.insert_socket(self.index)

        return {"FINISHED"}


class PCL4_PT_line_mixin:
    @classmethod
    def line_poll(cls, context):
        return cls.line_node(context) is not None and isinstance(cls.line_node(context), LineNode)

    @classmethod
    def line_node(cls, context):
        return context.active_node
    
    @classmethod
    def lineset_node(cls, context):
        return cls.line_node(context).get_selected_lineset()

    @classmethod
    def line_enabled(cls, context):
        return get_overrided_attr(cls.line_node(context), "is_active", context=context, default=False)

    @classmethod
    def lineset_enabled(cls, context):
        return cls.line_enabled(context) and super().lineset_enabled(context)


class PCL4_PT_line_base(PCL4_PT_line_mixin):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"
    bl_order = 100
    bl_label = ""
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        return cls.line_poll(context)

    def draw_header(self, context):
        layout = self.layout
        node = self.line_node(context)

        split = layout.split(factor=0.5)
        layout_prop(context, split, node, "is_active", text=node.name, translate=False, text_ctxt=Translation.ctxt)

        split = split.split(factor=1.0)
        row = split.row()
        row.alignment = "RIGHT"
        layout_prop(context, row, node, "render_priority", text="Render Priority", text_ctxt=Translation.ctxt)
        row.label(text=" ", text_ctxt=Translation.ctxt)

    def draw(self, context):
        layout = self.layout
        layout.enabled = PencilNodeTree.tree_from_context(context).is_entity()
        node = self.line_node(context)

        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.enabled = self.line_enabled(context)

        # LineSetのリスト
        row = col.row()
        split = row.split(factor=0.32)

        col2 = split.column()

        col2.label(text="Line Sets", text_ctxt=Translation.ctxt)
        col2.template_list(
            "PCL4_UL_LineSetsListView", "",
            node, "inputs",
            node, "lineset_selected_index",
            sort_lock=True)

        row2 = col2.row(align=True)
        new_lineset_button = row2.operator("pcl4.new_line_set", text="Add")
        new_lineset_button.node_name = node.name
        new_lineset_button.index = -1
        row2 = row2.row()
        row2.enabled = len(getattr(node, "inputs", None)) > 1
        remove_lineset_button = row2.operator("pcl4.remove_line_set", text="Remove")
        remove_lineset_button.node_name = node.name
        remove_lineset_button.index = node.lineset_selected_index

        split = split.split(factor=0.1)
        col2 = split.column()
        col2.separator(factor=12.0)
        up_button = col2.operator("pcl4.line_sets_list_move_item", icon="TRIA_UP", text="")
        up_button.node_name = node.name
        up_button.index = node.lineset_selected_index
        up_button.button_type = "UP"
        down_button = col2.operator("pcl4.line_sets_list_move_item", icon="TRIA_DOWN", text="")
        down_button.node_name = node.name
        down_button.index = node.lineset_selected_index
        down_button.button_type = "DOWN"

        # 選択中のLineSetのObjectsとMaterialsを表示する
        lineset = self.lineset_node(context)

        split = split.split(factor=1.0)
        row = split.row()
        LineSetNodePanel.draw_objects_list(row.column(), lineset)
        LineSetNodePanel.draw_materials_list(row.column(), lineset)

        #
        col.separator(factor=2.0)
        row = col.row()
        layout_prop(context, row, node, "line_size_type", text="Line Size", expand=True, text_ctxt=Translation.ctxt)

        col.separator()
        layout_prop(context, col, node, "is_output_to_render_elements_only", text="Output to Render Elements Only", text_ctxt=Translation.ctxt)
        layout_prop(context, col, node, "over_sampling", text="Over Sampling", text_ctxt=Translation.ctxt)
        layout_prop(context, col, node, "antialiasing", text="Antialiasing", slider=True, text_ctxt=Translation.ctxt)
        layout_prop(context, col, node, "off_screen_distance", text="Offscreen Distance", text_ctxt=Translation.ctxt)
        layout_prop(context, col, node, "random_seed", text="Random Seed", text_ctxt=Translation.ctxt)

class PCL4_PT_line(PCL4_PT_line_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_line_parameters"

    @classmethod
    def poll(cls, context):
        return super().poll(context) and PencilNodeTree.show_node_params(context)


class PCL4_PT_lineset_base(PCL4_PT_line_mixin, LineSetNodePanel.PCL4_PT_lineset_base):
    @classmethod
    def poll(cls, context):
        return cls.line_poll(context) and super().poll(context)
   
    @classmethod
    def show_lists(cls):
        return False

class PCL4_PT_lineset(PCL4_PT_lineset_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_for_line"

    @classmethod
    def poll(cls, context):
        return super().poll(context) and PencilNodeTree.show_node_params(context)


class PCL4_PT_lineset_brush_base(PCL4_PT_line_mixin, LineSetNodePanel.PCL4_PT_lineset_brush_base):
    pass
class PCL4_PT_lineset_brush(PCL4_PT_lineset_brush_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_brush_for_line"
    bl_parent_id = "PCL4_PT_lineset_for_line"


class PCL4_PT_lineset_edge_base(PCL4_PT_line_mixin, LineSetNodePanel.PCL4_PT_lineset_edge_base):
    pass
class PCL4_PT_lineset_edge(PCL4_PT_lineset_edge_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_edge_for_line"
    bl_parent_id = "PCL4_PT_lineset_for_line"
 

class PCL4_PT_lineset_reduction_base(PCL4_PT_line_mixin, LineSetNodePanel.PCL4_PT_lineset_reduction_base):
    pass
class PCL4_PT_lineset_reduction(PCL4_PT_lineset_reduction_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_reduction_for_line"
    bl_parent_id = "PCL4_PT_lineset_for_line"
