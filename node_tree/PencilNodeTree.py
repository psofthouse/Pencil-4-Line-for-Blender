# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

from pathlib import Path
import sys
import platform
import bpy
import itertools
from ..misc import cpp_ulits
from .misc import PencilCurves
from .misc.NamedRNAStruct import NamedRNAStruct
from .misc.IDMap import MaterialIDMap
from .misc.IDMap import ObjectIDMap
from .misc import DataUtils
from .misc import GuiUtils
from .misc import AttrOverride
from .nodes.LineNode import LineNode
from .nodes.LineSetNode import LineSetNode
from .nodes.BrushSettingsNode import BrushSettingsNode
from .nodes.BrushDetailNode import BrushDetailNode
from .nodes.ReductionSettingsNode import ReductionSettingsNode
from .nodes.TextureMapNode import TextureMapNode
from .nodes.LineFunctionsNode import LineFunctionsContainerNode
from .nodes.PencilNodeMixin import PencilNodeMixin
from ..i18n import Translation


class PencilNodeTree(bpy.types.NodeTree):
    bl_idname = "Pencil4NodeTreeType"
    bl_label = "Pencil+ 4 Line"
    bl_icon = 'EVENT_P'

    @classmethod
    def is_exist(cls):
        for x in bpy.data.node_groups:
            if isinstance(x, cls):
                return True
        return False

    @classmethod
    def is_entity_exist(cls):
        for x in bpy.data.node_groups:
            if isinstance(x, cls) and x.is_entity():
                return True
        return False

    @classmethod
    def enumerate_trees(cls):
        return list(x for x in bpy.data.node_groups if isinstance(x, cls))

    @classmethod
    def enumerate_entity_trees(cls):
        return list(x for x in bpy.data.node_groups if isinstance(x, cls) and x.is_entity())

    @classmethod
    def tree_from_context(cls, context):
        return context.space_data.edit_tree if isinstance(context.space_data.edit_tree, cls) else None

    def is_entity(self):
        return self.library is None

    @classmethod
    def poll(cls, context):
        return True

    def update(self):
        for screen in bpy.data.screens:
            GuiUtils.update_view3d_area(screen)

        if self.first_update:
            if self.is_entity():
                self.use_fake_user = True
            else:
                self.material_id_map.record(self)
                self.object_id_map.record(self)
                bpy.app.timers.register(
                    lambda: self.__node_tree_post_linked(),
                    first_interval=0.0)
            self.first_update = False

        # 不適正なノードリンクを削除
        links_to_remove = []
        for link in self.links:
            if isinstance(link.to_socket.node, bpy.types.NodeReroute):
                continue
            from_soket = link.to_socket.get_connected_node_socket()
            if from_soket is not None and link.to_socket.bl_idname != from_soket.bl_idname:
                links_to_remove.append(link)
        for l in links_to_remove:
            self.links.remove(l)

        # ラインリスト表示の選択状態が空の場合、先頭のラインを選択するように試みる
        if self.get_selected_line() is None:
            lines = self.enumerate_lines()
            if len(lines) > 0:
                self.set_selected_line(lines[0])

    @classmethod
    def generate_cpp_nodes(cls, depsgraph: bpy.types.Depsgraph=None):
        if platform.system() == "Windows":
            if sys.version_info.major == 3 and sys.version_info.minor == 9:
                from ..bin import pencil4line_for_blender_win64_39 as cpp
            elif sys.version_info.major == 3 and sys.version_info.minor == 10:
                from ..bin import pencil4line_for_blender_win64_310 as cpp
            elif sys.version_info.major == 3 and sys.version_info.minor == 11:
                from ..bin import pencil4line_for_blender_win64_311 as cpp
        elif platform.system() == "Darwin":
            if sys.version_info.major == 3 and sys.version_info.minor == 9:
                from ..bin import pencil4line_for_blender_mac_39 as cpp
            elif sys.version_info.major == 3 and sys.version_info.minor == 10:
                from ..bin import pencil4line_for_blender_mac_310 as cpp
            elif sys.version_info.major == 3 and sys.version_info.minor == 11:
                from ..bin import pencil4line_for_blender_mac_311 as cpp
        elif platform.system() == "Linux":
            if sys.version_info.major == 3 and sys.version_info.minor == 9:
                from ..bin import pencil4line_for_blender_linux_39 as cpp
            elif sys.version_info.major == 3 and sys.version_info.minor == 10:
                from ..bin import pencil4line_for_blender_linux_310 as cpp
            elif sys.version_info.major == 3 and sys.version_info.minor == 11:
                from ..bin import pencil4line_for_blender_linux_311 as cpp

        # C++側に渡すためのノードのインスタンスを生成
        node_dict = {}

        # 全てのPencilNodeTree配下のノードを列挙
        for py_node in cls.__enumerate_all_nodes_for_render():
            if not isinstance(py_node, PencilNodeMixin) or py_node.mute:
                continue
            if isinstance(py_node, LineNode):
                if not AttrOverride.get_overrided_attr(py_node, "is_active", depsgraph=depsgraph):
                    continue
                cpp_node = cpp.line_node()
            elif isinstance(py_node, LineSetNode):
                if not AttrOverride.get_overrided_attr(py_node, "is_on", depsgraph=depsgraph):
                    continue
                cpp_node = cpp.line_set_node()
            elif isinstance(py_node, BrushSettingsNode):
                cpp_node = cpp.brush_settings_node()
            elif isinstance(py_node, BrushDetailNode):
                cpp_node = cpp.brush_detail_node()
            elif isinstance(py_node, ReductionSettingsNode):
                cpp_node = cpp.reduction_settings_node()
            elif isinstance(py_node, TextureMapNode):
                cpp_node = cpp.texture_map_node()
            node_dict[py_node] = cpp_node

        line_function_nodes_dict = {}
        for mat in bpy.data.materials:
            py_node = LineFunctionsContainerNode.get_linked_line_functions_node(mat)
            if py_node:
                if not py_node in line_function_nodes_dict:
                    line_function_nodes_dict[py_node] = []
                    cpp_node = cpp.line_functions_node()
                    node_dict[py_node] = cpp_node
                line_function_nodes_dict[py_node].append(mat)

        # 各ノードに値を詰める
        for py_node, cpp_node in node_dict.items():
            cpp_ulits.copy_props(py_node, cpp_node, node_dict, depsgraph=depsgraph)

        for py_node, target_materials in line_function_nodes_dict.items():
            node_dict[py_node]._target_materials = target_materials

        return (list(node_dict[x] for x in cls.enumerate_all_lines() if x in node_dict),
                list(node_dict[x] for x in line_function_nodes_dict))

    def enumerate_lines(self):
        return sorted((x for x in self.nodes if x.__class__.__name__ == "LineNode"),
                      key=lambda n: (n.render_priority, n.name))

    @classmethod
    def enumerate_all_nodes(cls):
        return itertools.chain.from_iterable(tree.nodes for tree in cls.enumerate_trees())

    @classmethod
    def __enumerate_all_nodes_for_render(cls):
        override_library_references = set()
        for tree in cls.enumerate_trees():
            if tree.override_library is not None:
                override_library_references.add(tree.override_library.reference)
        return itertools.chain.from_iterable(tree.nodes for tree in cls.enumerate_trees() if tree.is_entity() or not tree in override_library_references)

    @classmethod
    def enumerate_all_lines(cls):
        return sorted((x for x in cls.enumerate_all_nodes() if x.__class__.__name__ == "LineNode"),
                      key=lambda n: (n.render_priority, n.name))

    def get_selected_index(self):
        node = self.get_selected_line()
        return self.nodes.values().index(node) if node else -1

    def set_selected_index(self, value):
        self.set_selected_line(self.nodes[value] if 0 <= value and value < len(self.nodes) else None)

    linelist_selected_index: bpy.props.IntProperty(get=get_selected_index, set=set_selected_index)
    selected_line_node: bpy.props.PointerProperty(type=NamedRNAStruct, options={"HIDDEN", "SKIP_SAVE"})

    def get_selected_line(self):
        return self.selected_line_node.find([n for n in self.nodes.values() if isinstance(n, LineNode)])

    def set_selected_line(self, node):
        if node is None and (not isinstance(node, LineNode) or not node in self.nodes.values()):
            node = None
        self.selected_line_node.set(node)
        if node is not None:
            self.nodes.active = node

    show_visible_lines: bpy.props.BoolProperty(default=True)

    def get_show_node_panel(self):
        active_node = self.nodes.active
        if not isinstance(active_node, PencilNodeMixin):
            return False
        if isinstance(active_node, LineNode):
            return False
        if isinstance(active_node, LineSetNode):
            for link in active_node.outputs[0].links:
                if link.to_socket.node is not None:
                    return False
        return True

    show_node_panel: bpy.props.BoolProperty(get=get_show_node_panel)
    preferred_parent_node_in_panel: bpy.props.PointerProperty(type=NamedRNAStruct)

    @staticmethod
    def show_node_params(context):
        tree = PencilNodeTree.tree_from_context(context)
        return tree is not None and tree.show_node_panel
    
    def get_node_hierarchy_in_panel(self) -> list:
        nodes = [None]
        active_node = self.nodes.active if isinstance(self.nodes.active, PencilNodeMixin) else None
        if self.show_node_panel and active_node is not None:
            # アクティブノードのパネルを表示する場合、選択可能な親ノードのボタンも表示する
            preferred_show_node = self.preferred_parent_node_in_panel.get_node(self.nodes)
            if active_node != preferred_show_node:
                parents = active_node.find_connected_to_nodes()
                parent = next((x for x in parents if x == preferred_show_node), None)
                if parent is None and len(parents) > 0:
                    parent = parents[0]
                if parent and not isinstance(parent, LineNode) and not isinstance(parent, LineSetNode):
                    nodes.append(parent)
            nodes.append(active_node)
        else:
            # ラインリストを表示する場合、選択中のラインセットのボタンを表示する
            line_node = self.get_selected_line()
            lineset_node = line_node.get_selected_lineset() if line_node is not None else None
            if lineset_node is not None:
                brush_settings_socket_name = "v_brush" if self.show_visible_lines else "h_brush"
                brush_settings = \
                    next(x for x in lineset_node.inputs if x.identifier == brush_settings_socket_name) \
                    .get_connected_node()
                if brush_settings is not None:
                    nodes.append(brush_settings)
        if isinstance(nodes[-1], BrushSettingsNode):
            child = nodes[-1].find_connected_from_node(nodes[-1].brush_detail_node)
            if child is not None:
                nodes.append(child)
        return nodes

    curve_node_tree: bpy.props.PointerProperty(type=bpy.types.NodeTree)

    first_update: bpy.props.BoolProperty(default=True, options={"HIDDEN", "SKIP_SAVE"})

    material_id_map: bpy.props.PointerProperty(type=MaterialIDMap, options={"HIDDEN"})
    object_id_map: bpy.props.PointerProperty(type=ObjectIDMap, options={"HIDDEN"})

    @classmethod
    def set_first_update_flag(cls):
        for tree in cls.enumerate_entity_trees():
            tree.first_update = True

    @classmethod
    def clear_first_update_flag(cls):
        for tree in cls.enumerate_entity_trees():
            tree.first_update = False

    @classmethod
    def correct_curve_tree(cls):
        for tree in cls.enumerate_entity_trees():
            if tree.curve_node_tree is None:
                tree.curve_node_tree = PencilCurves.default_tree(create_if_none=False)

    @classmethod
    def migrate_nodes(cls):
        for tree in cls.enumerate_entity_trees():
            for node in (node for node in tree.nodes if isinstance(node, PencilNodeMixin)):
                node.migrate()

    def __node_tree_post_linked(self):
        # リンク時は何もしない
        if not self.is_entity():
            return

        # アペンド時の動作
        self.use_fake_user = True

        # 関連するLine Merge Helperの削除
        remove_helpers = list(
            o for o in bpy.data.objects if o.get("pencil4_node_trees") and self in o.get("pencil4_node_trees"))
        for helper in remove_helpers:
            bpy.data.objects.remove(helper)

    @staticmethod
    def register_menu():
        bpy.types.NODE_MT_editor_menus.append(menu_fn)
        # Bridgeの方が先にロードされている場合を考慮
        if hasattr(bpy.types, "PCL4BRIDGE_MT_BridgeMenu"):
            bpy.types.PCL4BRIDGE_MT_BridgeMenu.execute_register()


    @staticmethod
    def unregister_menu():
        # Bridgeが既にロードされている場合を考慮
        if hasattr(bpy.types, "PCL4BRIDGE_MT_BridgeMenu"):
            bpy.types.PCL4BRIDGE_MT_BridgeMenu.execute_unregister()
        bpy.types.NODE_MT_editor_menus.remove(menu_fn)


