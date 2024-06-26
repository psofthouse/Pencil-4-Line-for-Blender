# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.


if "bpy" in locals():
    import imp
    imp.reload(Translation)
    imp.reload(pencil4_render_session)
else:
    from .i18n import Translation
    from . import pencil4_render_session

import bpy
import os

class PCL4_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    render_app_path: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    viewport_render_timeout: bpy.props.FloatProperty(default=2.0, min=0.5, max=10.0)
    abort_rendering_if_error_occur: bpy.props.BoolProperty(default=False)

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "render_app_path", text="PSOFT Pencil+ 4 Render App Path", text_ctxt=Translation.ctxt)
        layout.prop(self, "viewport_render_timeout", text="Viewport Preview Timeout Period", text_ctxt=Translation.ctxt)
        layout.prop(self, "abort_rendering_if_error_occur", text="Abort Rendering when Errors Occur", text_ctxt=Translation.ctxt)

        layout.separator()

        box = layout.box()
        col = box.column(align=True)
        col.alert = True
        if pencil4_render_session.get_dll_valid():
            col.label(text="If deleting or uninstalling the add-on fails,", text_ctxt=Translation.ctxt, icon='ERROR')
            col.label(text="please try the following.", text_ctxt=Translation.ctxt, icon='BLANK1')
        else:
            col.label(text="The add-on is not properly installed.", icon="ERROR", text_ctxt=Translation.ctxt)
            col.label(text="Please reinstall the add-on.", icon="BLANK1", text_ctxt=Translation.ctxt)
            col.label(text="If the installation fails, try removing the add-on following the steps below.", icon="BLANK1", text_ctxt=Translation.ctxt)

        box.separator(factor=0.25)

        col = box.column()
        col.label(text="1. Open the Pencil+ 4 Line add-on folder.", text_ctxt=Translation.ctxt)
        row = col.row(align=True)
        row.separator(factor=4.0)
        filepath = os.path.dirname(os.path.realpath(__file__))
        op = row.operator("wm.path_open", text=filepath, translate=False, icon='FILEBROWSER')
        op.filepath = filepath
        row.separator(factor=4.0)
        col.label(text="2. Terminate all Blender processes.", text_ctxt=Translation.ctxt)
        col.separator()
        col.label(text="3. Delete all the items in the Pencil+ 4 Line add-on folder.", text_ctxt=Translation.ctxt)


class PCL4_OT_ShowPreferences(bpy.types.Operator):
    bl_idname = "pcl4.show_preferences"
    bl_label = "Show Preferences"
    bl_options = {'REGISTER'}
    bl_translation_context = Translation.ctxt

    def execute(self, context):
        bpy.ops.screen.userpref_show("INVOKE_DEFAULT")
        context.preferences.active_section  = "ADDONS"
        bpy.ops.preferences.addon_expand(module = __package__)
        bpy.ops.preferences.addon_show(module = __package__)
        return {'FINISHED'}
