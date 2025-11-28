# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy


# Cache for Blender version detection (checked once at module load)
_HAS_NODE_TREE_PROPERTY = "node_tree" in bpy.types.Scene.bl_rna.properties


def get_compositing_node_group_from_scene(scene: bpy.types.Scene) -> bpy.types.NodeTree:
    if _HAS_NODE_TREE_PROPERTY:
        return scene.node_tree
    return scene.compositing_node_group
