# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
from .PencilNodeMixin import PencilNodeMixin
from .PencilNodeSockets import LineSetSocket
from ..misc.NamedRNAStruct import NamedRNAStruct

LINE_SET_SOCKET_ID = "lineset"

class LineNode(bpy.types.Node, PencilNodeMixin):
    """Pencil line node"""
    bl_idname = "Pencil4LineNodeType"
    bl_label = "Line"
    bl_icon = "GREASEPENCIL"

    new_node_offset_x = -360
    new_node_step_y = -480

    line_size_type_items = (
        ("ABSOLUTE", "Absolute", "Absolute", 0),
        ('RELATIVE', "Relative (640*480)", "Relative", 1),
    )

    node_name: bpy.props.StringProperty(get=lambda self: self.name)

    is_active: bpy.props.BoolProperty(default=True)
    render_priority: bpy.props.IntProperty(default=0, min=0, max=65535)

    line_sets: bpy.props.StringProperty(default=LINE_SET_SOCKET_ID,
                                        set=lambda self, value: None)

    line_size_type: bpy.props.EnumProperty(items=line_size_type_items, default="ABSOLUTE")

    is_output_to_render_elements_only: bpy.props.BoolProperty(default=False)
    over_sampling: bpy.props.IntProperty(default=2, min=1, max=4)
    antialiasing: bpy.props.FloatProperty(default=1.0, min=0.0, max=2.0, step=1.0)
    off_screen_distance: bpy.props.FloatProperty(default=150.0, min=0.0, max=1000.0, subtype="PIXEL")
    random_seed: bpy.props.IntProperty(default=0, min=0, max=65535)

    def init(self, context):
        super().init()

        self.inputs.new(LineSetSocket.bl_idname, "Line Set", identifier=LINE_SET_SOCKET_ID)

        tree = next((x for x in bpy.data.node_groups if self in list(x.nodes)), None)
        if tree:
            other_line_nodes = list(x for x in tree.nodes if x != self and isinstance(x, LineNode))
            if len(other_line_nodes) > 0:
                self.render_priority = 1 + max(x.render_priority for x in other_line_nodes)

    def draw_buttons(self, context, layout):
        row0 = layout.row()
        row = row0.row()
        row.prop(self, "is_active", text="Active")

        for i, input in enumerate(self.inputs):
            if i < len(self.inputs) - 1 and not input.is_linked:
                row = row0.row()
                row.alignment = "RIGHT"
                row.enabled = context.space_data.edit_tree.library is None
                new_lineset_button = row.operator("pcl4.shrink_line_set", text="", icon="UNLINKED", emboss=False)
                new_lineset_button.node_name = self.name
                break

    def draw_buttons_ext(self, context, layout):
        pass

    def draw_socket(self, socket, context, layout, text):
        if isinstance(socket, LineSetSocket):
            layout.enabled = self.is_active and\
                context.space_data.edit_tree.library is None

            row = layout.row()
            connected_node = socket.get_connected_node()
            if connected_node is not None:
                row.label(text=connected_node.name, translate=False)
            else:
                button = row.operator("pcl4.new_line_set", text="", icon="NODE", emboss=False)
                button.node_name = self.name
                button.index = self.inputs.values().index(socket)

            row = layout.row(align=True)
            
            row.alignment = "RIGHT"
            button = row.operator("pcl4.insert_socket", text="", icon="ADD")
            button.node_name = self.name
            button.index = self.inputs.values().index(socket)

            button = row.operator("pcl4.remove_line_set", text="", icon="REMOVE")
            button.node_name = self.name
            button.index = self.inputs.values().index(socket)


    def update(self):
        # 末尾に未接続の入力ソケットがない場合は追加する
        if len(self.inputs) == 0 or self.inputs[-1].is_linked:
            self.insert_socket(len(self.inputs))

    def insert_socket(self, index):
            self.inputs.new(LineSetSocket.bl_idname, "Line Set", identifier=LINE_SET_SOCKET_ID)
            if index != len(self.inputs):
                self.inputs.move(len(self.inputs) - 1, index)

    def enumerate_input_nodes(self):
        return list(x.get_connected_node() for x in self.inputs)

    def get_selected_index(self):
        node = self.get_selected_lineset()
        return self.enumerate_input_nodes().index(node) if node is not None else -1

    def set_selected_index(self, value):
        node = self.inputs[value].get_connected_node() if 0 <= value and value < len(self.inputs) else None
        self.selected_lineset_node.set(node)
        if node is not None:
            tree = next((x for x in bpy.data.node_groups if node in list(x.nodes)), None)
            if tree is not None:
                tree.nodes.active = node

    lineset_selected_index: bpy.props.IntProperty(get=get_selected_index, set=set_selected_index)
    selected_lineset_node: bpy.props.PointerProperty(type=NamedRNAStruct, options={"HIDDEN", "SKIP_SAVE"})

    def get_selected_lineset(self):
        return self.selected_lineset_node.find(self.enumerate_input_nodes())

    def set_selected_lineset(self, node):
        if ((x for x in self.enumerate_input_nodes() if x is not None and x == node), None) is not None:
            self.selected_lineset_node.set(node)
            return True
        return False

    def calc_new_node_position(self, socket_index: int):
        ret = super().calc_new_node_position(0)
        step = [self.new_node_step_x, self.new_node_step_y]
        connected_nodes = [x.get_connected_node() for x in self.inputs]

        up = next((connected_nodes[i] for i in range(socket_index - 1, -1, -1) if connected_nodes[i] is not None), None)
        down = next((connected_nodes[i] for i in range(socket_index + 1, len(self.inputs), ) if connected_nodes[i] is not None), None)
        if (up is not None and down is not None):
            ret[0] = (up.location[0] + down.location[0]) / 2
            ret[1] = (up.location[1] + down.location[1]) / 2
            step = [20, -20]
        elif (up is not None):
            ret = up.location
        elif (down is not None):
            ret = down.location
            step[1] = -step[1]

        while(next((x for x in connected_nodes if x is not None and
                    abs(x.location[0] - ret[0]) < 1 and
                    abs(x.location[1] - ret[1]) < 1), None)):
            ret = [ret[0] + step[0], ret[1] + step[1]]
        
        return ret