class PCL4_MT_LineMergeTargets(bpy.types.Menu):
    bl_label = 'Merge into Another Line Node Tree'
    bl_idname = 'PCL4_MT_LineMergeTargets'
    bl_translation_context = Translation.ctxt

    def draw(self, context):
        layout = self.layout
        for tree in PencilNodeTree.enumerate_trees():
            row = layout.row()
            if tree == context.space_data.edit_tree:
                row.emboss = "NORMAL"
            op = row.operator(PCL4_OT_ShowMergeMenu.bl_idname,
                              text=tree.name_full, translate=False,
                              icon="LINK_BLEND" if not tree.is_entity() else
                              "APPEND_BLEND" if tree.material_id_map.has_data() else
                              "NONE")
            op.dst_tree = tree.name_full
            row.enabled = tree != context.space_data.edit_tree and tree.is_entity()


class PCL4_MT_LineEditorMenu(bpy.types.Menu):
    bl_label = 'Pencil+ 4'
    bl_idname = 'PCL4_MT_LineEditorMenu'

    def draw(self, context):
        layout = self.layout
        tree: PencilNodeTree = context.space_data.edit_tree
        row = layout.row()
        op = row.operator(PCL4_OT_CleanupListsInLineSetNodes.bl_idname)
        op.src_tree = tree.name_full
        row.enabled = tree.is_entity()
        layout.separator()
        layout.menu(PCL4_MT_LineMergeTargets.bl_idname)


