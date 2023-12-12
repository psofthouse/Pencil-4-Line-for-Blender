# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy

from ..nodes.ReductionSettingsNode import ReductionSettingsNode
from ..PencilNodeTree import PencilNodeTree
from ..misc.GuiUtils import layout_prop
from ...i18n import Translation

class PCL4_PT_reduction_settings(bpy.types.Panel):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"
    bl_label = "Start and End"
    bl_translation_context = Translation.ctxt
    bl_order = 100

    @classmethod
    def poll(cls, context):
        return context.active_node is not None and isinstance(context.active_node, ReductionSettingsNode) and PencilNodeTree.show_node_params(context)

    def draw(self, context):
        layout = self.layout
        layout.enabled = PencilNodeTree.tree_from_context(context).is_entity()
        node = context.active_node

        row = layout.row(align=True)
        layout_prop(context, row, node, "reduction_start", text="Start", text_ctxt=Translation.ctxt)
        layout_prop(context, row, node, "reduction_end", text="End", text_ctxt=Translation.ctxt)

        layout.separator()
        row = layout.row(align=True)
        layout_prop(context, row, node, "refer_object_on", text="Refer Object", text_ctxt=Translation.ctxt)
        col = row.column()
        col.enabled = node.refer_object_on
        layout_prop(context, col, node, "object_reference", text="", text_ctxt=Translation.ctxt)

        layout.separator()

        data = node.get_curve_data(node.curve)
        if data is not None:
            layout.template_curve_mapping(data, "mapping")

        

