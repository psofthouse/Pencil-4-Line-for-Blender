# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

if "bpy" in locals():
    import imp
    imp.reload(pencil4_render_images)
    imp.reload(Translation)
else:
    from . import pencil4_render_images
    from .i18n import Translation

import bpy

class PCL4_OT_AddImageNode(bpy.types.Operator):
    bl_idname = "pcl4.add_image_node"
    bl_label = "Add Image Node"
    bl_options = {'REGISTER', 'UNDO'}

    view_layer: bpy.props.StringProperty(default = "", options = {'HIDDEN'})
    for_render_element: bpy.props.BoolProperty(default = False, options = {'HIDDEN'})
    target_element_ptr: bpy.props.StringProperty(default = "", options = {'HIDDEN'})

    def execute(self, context):
        view_layer = context.scene.view_layers[self.view_layer]

        image = None
        if self.for_render_element:
            if self.target_element_ptr != "":
                ptr = int(self.target_element_ptr)
                render_elements = view_layer.pencil4_line_outputs.render_elements
                elem = next((e for e in render_elements if e.as_pointer() == ptr), None)
                image = elem.output.main if elem is not None else None
            else:
                image = pencil4_render_images.new_element_image(view_layer)
        else:
            image = pencil4_render_images.get_image(view_layer)
        if image is None or image.name == "":
            return {'CANCELLED'}

        bpy.ops.node.add_node(type="CompositorNodeImage",
            use_transform=True,
            settings=[{"name":"image", "value":f"bpy.data.images['{image.name}']"}])
        return bpy.ops.node.translate_attach_remove_on_cancel('INVOKE_DEFAULT')


class PCL4_OT_DeleteLineRenderElement(bpy.types.Operator):
    bl_idname = "pcl4.delete_line_render_element"
    bl_label = "Delete Line Render Element"
    bl_options = {'REGISTER', 'UNDO'}

    view_layer: bpy.props.StringProperty(default = "", options = {'HIDDEN'})
    target_element_ptr: bpy.props.StringProperty(default = "", options = {'HIDDEN'})

    def execute(self, context):
        view_layer = context.scene.view_layers[self.view_layer]
        ptr = int(self.target_element_ptr)
        render_elements = view_layer.pencil4_line_outputs.render_elements
        for i, elem in enumerate(render_elements):
            if elem.as_pointer() == ptr:
                image = elem.output.main
                render_elements.remove(i)

                if image is not None:
                    tree = context.scene.node_tree
                    if tree is not None:
                        remove_nodes = [n for n in tree.nodes if n.type == "IMAGE" and n.image == image]
                        for n in remove_nodes:
                            tree.nodes.remove(n)

                break

        return {'FINISHED'}


class PCL4_MT_ViewLayers(bpy.types.Menu):
    bl_label = 'Pencil+ 4'
    bl_idname = 'PCL4_MT_ViewLayers'

    def draw(self, context):
        layout = self.layout
        layout.enabled = context.space_data.node_tree is not None
        for view_layer in context.scene.view_layers:
            ops = layout.operator(PCL4_OT_AddImageNode.bl_idname, text=view_layer.name, translate=False)
            ops.view_layer = view_layer.name
            ops.for_render_element = False
            ops.target_element_ptr = ""


class PCL4_MT_ElementAddDelete(bpy.types.Menu):
    bl_label = 'Pencil+ 4 Line Render Element Add Delete'
    bl_idname = 'PCL4_MT_Element_Add_Delete'

    def draw(self, context):
        layout = self.layout
        layout.enabled = context.space_data.node_tree is not None

        ops = layout.operator(PCL4_OT_AddImageNode.bl_idname, text="Add", text_ctxt=Translation.ctxt)
        ops.view_layer = context.view_layer.name
        ops.for_render_element = True
        ops.target_element_ptr = str(context.element.as_pointer())

        ops = layout.operator(PCL4_OT_DeleteLineRenderElement.bl_idname, text="Delete", text_ctxt=Translation.ctxt)
        ops.view_layer = context.view_layer.name
        ops.target_element_ptr = str(context.element.as_pointer())


class PCL4_MT_ElementSelector(bpy.types.Menu):
    bl_label = 'Pencil+ 4 Line Render Element Selector'
    bl_idname = 'PCL4_MT_Element_Selector'

    def draw(self, context):
        layout = self.layout
        layout.enabled = context.space_data.node_tree is not None

        ops = layout.operator(PCL4_OT_AddImageNode.bl_idname, text="New", text_ctxt=Translation.ctxt)
        ops.view_layer = context.view_layer.name
        ops.for_render_element = True
        ops.target_element_ptr = ""

        elements = context.view_layer.pencil4_line_outputs.render_elements
        if len(elements) > 0:
            layout.separator()
            for elem in elements:
                row = layout.row()
                row.context_pointer_set("view_layer", context.view_layer)
                row.context_pointer_set("element", elem)
                image = elem.output.main
                row.menu(PCL4_MT_ElementAddDelete.bl_idname, text=image.name if image else "None", translate=False)


