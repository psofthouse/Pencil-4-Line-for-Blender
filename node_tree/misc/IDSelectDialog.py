# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
from . import GuiUtils

class SelectableElement(bpy.types.PropertyGroup):
    content: bpy.props.PointerProperty(type=bpy.types.ID)
    is_selected: bpy.props.BoolProperty()

class PCL4_UL_IDSelectListView(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        global current_list
        current_list = self
        layout.prop(item, "is_selected", text=item.content.name_full, translate=False)

    def filter_items(self, context, data, propname):
        global current_list
        current_list = self
        objects = list(x.content for x in getattr(data, propname))
        helper_funcs = bpy.types.UI_UL_list
        flt_flags = []
        flt_neworder = []

        if self.filter_name:
            flt_flags = helper_funcs.filter_items_by_name(self.filter_name, self.bitflag_filter_item, objects, "name_full")
        if not flt_flags:
            flt_flags = [self.bitflag_filter_item] * len(objects)

        return flt_flags, flt_neworder    

current_list: PCL4_UL_IDSelectListView = None


class IDSelectOperatorMixin:
    selected_index: bpy.props.IntProperty()

    def listing(self, context):
        return ([], [])

    def select(self, context, selected_ids:list[bpy.types.ID]):
        return {"FINISHED"}

    def clear(self, context):
        wm = context.window_manager
        wm.pcl4_id_select_dialog_elements.clear()
        current_list = None

    def cancel(self, context):
        self.clear(context)

    def execute(self, context):
        wm = context.window_manager
        selected_ids = [x.content for x in wm.pcl4_id_select_dialog_elements if x.is_selected]
        ret = self.select(context, selected_ids)
        self.clear(context)
        context.area.tag_redraw()
        GuiUtils.update_view3d_area(context.screen)
        return ret

    def invoke(self, context, event):
        self.clear(context)

        wm = context.window_manager
        ids, initial_selection = self.listing(context)
        for id in ids:
            elem:SelectableElement = wm.pcl4_id_select_dialog_elements.add()
            elem.content = id
            elem.is_selected = id in initial_selection
        
        self.selected_index = -1
        return wm.invoke_props_dialog(self, width=400)

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout

        row = layout.row()
        row.operator(PCL4_OT_IDSelectDialogAll.bl_idname)
        row.operator(PCL4_OT_IDSelectDialogNone.bl_idname)
        row.operator(PCL4_OT_IDSelectDialogInvert.bl_idname)

        layout.template_list(
            "PCL4_UL_IDSelectListView", "",
            wm, "pcl4_id_select_dialog_elements",
            self, "selected_index")

    @staticmethod
    def register_props():
        bpy.types.WindowManager.pcl4_id_select_dialog_elements = bpy.props.CollectionProperty(type=SelectableElement)

    @staticmethod
    def unregister_props():
        del bpy.types.WindowManager.pcl4_id_select_dialog_elements


def get_displaying_contents(context):
    wm = context.window_manager
    flt_flags, _ = current_list.filter_items(context, wm, "pcl4_id_select_dialog_elements")
    return set(x.content for i, x in enumerate(wm.pcl4_id_select_dialog_elements) if flt_flags[i] != 0)

class PCL4_OT_IDSelectDialogAll(bpy.types.Operator):
    bl_idname = "pcl4.id_select_dialog_all"
    bl_label = "All"

    def execute(self, context):
        displaying = get_displaying_contents(context)
        for element in context.window_manager.pcl4_id_select_dialog_elements:
            element.is_selected = element.content in displaying
        return {"FINISHED"}

class PCL4_OT_IDSelectDialogNone(bpy.types.Operator):
    bl_idname = "pcl4.id_select_dialog_none"
    bl_label = "None"

    def execute(self, context):
        for element in context.window_manager.pcl4_id_select_dialog_elements:
            element.is_selected = False
        return {"FINISHED"}

class PCL4_OT_IDSelectDialogInvert(bpy.types.Operator):
    bl_idname = "pcl4.id_select_dialog_invert"
    bl_label = "Invert"

    def execute(self, context):
        displaying = get_displaying_contents(context)
        for element in context.window_manager.pcl4_id_select_dialog_elements:
            element.is_selected = not element.is_selected if element.content in displaying else False
        return {"FINISHED"}
