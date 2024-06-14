# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import math

from .PencilNodeMixin import PencilNodeMixin
from .PencilNodeSockets import *
from ...i18n import Translation


class TextureMapNode(bpy.types.Node, PencilNodeMixin):
    """Texture Map Node"""
    bl_idname = "Pencil4TextureMapNodeType"
    bl_label = "Texture Map"
    bl_icon = "GREASEPENCIL"

    source_type_items = (
        ("IMAGE", "Image", "", 0),
        ("OBJECTCOLOR", "Object Color", "", 1),
    )

    wrap_mode_items = (
        ("REPEAT", "Repeat", "Repeat", 0),
        ("CLAMP", "Clamp", "Clamp", 1),
        ("MIRROR", "Mirror", "Mirror", 2),
        ("MIRROR_ONCE", "Mirror Once", "Mirror Once", 3),
        ("CLIP", "Clip", "Clip", 4)
    )

    filter_mode_items = (
        ("POINT", "Point", "Point", 0),
        ("BILINEAR", "Bilinear", "Bilinear", 1),
    )

    uv_source_items = (
        ("SCREEN", "Screen", "", 0),
        ("OBJECTUV", "Object UV", "", 1),
    )

    selection_mode_items = (
        ("INDEX", "Index", "", 0),
        ("NAME", "Name", "", 1),
    )

    source_type: bpy.props.EnumProperty(items=source_type_items, default="IMAGE", override={'LIBRARY_OVERRIDABLE'})

    image: bpy.props.PointerProperty(type=bpy.types.Image, override={'LIBRARY_OVERRIDABLE'})
    wrap_mode_u: bpy.props.EnumProperty(items=wrap_mode_items, default="REPEAT", override={'LIBRARY_OVERRIDABLE'})
    wrap_mode_v: bpy.props.EnumProperty(items=wrap_mode_items, default="REPEAT", override={'LIBRARY_OVERRIDABLE'})
    filter_mode: bpy.props.EnumProperty(items=filter_mode_items, default="BILINEAR", override={'LIBRARY_OVERRIDABLE'})
    tiling: bpy.props.FloatVectorProperty(subtype="XYZ", size=2, default=[1.0, 1.0], override={'LIBRARY_OVERRIDABLE'})
    offset: bpy.props.FloatVectorProperty(subtype="XYZ", size=2, default=[0.0, 0.0], override={'LIBRARY_OVERRIDABLE'})
    rotation: bpy.props.FloatProperty(default=0.0, min=-20*math.pi, max=20*math.pi, subtype="ANGLE", override={'LIBRARY_OVERRIDABLE'})

    uv_source: bpy.props.EnumProperty(items=uv_source_items, default="SCREEN", override={'LIBRARY_OVERRIDABLE'})
    uv_selection_mode: bpy.props.EnumProperty(items=selection_mode_items, default="INDEX", override={'LIBRARY_OVERRIDABLE'})
    uv_index: bpy.props.IntProperty(default=0, min=0, max=7, override={'LIBRARY_OVERRIDABLE'})
    uv_name: bpy.props.StringProperty(default="UVMap", override={'LIBRARY_OVERRIDABLE'})

    object_color_selection_mode: bpy.props.EnumProperty(items=selection_mode_items, default="INDEX", override={'LIBRARY_OVERRIDABLE'})
    object_color_index: bpy.props.IntProperty(default=0, min=0, max=7, override={'LIBRARY_OVERRIDABLE'})
    object_color_name: bpy.props.StringProperty(default="Color", override={'LIBRARY_OVERRIDABLE'})

    def init(self, context):
        super().init()
        self.outputs.new(TextureMapSocket.bl_idname, "Output")

    def draw_buttons_ext(self, context, layout):
        pass

    def draw_socket(self, socket, context, layout, text):
        layout.label(text=socket.name, text_ctxt=Translation.ctxt)

    def migrate(self):
        old_uv_source = self.get("texture_uv_source", None)
        if old_uv_source is not None:
            if old_uv_source == 0:
                self.uv_source = "SCREEN"
            else:
                self.uv_source = "OBJECTUV"
                self.uv_selection_mode = "INDEX"
                self.uv_index = old_uv_source - 1
            del self["texture_uv_source"]
