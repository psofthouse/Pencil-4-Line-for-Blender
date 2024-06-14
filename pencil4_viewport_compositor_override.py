# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

if "bpy" in locals():
    import imp
    imp.reload(pencil4_render_images)
else:
    from . import pencil4_render_images

import bpy

class Manager:
    _handler = None

    @classmethod
    def _draw(cls):
        use_compositor = getattr(bpy.context.space_data.shading, "use_compositor", "DISABLED")
        if use_compositor == "DISABLED" or type(use_compositor) is bool:
            return
        depsgraph = bpy.context.view_layer.depsgraph
        if depsgraph is None:
            return
        scene = depsgraph.scene_eval
        if scene.use_nodes and scene.node_tree:
            for node in pencil4_render_images.iterate_all_pencil_image_nodes(scene.node_tree):
                if not node.mute:
                    node.mute = True
                for l in node.outputs[0].links:
                    cls._setup_input_socket_default(l)
    
    @classmethod
    def _setup_input_socket_default(cls, link: bpy.types.NodeLink):
        if isinstance(link.to_node, bpy.types.NodeReroute):
            for l in link.to_node.outputs[0].links:
                cls._setup_input_socket_default(l)
        elif link.to_socket.type == "RGBA" and any(item != 0 for item in link.to_socket.default_value):
            link.to_socket.default_value = (0, 0, 0, 0)


def register():
    Manager._handler = bpy.types.SpaceView3D.draw_handler_add(Manager._draw, (), 'WINDOW', 'PRE_VIEW')

def unregister():
    if Manager._handler:
        bpy.types.SpaceView3D.draw_handler_remove(Manager._handler, 'WINDOW')
        Manager._handler = None
