# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy

from .PencilNodeMixin import PencilSocketMixin


class LineSetSocket(bpy.types.NodeSocket, PencilSocketMixin):
    bl_idname = "Pencil4LineSetSocketType"
    bl_label = "Line Set Socket"
    from_node_type = "Pencil4LineSetNodeType"

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.216, 0.5)


class BrushSettingsSocket(bpy.types.NodeSocket, PencilSocketMixin):
    bl_idname = "Pencil4BrushSettingsSocketType"
    bl_label = "Brush Settings Socket"
    from_node_type = "Pencil4BrushSettingsNodeType"

    def draw_color(self, context, node):
        return (0.4, 1.0, 0.216, 0.5)


class BrushDetailSocket(bpy.types.NodeSocket, PencilSocketMixin):
    bl_idname = "Pencil4BrushDetailSocketType"
    bl_label = "Brush Detail Socket"
    from_node_type = "Pencil4BrushDetailNodeType"

    def draw_color(self, context, node):
        return (0.0, 0.9, 0.9, 0.5)


class ReductionSettingsSocket(bpy.types.NodeSocket, PencilSocketMixin):
    bl_idname = "Pencil4ReductionSettingsSocketType"
    bl_label = "Reduction Settings Socket"
    from_node_type = "Pencil4ReductionSettingsNodeType"

    def draw_color(self, context, node):
        return (0.0, 0.4, 0.9, 0.5)


class TextureMapSocket(bpy.types.NodeSocket, PencilSocketMixin):
    bl_idname = "Pencil4TextureMapSocketType"
    bl_label = "Texture Map Socket"
    from_node_type = "Pencil4TextureMapNodeType"

    def draw_color(self, context, node):
        return (0.0, 0.4, 0.9, 0.5)


classes = (
    LineSetSocket,
    BrushSettingsSocket,
    BrushDetailSocket,
    ReductionSettingsSocket,
    TextureMapSocket
)
