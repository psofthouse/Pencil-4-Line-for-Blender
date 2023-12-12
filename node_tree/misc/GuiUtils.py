# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
from ...i18n import Translation
from .IDSelectDialog import IDSelectOperatorMixin
from . import DataUtils
from . import AttrOverride

def layout_prop(context, layout, node, prop_name, preserve_icon_space = False, preserve_icon_space_emboss = True, **kwargs):
    source, prop = AttrOverride.get_override_source(node, prop_name, context)
    if (source is not None or preserve_icon_space) and layout.direction == "VERTICAL":
        layout = layout.row()
    if source is not None:
        if type(getattr(node, prop_name)) == bool and type(source.get(prop)) == int:
            row = layout.row(align=True)
            ot = row.operator("pcl4.toggle_bool_attribute_override", text="", icon="CHECKBOX_HLT" if source.get(prop) else "CHECKBOX_DEHLT", emboss=False)
            ot.prop_name = prop
            ot.data_ptr = str(source.as_pointer())
            if "text" in kwargs and len(kwargs["text"]) > 0:
                row.label(**kwargs)
        else:
            layout.prop(source, '["%s"]' % bpy.utils.escape_identifier(prop), **kwargs)
        ot = layout.operator("pcl4.remove_attribute_override", text="", icon_value=layout.icon(source), depress=True)
        ot.prop_name = prop
        ot.data_ptr = str(source.as_pointer())
    else:
        layout.prop(node, prop_name, **kwargs)
        if preserve_icon_space:
            ot = layout.operator("pcl4.remove_attribute_override", text="", icon="BLANK1", emboss=preserve_icon_space_emboss)
            ot.prop_name = ""
            ot.data_ptr = ""

def prop_pair(context, layout, node, prop_name0, label_text0, prop_name1, label_text1):
    row = layout.row(align=True)
    is_overrided0 = AttrOverride.is_overrided(node, prop_name0, context)
    is_overrided1 = AttrOverride.is_overrided(node, prop_name1, context)
    preserve_icon_space = is_overrided0 or is_overrided1
    layout_prop(context, row, node, prop_name0, text=label_text0, text_ctxt=Translation.ctxt, preserve_icon_space=preserve_icon_space)
    layout_prop(context, row, node, prop_name1, text=label_text1, text_ctxt=Translation.ctxt, preserve_icon_space=preserve_icon_space)

def indented_box_column(layout, split_factor=0.02, algin=False):
    split = layout.split(factor=split_factor)
    col = split.column()
    split = split.split(factor=1.0)
    box = split.box()
    col = box.column(align=algin)
    col.use_property_split = False
    return col

def map_property(context, layout, node, socket_id, heading, map_opacity_prop, map_opacity_text):
    on_prop = socket_id + "_on_gui"
    enabled = AttrOverride.get_overrided_attr(node, on_prop, context=context, default=False)

    row = layout.row()
    split = row.split(factor=0.4)
    split.use_property_split = False

    row = split.row(align=True)
    row.alignment = "RIGHT"
    layout_prop(context, row, node, on_prop, text="", text_ctxt=Translation.ctxt)
    row.label(text=heading, text_ctxt=Translation.ctxt)
    row.label(text="", icon = "TEXTURE", text_ctxt=Translation.ctxt)
    
    split = split.split(factor=1.0)
    row = split.row(align=True)
    row.enabled = enabled
    target_node = node.find_connected_from_node(socket_id)
    button = row.operator("pcl4.activate_node",
        text=target_node.name if target_node is not None else "None",
        icon = "TRACKING" if target_node is not None else "NONE")
    button.node.set(target_node)
    button.preferred_parent_node.set(node)

    if AttrOverride.is_overrided(node, map_opacity_prop, context):
        row.label(text="", icon="BLANK1")
    layout_prop(context, row, node, map_opacity_prop, text=map_opacity_text, text_ctxt=Translation.ctxt)

def enum_property(layout, node, property, items, text: str=""):
    row = layout.row()
    split = row.split(factor=0.4)
    split.use_property_split = False

    row = split.row(align=True)
    row.alignment = "RIGHT"
    row.label(text=text, text_ctxt=Translation.ctxt)
    
    selected = getattr(node, property, "")
    split = split.split(factor=1.0)
    row = split.row(align=True)
    for item in items:
        ot = row.operator("pcl4.select_enum_prop",
            text=item[1], depress=item[0] == selected, text_ctxt=Translation.ctxt)
        ot.node_name = node.name
        ot.prop_name = property
        ot.item = item[0]

