# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy

from .PencilNodeMixin import *
from .PencilNodeSockets import *
from ..misc.PencilCurves import *
from ...i18n import Translation


class ReductionSettingsNode(bpy.types.Node, PencilNodeMixin):
    """Reduction Settings Node"""
    bl_idname = "Pencil4ReductionSettingsNodeType"
    bl_label = "Reduction Settings"
    bl_icon = "GREASEPENCIL"

    reduction_start: bpy.props.FloatProperty(default=1.0, min=0.01, max=100000.0, soft_min=0.01, soft_max=100.0, subtype="DISTANCE", override={'LIBRARY_OVERRIDABLE'})
    reduction_end: bpy.props.FloatProperty(default=10.0, min=0.01, max=100000.0, soft_min=0.01, soft_max=100.0, subtype="DISTANCE", override={'LIBRARY_OVERRIDABLE'})
    curve: bpy.props.StringProperty(default="")
    refer_object_on: bpy.props.BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
    object_reference: bpy.props.PointerProperty(type=bpy.types.Object, override={'LIBRARY_OVERRIDABLE'})

    def init(self, context):
        super().init()
        self.outputs.new(ReductionSettingsSocket.bl_idname, "Output")
        self.curve = self.create_curve_data([[0.0, 1.0], [0.2, 0.4], [1.0, 0.1]])

    def free(self):
        self.delete_curve_data("curve")

    def draw_socket(self, socket, context, layout, text):
        layout.label(text=socket.name, text_ctxt=Translation.ctxt)