class PCL4_MT_ElementViewLayers(bpy.types.Menu):
    bl_label = 'Pencil+ 4 Line Render Element'
    bl_idname = 'PCL4_MT_Element_ViewLayers'
    bl_translation_context = Translation.ctxt

    def draw(self, context):
        layout = self.layout
        layout.enabled = context.space_data.node_tree is not None
        for view_layer in context.scene.view_layers:
            row = layout.row()
            row.context_pointer_set("view_layer", view_layer)
            row.menu(PCL4_MT_ElementSelector.bl_idname, text=view_layer.name, translate=False)


def menu_fn(self, context):
    if context.area.ui_type == 'CompositorNodeTree':
        layout = self.layout
        layout.separator()
        self.layout.menu(PCL4_MT_ViewLayers.bl_idname)
        self.layout.menu(PCL4_MT_ElementViewLayers.bl_idname)


def register_menu():
    bpy.types.NODE_MT_add.append(menu_fn)


def unregister_menu():
    bpy.types.NODE_MT_add.remove(menu_fn)


class PCL4_PT_LineRenderElement(bpy.types.Panel):
    bl_idname = "PCL4_PT_line_render_element"
    
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"
    bl_label = "Render Element"
    bl_translation_context = Translation.ctxt
    bl_order = 0

    @classmethod
    def poll(cls, context):
        tree: bpy.types.NodeTree = context.space_data.node_tree
        if tree is None or tree != context.scene.node_tree:
            return False

        node = tree.nodes.active
        if node is None or node.bl_idname != "CompositorNodeImage":
            return False

        for view_layer in context.scene.view_layers:
            if view_layer.pencil4_line_outputs.contains_in_render_elements(node.image):
                return True
        
        return False
        
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        node = context.space_data.node_tree.nodes.active

        for view_layer in context.scene.view_layers:
            elem = view_layer.pencil4_line_outputs.get_render_element_from_image(node.image)
            if elem is not None:
                break
        
        if elem is None:
            return
        
        def prop(prop_name, label_text):
            col.prop(elem, prop_name, text=label_text, text_ctxt=Translation.ctxt)

        col = layout.column(align=True)
        enum_property(col, elem, "element_type", pencil4_render_images.RenderElement.element_type_items, text="Output Element")
        col = col.column(align=True)
        col.enabled = elem.element_type != "COLOR"
        prop("z_min", "Z Min")
        prop("z_max", "Z Max")

        col = layout.column(align=True, heading="Background Color", heading_ctxt=Translation.ctxt)
        prop("enalbe_background_color", "On")
        col = col.column()
        col.enabled = elem.enalbe_background_color
        prop("background_color", " ")

        col = layout.column(align=True, heading="Output Categories", heading_ctxt=Translation.ctxt)
        prop("visible_lines_on", "Visible Lines")
        prop("hidden_lines_on", "Hidden Lines")

        col = layout.column(align=True, heading="Output Edges", heading_ctxt=Translation.ctxt)
        prop("outline_on", "Outline")
        prop("object_on", "Object")
        prop("intersection_on", "Intersection")
        prop("smoothing_on", "Smoothing Boundary")
        prop("material_id_on", "Material ID Boundary")
        prop("selected_edges_on", "Selected Edges")
        prop("normal_angle_on", "Normal Angle")
        prop("wireframe_on", "Wireframe")

        col = layout.column(align=True)
        row = col.row(align=True, heading="Output Line Set IDs", heading_ctxt=Translation.ctxt)
        for i in range(8):
            row.prop(elem, "line_set_ids", text=f"{i + 1}", index=i, toggle=True)
            if i == 3:
                row = col.row(align=True)


def enum_property(layout, elem, property, items, text: str=""):
    row = layout.row()
    split = row.split(factor=0.4)
    split.use_property_split = False

    row = split.row(align=True)
    row.alignment = "RIGHT"
    row.label(text=text, text_ctxt=Translation.ctxt)
    
    selected = getattr(elem, property, "")
    split = split.split(factor=1.0)
    row = split.row(align=True)
    for item in items:
        ot = row.operator("pcl4.select_element_enum_prop",
            text=item[1], depress=item[0] == selected, text_ctxt=Translation.ctxt)
        ot.elem_ptr = str(elem.as_pointer())
        ot.prop_name = property
        ot.item = item[0]

class PCL4_OT_SELECT_ELEMENT_ENUM_PROP(bpy.types.Operator):
    bl_idname = "pcl4.select_element_enum_prop"
    bl_label = "Select Element Enum Prop"

    elem_ptr: bpy.props.StringProperty()
    prop_name: bpy.props.StringProperty()
    item: bpy.props.StringProperty()

    def execute(self, context):
        ptr = int(self.elem_ptr)
        for view_layer in context.scene.view_layers:
            for elem in view_layer.pencil4_line_outputs.render_elements:
                if elem.as_pointer() == ptr:
                    setattr(elem, self.prop_name, self.item)
                    return {"FINISHED"}
        return {"CANCELLED"}
