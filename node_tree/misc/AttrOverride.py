# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
from rna_prop_ui import rna_idprop_ui_create 
from typing import Tuple 
import re
from ...i18n import Translation

def __overrided_attr(struct: bpy.types.Struct, prop_name: str, override_sources, default=None):
    if default is not None and not hasattr(struct, prop_name):
        return default, None, None
    value = getattr(struct, prop_name)
    data_path = struct.path_from_id(prop_name)
    if data_path.endswith("_on_gui"):
        data_path = data_path[:-len("_gui")]
    for source in override_sources:
        if source is None:
            continue
        override_value = None
        if data_path in source:
            override_value = source[data_path]
        else:
            for pattern, v in source.items():
                try:
                    if re.fullmatch(pattern, data_path):
                        override_value = v
                        data_path = pattern
                        break
                except:
                    pass
        if override_value is not None:
            if type(override_value) == type(value):
                return override_value, source, data_path
            if type(override_value) == int and type(value) == bool:
                return bool(override_value), source, data_path
            else:
                try:
                    if len(value) == len(override_value) and type(value[0]) == type(override_value[0]):
                        return override_value, source, data_path
                except:
                    pass
    return value, None, None

def is_overrided(id, prop_name, context) -> bool:
    _, source, _= __overrided_attr(id, prop_name, (context.view_layer, context.scene))
    return source is not None

def get_overrided_attr(id, prop_name, default=None, context=None, depsgraph=None) -> any:
    if context is not None:
        value, _, _ = __overrided_attr(id, prop_name, (context.view_layer, context.scene), default=default)
    elif depsgraph is not None:
        value, _, _ = __overrided_attr(id, prop_name, (depsgraph.view_layer_eval, depsgraph.scene_eval), default=default)
    else:
        value = getattr(id, prop_name, default)
    return value

def get_override_source(id, prop_name, context) -> Tuple[bpy.types.ID, str]:
    _, source, prop = __overrided_attr(id, prop_name, (context.view_layer, context.scene))
    return source, prop

class AddAttributeOverrideMixin:
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def get_target(cls, context):
        pass

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        prev_clipboard = context.window_manager.clipboard
        bpy.ops.ui.copy_data_path_button()
        data_path = context.window_manager.clipboard
        bpy.ops.ui.copy_data_path_button(full_path=True)
        data_path_full = context.window_manager.clipboard
        context.window_manager.clipboard = prev_clipboard

        data = None
        if data_path_full.startswith("bpy.data.node_groups"):
            local_vars = {}
            exec(f"import bpy; data = {data_path_full.rpartition('.')[0]}",  {}, local_vars)
            data = local_vars["data"]
        else:
            match = re.search(r'\["nodes\[\\"(.*?)\\"\]\.(.*?)"\]$', data_path)
            if match: 
                data_path = match.group()[2:-2].replace("\\\"", "\"")
                data = context.space_data.edit_tree.nodes.get(match.group(1))
        if data is None:
            return {"CANCELLED"}

        override_src = self.get_target(context)
        if data_path.endswith("_on_gui"):
            data_path = data_path[:-len("_gui")]
        prop_name = data_path.rsplit('.', 1)[-1]
        prop = data.__class__.bl_rna.properties[prop_name]
        if isinstance(prop, bpy.types.EnumProperty):
            return {"CANCELLED"}
        rna_idprop_ui_create(override_src, data_path,
                            default=getattr(prop, "default_array") if getattr(prop, "is_array", False) else getattr(prop, "default"),
                            min=getattr(prop, "hard_min", 0.0),
                            max=getattr(prop, "hard_max", 1.0),
                            soft_min=getattr(prop, "soft_min", None),
                            soft_max=getattr(prop, "soft_max", None),
                            description=getattr(prop, "description", None),
                            )
        ui_data = override_src.id_properties_ui(data_path)
        if hasattr(prop, "subtype"):
            if (not hasattr(bpy.types.WM_OT_properties_edit, "subtype_items") or
                prop.subtype in (t for t, _, _ in bpy.types.WM_OT_properties_edit.subtype_items)):
                ui_data.update(subtype=prop.subtype)
        if hasattr(prop, "step"):
            ui_data.update(step=prop.step)
        if hasattr(prop, "precision"):
            ui_data.update(precision=prop.precision)
        override_src[data_path] = getattr(data, prop_name)
        return {"FINISHED"}


class PCL4_OT_AddAttributeOverrideScene(AddAttributeOverrideMixin, bpy.types.Operator):
    bl_idname = "pcl4.add_attribute_override_scene"
    bl_label = "Add Attribute Override (Scene)"

    def get_target(cls, context):
        return context.scene

class PCL4_OT_AddAttributeOverrideViewLayer(AddAttributeOverrideMixin, bpy.types.Operator):
    bl_idname = "pcl4.add_attribute_override_view_layer"
    bl_label = "Add Attribute Override (ViewLayer)"

    def get_target(cls, context):
        return context.view_layer


class AttrOverrideDataPtrMixin:
    data_ptr: bpy.props.StringProperty()
    prop_name: bpy.props.StringProperty()

    def get_override_source_from_data_ptr(self) -> bpy.types.ID:
        if self.data_ptr == "" or self.prop_name == "":
            return None
        ptr = int(self.data_ptr)
        for scene in bpy.data.scenes:
            if ptr == scene.as_pointer():
                return scene
            for view_layer in scene.view_layers:
                if ptr == view_layer.as_pointer():
                    return view_layer
        return None
    
    def redraw(self, context):
        context.scene.update_tag()
        for area in (x for x in context.screen.areas if x.type == "VIEW_3D"):
            area.tag_redraw()

class PCL4_OT_RemoveAttributeOverride(AttrOverrideDataPtrMixin, bpy.types.Operator):
    bl_idname = "pcl4.remove_attribute_override"
    bl_label = "Remove Attribute Override"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        data = self.get_override_source_from_data_ptr()
        if data is None:
            return {"CANCELLED"}
        del data[self.prop_name]
        self.redraw(context)
        return {"FINISHED"}

class PCL4_OT_ToggleBoolAttributeOverride(AttrOverrideDataPtrMixin, bpy.types.Operator):
    bl_idname = "pcl4.toggle_bool_attribute_override"
    bl_label = "Toggle Bool Attribute Override"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        data = self.get_override_source_from_data_ptr()
        if data is None:
            return {"CANCELLED"}
        data[self.prop_name] = 0 if data[self.prop_name] else 1
        self.redraw(context)
        return {"FINISHED"}


class WM_MT_button_context(bpy.types.Menu):
    bl_label = "Pencil+ 4"

    def draw(self, context):
        pass

    def register():
        bpy.types.WM_MT_button_context.append(draw_menu)

    def unregister():
        bpy.types.WM_MT_button_context.remove(draw_menu)

def draw_menu(self, context: bpy.context):
    if (not isinstance(context.space_data, bpy.types.SpaceNodeEditor) or
        context.space_data.edit_tree.bl_idname != "Pencil4NodeTreeType" or
        not bpy.ops.ui.copy_data_path_button.poll()):
        return
    layout = self.layout
    layout.separator()
    layout.operator(PCL4_OT_AddAttributeOverrideScene.bl_idname, text="Attribute Override (Scene)", icon="SCENE_DATA", text_ctxt=Translation.ctxt)
    layout.operator(PCL4_OT_AddAttributeOverrideViewLayer.bl_idname, text="Attribute Override (ViewLayer)", icon="RENDERLAYERS", text_ctxt=Translation.ctxt)