def menu_fn(self, context):
    if context.area.ui_type == PencilNodeTree.bl_idname:
        self.layout.menu(PCL4_MT_LineEditorMenu.bl_idname)


class PCL4_OT_CleanupListsInLineSetNodes_mixin:
    bl_idname = "pcl4.cleanup_lists_in_line_set_nodes"
    bl_label = "Cleanup Lists in Line Set Nodes"
    bl_options = {"REGISTER", "UNDO"}
    bl_translation_context = Translation.ctxt
    src_tree: bpy.props.StringProperty(options={"HIDDEN"})
    replace_objects: bpy.props.BoolProperty(default=True)
    delete_unused_objects: bpy.props.BoolProperty(default=True)
    replace_materials: bpy.props.BoolProperty(default=True)
    delete_unused_materials: bpy.props.BoolProperty(default=True)

    def draw(self, context):
        src_tree: PencilNodeTree = next((x for x in bpy.data.node_groups if x.name_full == self.src_tree), None)
        layout = self.layout
        layout.use_property_split = False
        row = layout.row()
        row.enabled = src_tree.object_id_map.has_data()
        row.prop(self, "replace_objects", text=PCL4_OT_FixUnusedLibraryObjectsByNameMatching.bl_label, text_ctxt=Translation.ctxt)
        layout.prop(self, "delete_unused_objects", text=PCL4_OT_DeleteUnusedObjectsInLineSetNodes.bl_label, text_ctxt=Translation.ctxt)
        layout.separator()
        row = layout.row()
        row.enabled = src_tree.material_id_map.has_data()
        row.prop(self, "replace_materials", text=PCL4_OT_FixUnusedLibraryMaterialsByNameMatching.bl_label, text_ctxt=Translation.ctxt)
        layout.prop(self, "delete_unused_materials", text=PCL4_OT_DeleteUnusedMaterialsInLineSetNodes.bl_label, text_ctxt=Translation.ctxt)
        layout.separator()

    def execute(self, context):
        if self.replace_objects:
            bpy.ops.pcl4.fix_unused_library_objects_by_name_matching(tree=self.src_tree)
        if self.delete_unused_objects:
            bpy.ops.pcl4.delete_unused_objects_in_line_set_nodes(tree=self.src_tree)
        if self.replace_materials:
            bpy.ops.pcl4.fix_unused_library_materials_by_name_matching(tree=self.src_tree)
        if self.delete_unused_materials:
            bpy.ops.pcl4.delete_unused_materials_in_line_set_nodes(tree=self.src_tree)
        return {"FINISHED"}


