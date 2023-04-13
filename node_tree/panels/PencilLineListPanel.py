# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import itertools
import bpy
from ..nodes.LineNode import LineNode
from ..nodes.LineSetNode import LineSetNode
from ..nodes.BrushSettingsNode import BrushSettingsNode
from ..PencilNodeTree import PencilNodeTree
from . import LineNodePanel
from ..misc.NamedRNAStruct import NamedRNAStruct
from ...i18n import Translation
from ..nodes.PencilNodeMixin import PencilNodeMixin

class PCL4_UL_LineListView(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row2 = row.row()
        row2.alignment = "LEFT"
        row2.label(text=" ")
        row2 = row.row()
        row2.alignment = "CENTER"
        row2.prop(item, "is_active", text="")
        row.prop(item, "name", text="", emboss=False, translate=False)

    def draw_filter(self, context, layout):
        pass

    def filter_items(self, context, data, propname):
        nodes = getattr(data, propname)
        lines = PencilNodeTree.tree_from_context(context).enumerate_lines()

        flt_flags = []
        flt_neworder = []
        another_node_index = len(lines)

        for node in nodes:
            if isinstance(node, LineNode):
                flt_flags.append(self.bitflag_filter_item)
                flt_neworder.append(lines.index(node))
            else:
                flt_flags.append(0)
                flt_neworder.append(another_node_index)
                another_node_index = another_node_index + 1

        return flt_flags, flt_neworder        


class PCL4_PT_PencilLineList_mixin:
    @classmethod
    def linelist_poll(cls, context):
        return isinstance(context.space_data.edit_tree, PencilNodeTree)

    @classmethod
    def line_node(cls, context):
        return isinstance(context.space_data.edit_tree, PencilNodeTree) and\
               PencilNodeTree.tree_from_context(context).get_selected_line()


class PCL4_PT_PencilLineList(PCL4_PT_PencilLineList_mixin, bpy.types.Panel):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"
    bl_options = {"HIDE_HEADER"}
    bl_label = ""
    bl_order = 0

    preferred_show_nodes = list()

    @classmethod
    def poll(cls, context):
        if context.space_data.tree_type != PencilNodeTree.bl_idname:
            return False

        #　ライン描画のノードツリー実体が存在しない場合、強制的にノードツリーを新規生成する
        if not PencilNodeTree.is_entity_exist():
            # 描画処理中にcontextの変更はできないため、タイマーを利用してオペレーターを実行する
            # 新規生成したノードツリーをエディター上で選択するため、スペースのポインタ情報を引数で渡す
            ptr = str(context.space_data.as_pointer())
            bpy.app.timers.register(
                lambda: None if bpy.ops.pcl4.new_line_node_tree(space_node_editor_ptr = ptr) else None,
                first_interval=0.0)
            return False
        
        # 編集対象が空の場合、選択可能なノードツリーがあれば自動的に選択状態にする
        tree = PencilNodeTree.tree_from_context(context)
        if tree is None and PCL4_OT_SelectDefaultTree.get_default_tree() is not None:
            ptr = str(context.space_data.as_pointer())
            bpy.app.timers.register(
                lambda: None if bpy.ops.pcl4.select_default_tree(space_node_editor_ptr = ptr) else None,
                first_interval=0.0)
            return False

        # ラインリスト表示の選択とアクティブノードが異なる場合、ラインリスト表示選択の同期をタイマーにより実行する
        if tree is not None and not tree.show_node_panel:
            do_sync = False
            active_node = tree.nodes.active
            line_node = tree.get_selected_line()
            if isinstance(active_node, LineNode):
                do_sync = line_node != active_node
            elif isinstance(active_node, LineSetNode):
                linenodes = tree.enumerate_lines()
                lineset_node = line_node.get_selected_lineset() if line_node is not None else None
                if lineset_node != active_node:
                    for parent in active_node.find_connected_to_nodes():
                        if parent in linenodes:
                            do_sync = True
                            break
            if do_sync:
                bpy.app.timers.register(
                    lambda: None if bpy.ops.pcl4.sync_node_selection(tree_ptr=str(tree.as_pointer())) else None,
                    first_interval=0.0)
        
        return True

    def draw_switch_buttons(self, context, layout):
        tree = PencilNodeTree.tree_from_context(context)
        active_node = context.active_node if isinstance(context.active_node, PencilNodeMixin) else None
        show_node_panel = tree.show_node_panel

        nodes = [None]
        preferred_show_nodes = list(__class__.preferred_show_nodes)

        if show_node_panel and active_node is not None:
            # アクティブノードのパネルを表示する場合、選択可能な親ノードのボタンも表示する
            if active_node in preferred_show_nodes:
                nodes.extend(preferred_show_nodes)
            else:
                for parent in active_node.find_connected_to_nodes():
                    if parent in preferred_show_nodes:
                        for preferred_show_node in preferred_show_nodes:
                            nodes.append(preferred_show_node)
                            if preferred_show_node == parent:
                                break
                        nodes.append(active_node)
                        break
                
                if nodes[-1] != active_node:
                    auto_detect = [active_node]
                    while True:
                        parents = auto_detect[-1].find_connected_to_nodes()
                        if not parents:
                            break
                        parent = parents[0]
                        if isinstance(parent, LineNode) or isinstance(parent, LineSetNode):
                            break
                        auto_detect.append(parent)

                    nodes.extend(reversed(auto_detect))
        else:
            # ラインリストを表示する場合、選択中のラインセットのボタンを表示する
            line_node = tree.get_selected_line()
            lineset_node = line_node.get_selected_lineset() if line_node is not None else None
            if lineset_node is not None:
                brush_settings_socket_name = "v_brush" if tree.show_visible_lines else "h_brush"
                brush_settings = \
                    next(x for x in lineset_node.inputs if x.identifier == brush_settings_socket_name) \
                    .get_connected_node()
                if brush_settings is not None:
                    nodes.append(brush_settings)
            
        if isinstance(nodes[-1], BrushSettingsNode):
            child = nodes[-1].find_connected_from_node(nodes[-1].brush_detail_node)
            if child is not None:
                nodes.append(child)

        selected_node = active_node if show_node_panel else None

        layout.alignment = "LEFT"
        for i, node in enumerate(nodes):
            op = layout.operator("pcl4.activate_node",
                text=node.name if node is not None else "Line List",
                text_ctxt = Translation.ctxt,
                translate=node is None,
                icon="NONE" if node is not None else "PRESET",
                depress=node == selected_node)
            op.node.set(node)
            op.preferred_parent_node.set(nodes[i - 1] if i > 0 else None)

    def draw(self, context):
        layout = self.layout

        tree = PencilNodeTree.tree_from_context(context)
        if tree is None:
            return
        
        self.draw_switch_buttons(context, layout.row(align=True))

        if PencilNodeTree.show_node_params(context):
            return

        layout.separator(factor=0.25)
        split_p = layout.split(factor=0.1)
        split_p.column()
        split_p = split_p.split(factor=1.0)
        split_p = split_p.split(factor=0.95)

        row = split_p.row()
        row.enabled = tree.is_entity()

        split = row.split(factor=0.92)

        left_col = split.column()
        left_col.template_list(
            "PCL4_UL_LineListView", "",
            tree, "nodes",
            tree, "linelist_selected_index",
            rows=3, maxrows=3)

        row2 = left_col.row(align=True)
        left_col = row2.column()
        left_col.operator("pcl4.line_list_new_item", text="Add")
        right_col = row2.column()
        right_col.operator("pcl4.line_list_remove_item", text="Remove")
        right_col.enabled = tree.get_selected_line() is not None

        split = split.split(factor=1.0)
        right_col = split.column()
        right_col.separator(factor=4.0)
        up_button = right_col.operator("pcl4.line_list_move_item", icon="TRIA_UP", text="")
        up_button.button_type = "UP"
        down_button = right_col.operator("pcl4.line_list_move_item", icon="TRIA_DOWN", text="")
        down_button.button_type = "DOWN"

        right_col.enabled = len(tree.enumerate_lines()) >= 2

        split_p = split_p.split(factor=1.0)
        split_p.column()
        layout.separator(factor=0.25)


class PCL4_PT_line(PCL4_PT_PencilLineList_mixin, LineNodePanel.PCL4_PT_line_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_line_parameters_for_linelist"

    @classmethod
    def poll(cls, context):
        return cls.linelist_poll(context) and super().poll(context) and not PencilNodeTree.show_node_params(context)


class PCL4_PT_lineset(PCL4_PT_PencilLineList_mixin, LineNodePanel.PCL4_PT_lineset_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_for_linelist"

    @classmethod
    def poll(cls, context):
        return cls.linelist_poll(context) and super().poll(context) and not PencilNodeTree.show_node_params(context)


class PCL4_PT_lineset_brush(PCL4_PT_PencilLineList_mixin, LineNodePanel.PCL4_PT_lineset_brush_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_brush_for_linelist"
    bl_parent_id = "PCL4_PT_lineset_for_linelist"


class PCL4_PT_lineset_edge(PCL4_PT_PencilLineList_mixin, LineNodePanel.PCL4_PT_lineset_edge_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_edge_for_linelist"
    bl_parent_id = "PCL4_PT_lineset_for_linelist"
 

class PCL4_PT_lineset_reduction(PCL4_PT_PencilLineList_mixin, LineNodePanel.PCL4_PT_lineset_reduction_base, bpy.types.Panel):
    bl_idname = "PCL4_PT_lineset_reduction_for_linelist"
    bl_parent_id = "PCL4_PT_lineset_for_linelist"


class PCL4_OT_LineListNewItemOperator(bpy.types.Operator):
    bl_idname = "pcl4.line_list_new_item"
    bl_label = "New Item"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        node_tree = PencilNodeTree.tree_from_context(context)
        for node in node_tree.nodes:
            node.select = False
        lines = node_tree.enumerate_lines()

        new_node = node_tree.nodes.new(type=LineNode.bl_idname)
        location = [0, 0] if len(lines) == 0 else lines[-1].location
        while(next((x for x in lines if abs(x.location[0] - location[0]) < 1 and abs(x.location[1] - location[1]) < 1), None)):
            location = [location[0], location[1] -200]
        new_node.location = location
        new_node.name = LineNode.bl_label
        new_node.select = True
        node_tree.nodes.active = new_node
        node_tree.set_selected_line(new_node)
        return {"FINISHED"}


class PCL4_OT_LineListRemoveItemOperator(bpy.types.Operator):
    bl_idname = "pcl4.line_list_remove_item"
    bl_label = "Remove Item"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        node_tree = PencilNodeTree.tree_from_context(context)
        node_to_remove = node_tree.get_selected_line()
        if node_to_remove is None:
            return {"CANCELLED"}

        lines = node_tree.enumerate_lines()
        index = lines.index(node_to_remove)
        node_to_select = (lines[index + 1] if index < len(lines) - 1 else lines[index - 1]) if len(lines) > 0 else None 

        node_to_remove.delete_if_unused(node_tree)
        node_tree.set_selected_line(node_to_select)

        return {"FINISHED"}


class PCL4_OT_LineListMoveItemOperator(bpy.types.Operator):
    bl_idname = "pcl4.line_list_move_item"
    bl_label = "Move Item"
    bl_options = {"REGISTER", "UNDO"}

    button_type: bpy.props.StringProperty(default="UP")

    def execute(self, context):
        node_tree = PencilNodeTree.tree_from_context(context)
        src_node = node_tree.get_selected_line()

        if src_node is None:
            return {"CANCELLED"}

        ofs = -1 if self.button_type == "UP" else 1 if self.button_type == "DOWN" else 0
        if ofs == 0:
            return {"CANCELLED"}

        lines = node_tree.enumerate_lines()
        src_index = lines.index(src_node)
        tgt_index = src_index + ofs
        if tgt_index < 0 or len(lines) <= tgt_index:
            return {"CANCELLED"}

        tgt_node = lines[tgt_index]
        src_node.render_priority, tgt_node.render_priority = tgt_node.render_priority, src_node.render_priority
        lines[src_index], lines[tgt_index] = tgt_node, src_node

        # render_priorityの設定値が重複している場合、正しく移動できないのでpriorityを再計算する
        # render_priorityは負数を許可していないので別のint配列を作っておく
        priorities = list(x.render_priority for x in lines)
        
        # リストの上方向のpriority計算
        for i in range(min(src_index, tgt_index), -1, -1):
            priorities[i] = min(priorities[i], priorities[i + 1] - 1)
        priorities[0] = max(priorities[0], 0)
        
        # リストの下方向のpriority計算
        for i in range(1, len(lines), 1):
            priorities[i] = max(priorities[i], priorities[i - 1] + 1)
        
        # priorityをプロパティの反映させる
        for i in range(len(lines)):
            if lines[i].render_priority != priorities[i]:
                lines[i].render_priority = priorities[i]

        #
        node_tree.set_selected_line(src_node)

        return {"FINISHED"}


class PCL4_OT_ActivateNode(bpy.types.Operator):
    bl_idname = "pcl4.activate_node"
    bl_label = "Activate Node"

    node: bpy.props.PointerProperty(type=NamedRNAStruct)
    preferred_parent_node: bpy.props.PointerProperty(type=NamedRNAStruct)

    def set_active_node(self, context):
        tree = PencilNodeTree.tree_from_context(context)
        tree.nodes.active = self.node.get_node(context)

    def execute(self, context: bpy.context):
        tree = PencilNodeTree.tree_from_context(context)
        if tree is None:
            return {"CANCELLED"}
        self.set_active_node(context)

        parent = self.preferred_parent_node.get_node(context)
        PCL4_PT_PencilLineList.preferred_show_nodes = list() if parent is None else [parent]

        return {"FINISHED"}

def select_tree(tree, context, space_node_editor_ptr):
    if context.space_data is not None:
        context.space_data.node_tree = tree
    else:
        ptr = int(space_node_editor_ptr)
        for screen in context.blend_data.screens:
            for area in screen.areas:
                for space in area.spaces:
                    if ptr == space.as_pointer():
                        space.node_tree = tree

class PCL4_OT_NewLineNodeTree(bpy.types.Operator):
    bl_idname = "pcl4.new_line_node_tree"
    bl_label = "New Line Node Tree"

    space_node_editor_ptr: bpy.props.StringProperty(name='space_node_editor_ptr')

    def execute(self, context):
        tree = context.blend_data.node_groups.new("Pencil+ 4 Line Node Tree", "Pencil4NodeTreeType")
        select_tree(tree, context, self.space_node_editor_ptr)
        return {"FINISHED"}


class PCL4_OT_SelectDefaultTree(bpy.types.Operator):
    bl_idname = "pcl4.select_default_tree"
    bl_label = "Select Default Tree"

    space_node_editor_ptr: bpy.props.StringProperty(name='space_node_editor_ptr')

    @staticmethod
    def get_default_tree():
        return next((x for x in PencilNodeTree.enumerate_entity_trees() if x.use_fake_user or x.users > 0), None)

    def execute(self, context):
        tree = __class__.get_default_tree()
        if tree is None:
            return {"CANCELLED"}
        select_tree(tree, context, self.space_node_editor_ptr)
        return {"FINISHED"}


class PCL4_OT_SyncNodeSelection(bpy.types.Operator):
    bl_idname = "pcl4.sync_node_selection"
    bl_label = "Sync Node Selection"

    tree_ptr: bpy.props.StringProperty(name='tree_ptr')

    def execute(self, context):
        tree_ptr = int(self.tree_ptr)
        tree = next((x for x in bpy.data.node_groups if x.as_pointer() == tree_ptr), None)
        if tree is None:
            return {"CANCELLED"}

        linenodes = tree.enumerate_lines()
        active_node = tree.nodes.active

        if isinstance(active_node, LineNode):
            if active_node in linenodes:
                tree.linelist_selected_index = -1
                tree.set_selected_line(active_node) 
        elif isinstance(active_node, LineSetNode):
            line_node = tree.get_selected_line()
            if line_node and active_node in line_node.enumerate_input_nodes():
                line_node.set_selected_lineset(active_node)
            else:
                for line_node in linenodes:
                    if line_node and active_node in line_node.enumerate_input_nodes():
                        tree.set_selected_line(line_node) 
                        line_node.set_selected_lineset(active_node)
                        break

        for screen in context.blend_data.screens:
            for area in screen.areas:
                for space in area.spaces:
                    if getattr(space, "node_tree", None) == tree:
                        area.tag_redraw()

        return {"FINISHED"}