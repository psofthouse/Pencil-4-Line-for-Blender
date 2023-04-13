# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

from typing import Iterable
import bpy
from ..nodes.LineSetNode import LineSetNode

class MaterialMap(bpy.types.PropertyGroup):
    source: bpy.props.PointerProperty(type=bpy.types.Material)
    name: bpy.props.StringProperty()

class ObjectMap(bpy.types.PropertyGroup):
    source: bpy.props.PointerProperty(type=bpy.types.Object)
    name: bpy.props.StringProperty()

class IDMapMixin:
    def _record(self, tree: bpy.types.NodeTree, prop_name: str):
        self.clear()

        targets = set()
        for lineset in (x for x in tree.nodes if isinstance(x, LineSetNode)):
            prop = getattr(lineset, prop_name)
            for target in (x.content for x in prop if x is not None):
                targets.add(target)

        for target in targets:
            map = self.maps.add()
            map.source = target
            map.name = target.name

    def clear(self):
        self.maps.clear()
    
    def replacement_dict(self, dst_iterable:Iterable[bpy.types.ID]) -> dict[bpy.types.ID, bpy.types.ID]:
        dst_name_dict = {}
        for m in (m for m in dst_iterable if m.library is None):
            dst_name_dict[m.name] = m
        ret = {}
        for map in self.maps:
            if not map.source in dst_iterable:
                ret[map.source] = dst_name_dict.get(map.name, map.source)
        return ret

    def has_data(self):
        return len(self.maps) > 0

class MaterialIDMap(bpy.types.PropertyGroup, IDMapMixin):
    maps: bpy.props.CollectionProperty(type=MaterialMap)

    def record(self, tree: bpy.types.NodeTree):
        self._record(tree, "materials")

class ObjectIDMap(bpy.types.PropertyGroup, IDMapMixin):
    maps: bpy.props.CollectionProperty(type=ObjectMap)

    def record(self, tree: bpy.types.NodeTree):
        self._record(tree, "objects")