class PCL4_OT_CleanupListsInLineSetNodes(bpy.types.Operator, PCL4_OT_CleanupListsInLineSetNodes_mixin):
    bl_idname = "pcl4.cleanup_lists_in_line_set_nodes"
    bl_label = "Cleanup Lists in Line Set Nodes"
    bl_options = {"REGISTER", "UNDO"}
    bl_translation_context = Translation.ctxt

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class PCL4_OT_Merge_mixin(PCL4_OT_CleanupListsInLineSetNodes_mixin):
    dst_tree: bpy.props.StringProperty(options={"HIDDEN"})
    replace_same_name_lines: bpy.props.BoolProperty(default=True)
 
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.prop(self, "replace_same_name_lines", text="Replace Same Name Lines", text_ctxt=Translation.ctxt)

        layout.separator()
        layout.label(text=PCL4_OT_CleanupListsInLineSetNodes_mixin.bl_label, text_ctxt=Translation.ctxt)
        super().draw(context)
 
    def execute(self, context):
        src_tree: PencilNodeTree = next((x for x in bpy.data.node_groups if x.name_full == self.src_tree), None)
        dst_tree: PencilNodeTree = next((x for x in bpy.data.node_groups if x.name_full == self.dst_tree), None)
        if not isinstance(src_tree, PencilNodeTree) or not isinstance(dst_tree, PencilNodeTree):
            return {"CANCELLED"}

        # 現在のコンテキストがノードエディターではない場合、オーバーライドを適用してオペレーターを再帰呼び出しする
        def check_context(space_data, area):
            return isinstance(space_data, bpy.types.SpaceNodeEditor) and area.ui_type == PencilNodeTree.bl_idname

        if not check_context(context.space_data, context.area):
            override = context.copy()
            workspace_prev = None

            # 既存のワークスペースにPencil+ 4 ライン ノードツリーが存在すれば、それを採用する
            def override_context():
                for workspace in bpy.data.workspaces:
                    for screen in workspace.screens:
                        for area in (x for x in screen.areas if x.ui_type == PencilNodeTree.bl_idname):
                            for space in (x for x in area.spaces if x.type == "NODE_EDITOR"):
                                override["workspace"] = workspace
                                override["screen"] = screen
                                override["area"] = area
                                override["space_data"] = space
                                return

            override_context()

            # 既存のワークスペースにノードツリーが存在しない場合、一時的にワークスペースを追加する
            if not check_context(override["space_data"], override["area"]):
                workspace_prev = context.workspace
                path = next((x for x in Path(__file__).parents if x.name == "psoft_pencil4_line"), None)
                if path is None:
                    return {"CANCELLED"}
                success = bpy.ops.workspace.append_activate(
                    idname="Pencil+ 4 Line",
                    filepath=str(path / "resources" / "workspace.blend"))
                if success != {"FINISHED"}:
                    return {"CANCELLED"}
                override_context()

                if not check_context(override["space_data"], override["area"]):
                    return {"CANCELLED"}

            # オペレーターを再帰呼び出し
            ret = bpy.ops.pcl4.merge_line_node_tree(override,
                                                    src_tree=self.src_tree,
                                                    dst_tree=self.dst_tree,
                                                    replace_same_name_lines=self.replace_same_name_lines,
                                                    replace_materials=self.replace_materials
                                                    )

            # 一時的に追加したワークスペースがあれば削除する
            if workspace_prev is not None:
                bpy.ops.workspace.delete(override)
                context.window.workspace = workspace_prev

            return ret

        # リストのクリーンアップ
        super().execute(context)

        # カーブノードツリーが異なる場合、カーブノードをコピーする
        if src_tree.curve_node_tree is not None and src_tree.curve_node_tree != dst_tree.curve_node_tree:
            curve_props = set()
            for node in src_tree.nodes:
                for prop_name in (x for x in dir(node) if "curve" in x):
                    value = getattr(node, prop_name)
                    curve = PencilCurves.get_curve_data(src_tree.curve_node_tree, value) if type(value) is str else None
                    if curve is not None:
                        curve_props.add((node, prop_name, curve))
            if len(curve_props) > 0:
                if dst_tree.curve_node_tree is None:
                    dst_tree.curve_node_tree = PencilCurves.default_tree()
                for node, prop_name, src_curve in curve_props:
                    locations = list(x.location for x in src_curve.mapping.curves[0].points)
                    dst_curve = PencilCurves.create_curve_data(dst_tree.curve_node_tree, locations=locations)
                    setattr(node, prop_name, dst_curve)

        # ノードのコピー
        if len(src_tree.nodes) > 0:
            prev_tree = context.space_data.node_tree
            context.space_data.node_tree = src_tree
            bpy.ops.node.select_all(action='SELECT')
            bpy.ops.node.clipboard_copy()

            context.space_data.node_tree = dst_tree
            if self.replace_same_name_lines:
                src_line_names = set(x.name for x in src_tree.enumerate_lines())
                remove_lines = [x for x in dst_tree.enumerate_all_lines() if x.name in src_line_names]
                for remove_line in remove_lines:
                    dst_tree.set_selected_line(remove_line)
                    bpy.ops.pcl4.line_list_remove_item()
            bpy.ops.node.select_all(action="DESELECT")
            bpy.ops.node.clipboard_paste()

            context.space_data.node_tree = prev_tree

        # ノードツリーの選択状態の変更
        for workspace in bpy.data.workspaces:
            for screen in workspace.screens:
                for area in (x for x in screen.areas if x.ui_type == PencilNodeTree.bl_idname):
                    for space in (x for x in area.spaces if x.type == "NODE_EDITOR" and x.node_tree == src_tree):
                        space.node_tree = dst_tree

        # 元のノードツリーを削除
        bpy.data.node_groups.remove(src_tree)

        return {"FINISHED"}


