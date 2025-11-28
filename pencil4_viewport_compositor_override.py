# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

if "bpy" in locals():
    import imp
    imp.reload(pencil4_render_images)
    imp.reload(compositing_utils)
else:
    from . import pencil4_render_images
    from .misc import compositing_utils

import bpy

from .misc.compositing_utils import get_compositing_node_group_from_scene

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
        compositing_node_group = get_compositing_node_group_from_scene(scene)
        if scene.use_nodes and compositing_node_group is not None:
            for node in pencil4_render_images.iterate_all_pencil_image_nodes(compositing_node_group):
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
