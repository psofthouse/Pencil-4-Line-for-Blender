# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy

# このコードについて:
# "Pencil+ Curve Helper Node Tree"というNodeTreeを裏で新規作成し、Float Curveノードを自動生成する。
# 各PencilノードのカーブはFloat Curveノードのカーブデータを乗っ取る形で表示する。

CURVE_NODE_TREE_NAME = "Pencil+ 4 Curve Helper Node Tree"
CURVE_NODE_TREE_PROP = "is_pencil4_curve_helper_node_tree"

def default_tree(create_if_none = True):
    # 既存のカーブノードツリー探索
    for tree in bpy.data.node_groups:
        if tree.library is None and tree.get(CURVE_NODE_TREE_PROP) == True:
            return tree

    # アルファ版との互換性維持のためのノードツリー探索
    for tree in bpy.data.node_groups:
        if tree.library is None and tree.name == CURVE_NODE_TREE_NAME and tree.use_fake_user:
            tree[CURVE_NODE_TREE_PROP] = True
            return tree

    # 既存のカーブノードツリーが存在しない場合、必要があれば新規のカーブノードツリーを生成する
    if create_if_none:
        tree = bpy.data.node_groups.new(CURVE_NODE_TREE_NAME, "ShaderNodeTree")
        tree[CURVE_NODE_TREE_PROP] = True
        return tree

    return None


def create_curve_data(tree: bpy.types.NodeTree, locations=None):
    cn = tree.nodes.new("ShaderNodeFloatCurve")
    cn.name = "curve"

    if locations is not None and len(locations) > 1:
        curve_mapping = cn.mapping.curves[0]
        for i, location in enumerate(locations):
            if i < len(curve_mapping.points):
                curve_mapping.points[i].location[0] = location[0]
                curve_mapping.points[i].location[1] = location[1]
            else:
                curve_mapping.points.new(location[0], location[1])
        
    return cn.name


def count_curve_reference(curve_tree: bpy.types.NodeTree, curve_node: bpy.types.Node) -> int:
    if curve_tree is None or curve_node is None:
        return 0

    ret = 0
    for tree in (x for x in bpy.data.node_groups if x.bl_idname == "Pencil4NodeTreeType" and x.curve_node_tree == curve_tree):
        for node in tree.nodes:
            for prop_name in (x for x in dir(node) if "curve" in x):
                value = getattr(node, prop_name)
                curve = get_curve_data(curve_tree, value) if type(value) is str else None
                if curve == curve_node:
                    ret = ret + 1
    return ret


def get_curve_data(tree: bpy.types.NodeTree, curve_name):
    if tree is not None and curve_name in tree.nodes:
        return tree.nodes[curve_name]
    return None


def delete_curve_data(tree: bpy.types.NodeTree, curve_name):
    node_to_remove = tree.nodes[curve_name]
    if node_to_remove is not None and count_curve_reference(tree, node_to_remove) == 0:
        tree.nodes.remove(node_to_remove)


def evaluate_curve(tree: bpy.types.NodeTree, curve_name, length):
    ret = [1.0] * length

    curve_data = get_curve_data(tree, curve_name)
    if curve_data is not None:
        curve_mapping = curve_data.mapping
        for i in range(0, length):
            position = i / (length - 1)
            ret[i] = min(1.0, curve_mapping.evaluate(curve_mapping.curves[0], position))
    
    return ret