class PCL4_OT_MergeLineNodeTree(bpy.types.Operator, PCL4_OT_Merge_mixin):
    bl_idname = "pcl4.merge_line_node_tree"
    bl_label = "Merge Line Node Tree"
    bl_options = {"REGISTER", "UNDO"}


class PCL4_OT_ShowMergeMenu(bpy.types.Operator, PCL4_OT_Merge_mixin):
    bl_idname = "pcl4.show_line_node_tree_merge_menu"
    bl_label = "Merge Options"
    bl_translation_context = Translation.ctxt
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        self.src_tree = context.space_data.edit_tree.name_full
        return context.window_manager.invoke_props_dialog(self)


class PCL4_OT_LineSetNodes_mixin:
    tree: bpy.props.StringProperty(options={"HIDDEN"})

    def execute(self, context):
        trees = PencilNodeTree.enumerate_trees()
        if self.tree != "":
            trees = [next((x for x in trees if x.name_full == self.tree), None)]
        if len(trees) == 0 or trees[0] is None:
            return {"CANCELLED"}

        objects = DataUtils.collect_objects_in_scenes()
        materials = DataUtils.collect_materials_in_objects(objects)
        self.proc(trees, objects, materials)

        for area in context.screen.areas:
            area.tag_redraw()

        return {"FINISHED"}

    def proc(self, trees, objects, materials):
        pass


