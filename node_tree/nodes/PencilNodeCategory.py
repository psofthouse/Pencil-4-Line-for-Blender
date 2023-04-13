# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

from nodeitems_utils import NodeCategory, NodeItem

from ..PencilNodeTree import PencilNodeTree
from ...i18n import Translation

from .LineNode import LineNode
from .LineSetNode import LineSetNode
from .BrushDetailNode import BrushDetailNode
from .BrushSettingsNode import BrushSettingsNode
from .ReductionSettingsNode import ReductionSettingsNode
from .TextureMapNode import TextureMapNode

class PencilNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == PencilNodeTree.bl_idname

class PencilNodeItem(NodeItem):
    def __init__(self, nodecls):
        super().__init__(nodecls.bl_idname, label=nodecls.bl_label, settings={"name": repr(nodecls.bl_label)})

    @property
    def translation_context(self):
        return Translation.ctxt

node_categories = [
    PencilNodeCategory("PENCIL4NODES", "Pencil+ 4", items=[
        PencilNodeItem(LineNode),
        PencilNodeItem(LineSetNode),
        PencilNodeItem(BrushSettingsNode),
        PencilNodeItem(BrushDetailNode),
        PencilNodeItem(ReductionSettingsNode),
        PencilNodeItem(TextureMapNode)
    ])
]
