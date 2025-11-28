# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import nodeitems_utils

from .PencilNodeTree import PencilNodeTree
from .nodes.PencilNodeCategory import *
from .nodes.PencilNodeMixin import PencilNodeMixin
from .nodes.LineFunctionsNode import LineFunctionsContainerNode
from .misc.IDSelectDialog import IDSelectOperatorMixin

def register():
    PencilNodeMixin.target_node_tree_type = PencilNodeTree.bl_idname
    nodeitems_utils.register_node_categories('PENCIL4_NODES', node_categories)
    bpy.types.Screen.pcl4_dummy_index = bpy.props.IntProperty(default=-1, set=lambda self, val: None, get=lambda self: -1)
    bpy.types.Material.pcl4_line_functions = bpy.props.PointerProperty(type=bpy.types.Material,
        poll=lambda self, x: LineFunctionsContainerNode.get_line_functions_node(x))
    PencilNodeTree.register_menu()
    IDSelectOperatorMixin.register_props()

def unregister():
    IDSelectOperatorMixin.unregister_props()
    PencilNodeTree.unregister_menu()
    del bpy.types.Material.pcl4_line_functions
    del bpy.types.Screen.pcl4_dummy_index
    nodeitems_utils.unregister_node_categories('PENCIL4_NODES')