def update_view3d_area(screen: bpy.types.Screen):
    if screen is not None:
        for area in (x for x in screen.areas if x.type == "VIEW_3D"):
            area.tag_redraw()

class PCL4_OT_SELECT_ENUM_PROP(bpy.types.Operator):
    bl_idname = "pcl4.select_enum_prop"
    bl_label = "Select Enum Prop"
    bl_options = {'REGISTER', 'UNDO'}

    node_name: bpy.props.StringProperty()
    prop_name: bpy.props.StringProperty()
    item: bpy.props.StringProperty()

    def execute(self, context):
        setattr(context.space_data.edit_tree.nodes[self.node_name], self.prop_name, self.item)
        update_view3d_area(context.screen)
        return {"FINISHED"}


class PCL4_UL_ObjectsListView(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.content.name_full if item.content else "", translate=False)

    def filter_items(self, context, data, propname):
        objects = list(x.content for x in getattr(data, propname))
        helper_funcs = bpy.types.UI_UL_list
        flt_flags = []
        flt_neworder = []

        if self.filter_name:
            flt_flags = helper_funcs.filter_items_by_name(self.filter_name, self.bitflag_filter_item, objects, "name_full")
        if not flt_flags:
            flt_flags = [self.bitflag_filter_item] * len(objects)

        for i, x in enumerate(objects):
            if x is None:
                flt_flags[i] = 0

        return flt_flags, flt_neworder    


class IDSelectAddRemoveOperatorMixin(IDSelectOperatorMixin):
    bl_translation_context = Translation.ctxt
    
    select_type_items = (
        ("ADD", "Add", "Add", 0),
        ('REMOVE', "Remove", "Remove", 1),
    )

    data_ptr: bpy.props.StringProperty()
    propname: bpy.props.StringProperty()
    select_type: bpy.props.EnumProperty(items=select_type_items)

    def specify_data(self, context):
        return None

    def additional_excludes(self, context):
        return set()

    def listing(self, context):
        data = self.specify_data(context)
        if data is None:
            return ([], [])
        
        content_type = DataUtils.collection_content_type(data, self.propname)

        ids = DataUtils.enumerate_ids_from_collection(data, self.propname)
        if self.select_type == "ADD":
            targets = []
            if content_type.name == bpy.types.Material.__name__:
                targets = [x for x in bpy.data.materials
                           if x.node_tree is None or all(node.bl_idname != "Pencil4LineFunctionsContainerNodeType" for node in x.node_tree.nodes)]
            elif content_type.name == bpy.types.Object.__name__:
                targets = DataUtils.collect_objects_in_data()
            exludes = set(ids) | self.additional_excludes(context)
            ids = [x for x in targets if x.override_library is None and not x in exludes]
        
        selection = set(context.selected_objects)
        if content_type.name == bpy.types.Material.__name__:
            selection = DataUtils.collect_materials_in_objects(selection)

        return (ids, selection)

    def select(self, context, selected_ids:list[bpy.types.ID]):
        data = self.specify_data(context)
        if data is None:
            {"CANCELLED"}

        if self.select_type == "ADD":
            DataUtils.append_collection_element(data, self.propname, selected_ids)
        else:
            DataUtils.remove_collection_element_included_in_items(data, self.propname, selected_ids)
        
        DataUtils.remove_none_or_duplicated_collection_element(data, self.propname)

        return {"FINISHED"}


def draw_object_material_list(layout: bpy.types.UILayout,
                              label: str,
                              id: str,
                              data,
                              propname: str,
                              add_operator: str,
                              delete_operator: str):
    layout.label(text=label, text_ctxt=Translation.ctxt)

    if data is None:
        box = layout.box()
        box.separator(factor=18.0)
        return

    layout.template_list(
        "PCL4_UL_ObjectsListView", id,
        data, propname,
        bpy.data.screens[0], "pcl4_dummy_index")

    row = layout.row(align=True)
    btAdd = row.operator(add_operator, text="Add", text_ctxt=bpy.app.translations.contexts.default)
    btAdd.data_ptr = str(data.as_pointer())
    btAdd.propname = propname
    btAdd.select_type = "ADD"
    row = row.row()
    row.enabled = len(getattr(data, propname, None)) > 0
    btDelete = row.operator(delete_operator, text="Remove", text_ctxt=bpy.app.translations.contexts.default)
    btDelete.data_ptr = str(data.as_pointer())
    btDelete.propname = propname
    btDelete.select_type = "REMOVE"
