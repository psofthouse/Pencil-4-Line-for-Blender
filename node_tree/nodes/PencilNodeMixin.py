# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import itertools
from ..misc import PencilCurves
from ...i18n import Translation
from ..misc import GuiUtils
from ..misc import AttrOverride

class PencilNodeMixin:
    target_node_tree_type: str
    new_node_offset_x = -320
    new_node_step_x = 0
    new_node_offset_y = 0
    new_node_step_y = -80

    @classmethod
    def poll(cls, node_tree):
        return node_tree.bl_idname == cls.target_node_tree_type

    def init(self):
        pass

    def draw_label(self):
        return bpy.app.translations.pgettext(self.bl_label, msgctxt=Translation.ctxt)
    
    def delete_if_unused(self, node_tree: bpy.types.NodeTree):
        for output in self.outputs:
            if output.links:
                return

        child_nodes = set(l.from_node for l in itertools.chain.from_iterable(input.links for input in self.inputs))
        node_to_delete =  node_tree.nodes[self.name]
        node_tree.nodes.remove(node_to_delete)
        for child in child_nodes:
            child.delete_if_unused(node_tree)

    def swap_input(self, index0, index1):
        if index0 != index1:
            self.inputs.move(index0, index1)
            self.inputs.move(index1 + (1 if index0 > index1 else -1), index0)

    def find_input_socket_index(self, socket_identifier):
        for i, input in enumerate(self.inputs):
            if input.identifier == socket_identifier:
                return i

    def find_connected_from_node(self, socket_identifier):
        for input in self.inputs:
            if input.identifier == socket_identifier:
                return input.get_connected_node()

    def find_connected_to_nodes(self):
        def append_linked_node(ret, link: bpy.types.NodeLink):
            node = link.to_socket.node
            if isinstance(node, bpy.types.NodeReroute):
                for l in node.outputs[0].links:
                    append_linked_node(ret, l)
            else:
                ret.append(node)

        ret = list()
        if len(self.outputs) > 0:
            for link in self.outputs[0].links:
                append_linked_node(ret, link)
        return ret

    def calc_new_node_position(self, socket_index: int):
        return [
            self.location[0] + self.new_node_step_x * socket_index + self.new_node_offset_x,
            self.location[1] + self.new_node_step_y * socket_index + self.new_node_offset_y
        ]

    def create_new_node(self, input_socket_index, node_tree):
        socket = self.inputs[input_socket_index]
        new_node = node_tree.nodes.new(type=socket.from_node_type)
        new_node.name = new_node.__class__.bl_label
        new_node.location = self.calc_new_node_position(input_socket_index)
        node_tree.links.new(socket, new_node.outputs[0])
        return new_node

    def auto_create_node_and_return_when_property_on(self, context, socket_identifier):
        prop_name = socket_identifier + "_on"
        if getattr(self, prop_name, False):
            i, socket = next(((i, x) for i, x in enumerate(self.inputs) if not x.is_linked and x.identifier == socket_identifier), (None, None))
            if socket is not None:
                node_tree = context.space_data.edit_tree
                for node in node_tree.nodes:
                    node.select = False
                return self.create_new_node(i, node_tree)

    def auto_create_node_when_property_on(self, context, socket_identifier):
        self.auto_create_node_and_return_when_property_on(context, socket_identifier)
        GuiUtils.update_view3d_area(context.screen)

    def filtered_socket_id(self, id, context=None, depsgraph=None):
        return id if AttrOverride.get_overrided_attr(self, id + "_on", default=True, context=context, depsgraph=depsgraph) and\
                     AttrOverride.get_overrided_attr(self, id + "_amount", default=1.0, context=context, depsgraph=depsgraph) > 0 and\
                     AttrOverride.get_overrided_attr(self, id + "_opacity", default=1.0, context=context, depsgraph=depsgraph) > 0 else ""

    def tree_from_node(self):
        for tree in (x for x in bpy.data.node_groups if x.bl_idname == self.target_node_tree_type):
            if self in tree.nodes.values():
                return tree
    
    def create_curve_data(self, locations=None):
        tree = self.tree_from_node()
        if tree is None:
            return
        if tree.curve_node_tree is None:
            tree.curve_node_tree = PencilCurves.default_tree()
        return PencilCurves.create_curve_data(tree.curve_node_tree, locations)

    def get_curve_data(self, curve_name):
        tree = self.tree_from_node()
        if tree is None or tree.curve_node_tree is None:
            return
        return PencilCurves.get_curve_data(tree.curve_node_tree, curve_name)

    def delete_curve_data(self, curve_prop_name:str):
        tree = self.tree_from_node()
        if tree is None or tree.curve_node_tree is None:
            return
        curve_name = getattr(self, curve_prop_name)
        setattr(self, curve_prop_name, "")
        return PencilCurves.delete_curve_data(tree.curve_node_tree, curve_name)

    def evaluate_curve(self, curve_name, length):
        tree = self.tree_from_node()
        return PencilCurves.evaluate_curve(
            tree.curve_node_tree if tree is not None else None, curve_name, length)
    
    def get_curve_points_string(self, curve_name) -> str:
        curve = self.get_curve_data(curve_name)
        if curve is None:
            return ""
        return ";".join(f"{point.location[0]},{point.location[1]},{point.handle_type}" for point in curve.mapping.curves[0].points)
    
    def set_curve_points_string(self, curve_name, points_str: str):
        curve_points = [x for x in points_str.split(";")]
        if len(curve_points) < 2:
            return
        curve = self.get_curve_data(curve_name)
        if curve is None:
            return
        blender_points = curve.mapping.curves[0].points
        for _ in itertools.repeat(None, len(blender_points) - 2):
            blender_points.remove(blender_points[0])
        for i, point in enumerate(curve_points):
            point = point.split(",")
            if i < 2:
                blender_points[i].location[0] = float(point[0])
                blender_points[i].location[1] = float(point[1])
                blender_points[i].handle_type = point[2] if len(point) == 3 else "AUTO"
            else:
                blender_points.new(float(point[0]), float(point[1]))
                blender_points[i].handle_type = point[2] if len(point) == 3 else "AUTO"
        curve.mapping.update()

    def get_overrided_attr(self, prop_name, default=None, context=None, depsgraph=None) -> any:
        return AttrOverride.get_overrided_attr(self, prop_name, default=default, context=context, depsgraph=depsgraph)

    def migrate(self):
        pass

class PencilSocketMixin:
    def get_connected_node_socket(self, ignore_muted_link: bool = False):
        if self.is_output:
            return None
        for link in self.links:
            if ignore_muted_link and link.is_muted:
                continue
            while isinstance(link.from_socket.node, bpy.types.NodeReroute):
                if not link.from_socket.node.inputs[0].is_linked:
                    return None
                if ignore_muted_link and link.is_muted:
                    return None
                link = link.from_socket.node.inputs[0].links[0]
            return link.from_socket

    def get_connected_node(self, ignore_muted_link: bool = False):
        socket = self.get_connected_node_socket(ignore_muted_link)
        return socket.node if socket is not None else None

    def draw(self, context, layout, node, text):
        if hasattr(node, "draw_socket"):
            node.draw_socket(self, context, layout, text)
