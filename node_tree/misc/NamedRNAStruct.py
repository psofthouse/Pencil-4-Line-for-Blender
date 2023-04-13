# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy

class NamedRNAStruct(bpy.types.PropertyGroup):
    ptr: bpy.props.StringProperty(default="-1")
    name: bpy.props.StringProperty(default="")

    def set(self, o: bpy.types.bpy_struct):
        if o is not None:
            self.ptr = str(o.as_pointer())
            self.name = o.name
        else:
            self.reset()
    
    def reset(self):
        if self.ptr != "-1":
            self.ptr = "-1"
            self.name = ""

    def find(self, i):
        ptr = int(self.ptr)
        ret = next((x for x in i if x is not None and x.as_pointer() == ptr), None)
        if ret is None:
            ret = next((x for x in i if x is not None and x.name == self.name), None)
        return ret

    def get_node(self, context):
        for n in context.space_data.edit_tree.nodes:
            if self == n:
                return n

    def __eq__(self, other):
            if not isinstance(other, NamedRNAStruct):
                return int(self.ptr) == other.as_pointer() or self.name == other.name
            return self.price == other.price         