class PCL4_OT_FixUnusedLibraryMaterialsByNameMatching(bpy.types.Operator, PCL4_OT_LineSetNodes_mixin):
    bl_idname = "pcl4.fix_unused_library_materials_by_name_matching"
    bl_label = "Fix Unused Library Materials by Name Matching"
    bl_translation_context = Translation.ctxt
    bl_options = {"REGISTER", "UNDO"}

    def proc(self, trees, objects, materials):
        for tree in trees:
            replace_dict = tree.material_id_map.replacement_dict(materials)
            tree.material_id_map.clear()
            for lineset in (x for x in tree.nodes if isinstance(x, LineSetNode)):
                DataUtils.replace_collection_element(lineset, "materials", replace_dict)


class PCL4_OT_DeleteUnusedMaterialsInLineSetNodes(bpy.types.Operator, PCL4_OT_LineSetNodes_mixin):
    bl_idname = "pcl4.delete_unused_materials_in_line_set_nodes"
    bl_label = "Delete Unused Materials"
    bl_translation_context = Translation.ctxt
    bl_options = {"REGISTER", "UNDO"}

    def proc(self, trees, objects, materials):
        for tree in trees:
            for lineset in (x for x in tree.nodes if isinstance(x, LineSetNode)):
                DataUtils.remove_collection_element_not_included_in_items(lineset, "materials", materials)


class PCL4_OT_FixUnusedLibraryObjectsByNameMatching(bpy.types.Operator, PCL4_OT_LineSetNodes_mixin):
    bl_idname = "pcl4.fix_unused_library_objects_by_name_matching"
    bl_label = "Fix Unused Library Objects by Name Matching"
    bl_translation_context = Translation.ctxt
    bl_options = {"REGISTER", "UNDO"}

    def proc(self, trees, objects, materials):
        for tree in trees:
            replace_dict = tree.object_id_map.replacement_dict(objects)
            tree.object_id_map.clear()
            for lineset in (x for x in tree.nodes if isinstance(x, LineSetNode)):
                DataUtils.replace_collection_element(lineset, "objects", replace_dict)


class PCL4_OT_DeleteUnusedObjectsInLineSetNodes(bpy.types.Operator, PCL4_OT_LineSetNodes_mixin):
    bl_idname = "pcl4.delete_unused_objects_in_line_set_nodes"
    bl_label = "Delete Unused Objects"
    bl_translation_context = Translation.ctxt
    bl_options = {"REGISTER", "UNDO"}

    def proc(self, trees, objects, materials):
        for tree in trees:
            for lineset in (x for x in tree.nodes if isinstance(x, LineSetNode)):
                DataUtils.remove_collection_element_not_included_in_items(lineset, "objects", objects)
