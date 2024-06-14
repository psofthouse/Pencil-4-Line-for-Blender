# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

if "bpy" in locals():
    import imp
    imp.reload(cpp_ulits)
else:
    from .misc import cpp_ulits

import sys
import platform
import os
import re
from typing import Tuple
import bpy
import itertools
from typing import Iterable


if platform.system() == "Windows":
    if sys.version_info.major == 3 and sys.version_info.minor == 9:
        from .bin import pencil4line_for_blender_win64_39 as cpp
    elif sys.version_info.major == 3 and sys.version_info.minor == 10:
        from .bin import pencil4line_for_blender_win64_310 as cpp
    elif sys.version_info.major == 3 and sys.version_info.minor == 11:
        from .bin import pencil4line_for_blender_win64_311 as cpp
elif platform.system() == "Darwin":
    if sys.version_info.major == 3 and sys.version_info.minor == 9:
        from .bin import pencil4line_for_blender_mac_39 as cpp
    elif sys.version_info.major == 3 and sys.version_info.minor == 10:
        from .bin import pencil4line_for_blender_mac_310 as cpp
    elif sys.version_info.major == 3 and sys.version_info.minor == 11:
        from .bin import pencil4line_for_blender_mac_311 as cpp
elif platform.system() == "Linux":
    if sys.version_info.major == 3 and sys.version_info.minor == 9:
        from .bin import pencil4line_for_blender_linux_39 as cpp
    elif sys.version_info.major == 3 and sys.version_info.minor == 10:
        from .bin import pencil4line_for_blender_linux_310 as cpp
    elif sys.version_info.major == 3 and sys.version_info.minor == 11:
        from .bin import pencil4line_for_blender_linux_311 as cpp


IMAGE_NAME_PREFIX = "Pencil+ 4."

__ID_MAIN = "Line Render"
__ID_RENDER_ELEMENT = "Line Render Element"

def get_image_name(view_layer: bpy.types.ViewLayer) -> str:
    return IMAGE_NAME_PREFIX + __ID_MAIN + "." + view_layer.name

def get_element_image_name_prefix(view_layer: bpy.types.ViewLayer) -> str:
    return IMAGE_NAME_PREFIX + __ID_RENDER_ELEMENT + "." + view_layer.name


class OutputImage(bpy.types.PropertyGroup):
    main: bpy.props.PointerProperty(type=bpy.types.Image)

    def contains(self, image:bpy.types.Image):
        if image is None:
            return False
        return self.main == image
            
    def contains_any_image(self, images:list[bpy.types.Image]):
        for image in images:
            if self.contains(image):
                return True
        return False
    
    def rename(self, name:str):
        if self.main is not None and self.main.name != name and self.main.name != "" and not self.main.name.startswith(name + "."):
            self.main.name = name

    def correct_duplicated_output_images(self, images: set):
        if self.main is not None:
            if self.main in images:
                self.main = new_image("tmp")
            else:
                images.add(self.main)

class RenderElement(bpy.types.PropertyGroup):
    output: bpy.props.PointerProperty(type=OutputImage)

    element_type_items = (
        ("COLOR", "Color", "", 0),
        ('DEPTH', "Z Depth", "", 1),
    )
    element_type: bpy.props.EnumProperty(items=element_type_items, default="COLOR")
    z_min: bpy.props.FloatProperty(default=1.0, min=0.01, max=100000.0, soft_min=0.01, soft_max=100.0, subtype="DISTANCE")
    z_max: bpy.props.FloatProperty(default=3.0, min=0.01, max=100000.0, soft_min=0.01, soft_max=100.0, subtype="DISTANCE")
    enalbe_background_color: bpy.props.BoolProperty(default=False)
    background_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=4, min=0.0, max=1.0, default=[1.0, 1.0, 1.0, 1.0])
    visible_lines_on: bpy.props.BoolProperty(default=True)
    hidden_lines_on: bpy.props.BoolProperty(default=True)
    outline_on: bpy.props.BoolProperty(default=True)
    object_on: bpy.props.BoolProperty(default=True)
    intersection_on: bpy.props.BoolProperty(default=True)
    smoothing_on: bpy.props.BoolProperty(default=True)
    material_id_on: bpy.props.BoolProperty(default=True)
    selected_edges_on: bpy.props.BoolProperty(default=True)
    normal_angle_on: bpy.props.BoolProperty(default=True)
    wireframe_on: bpy.props.BoolProperty(default=True)
    line_set_ids: bpy.props.BoolVectorProperty(size=8, default=[True, True, True, True, True, True, True, True])

class VectorOutput(bpy.types.PropertyGroup):
    file_type_items = (
        ("AIEPS", "AI(EPS)", "Adobe Illustrator 8 EPS", 0),
        ('EPS', "EPS", "Encapsulated Post Scrip", 1),
        ('PLD', "PLD", "Pencil+ Line Data", 2),
    )

    def get_output_path(self):
        for view_layer in itertools.chain.from_iterable(scene.view_layers for scene in bpy.data.scenes):
            if not view_layer.pencil4_line_outputs.output.main:
                continue
            for vector_output in view_layer.pencil4_line_outputs.vector_outputs:
                if vector_output == self:
                    sub_path = self.sub_path
                    placeholder_count = sub_path.count("#")
                    if placeholder_count == 0:
                        sub_path += str(bpy.context.scene.frame_current).zfill(4)
                    else:
                        sub_path = sub_path.replace("#" * placeholder_count, str(bpy.context.scene.frame_current).zfill(placeholder_count))

                    # base_pathに"/tmp"が設定されている場合、正確な絶対パスを取得する方法が分からないので、Image経由で絶対パスを取得する                    
                    image = view_layer.pencil4_line_outputs.output.main
                    filepath_raw = image.filepath_raw
                    image.filepath_raw = view_layer.pencil4_line_outputs.vector_output_base_path
                    path = image.filepath_from_user()
                    image.filepath_raw = filepath_raw

                    path = os.path.join(path, sub_path)
                    path += ".pld" if self.file_type == "PLD" else ".eps"
                    return path
        return ""

    def update_sub_path(self, context):
        if self.file_type == "PLD":
            if not re.match("\\<(LineName|linename|LINENAME|Linename)\\>", self.sub_path):
                self.sub_path += "_<LineName>"
        else:
            self.sub_path = re.sub("_{0,1}\\<(LineName|linename|LINENAME|Linename)\\>", "", self.sub_path)

    output_path: bpy.props.StringProperty(get=get_output_path)

    on: bpy.props.BoolProperty(default=True)
    sub_path: bpy.props.StringProperty(default="Line", subtype="FILE_NAME")

    file_type: bpy.props.EnumProperty(items=file_type_items, default="AIEPS", update=update_sub_path)
    visible_lines_on: bpy.props.BoolProperty(default=True)
    hidden_lines_on: bpy.props.BoolProperty(default=True)
    outline_on: bpy.props.BoolProperty(default=True)
    object_on: bpy.props.BoolProperty(default=True)
    intersection_on: bpy.props.BoolProperty(default=True)
    smoothing_on: bpy.props.BoolProperty(default=True)
    material_id_on: bpy.props.BoolProperty(default=True)
    selected_edges_on: bpy.props.BoolProperty(default=True)
    normal_angle_on: bpy.props.BoolProperty(default=True)
    wireframe_on: bpy.props.BoolProperty(default=True)
    line_set_ids: bpy.props.BoolVectorProperty(size=8, default=[True, True, True, True, True, True, True, True])


class ViewLayerLineOutputs(bpy.types.PropertyGroup):
    output: bpy.props.PointerProperty(type=OutputImage)
    render_elements: bpy.props.CollectionProperty(type=RenderElement)
    vector_outputs: bpy.props.CollectionProperty(type=VectorOutput)
    vector_output_selected_index: bpy.props.IntProperty(options={"HIDDEN", "SKIP_SAVE"})
    vector_output_base_path: bpy.props.StringProperty(subtype="DIR_PATH")

    fix_output_after_load: bpy.props.BoolProperty(default=True)

    def contains_in_render_elements(self, image:bpy.types.Image) -> bool:
        return self.get_render_element_from_image(image) is not None
    
    def get_render_element_from_image(self, image:bpy.types.Image) -> RenderElement:
        for elem in self.render_elements:
            if elem.output.contains(image):
                return elem
    
    def rename_images(self, view_layer: bpy.types.ViewLayer):
        self.output.rename(get_image_name(view_layer))
        for elem in self.render_elements:
            elem.output.rename(get_element_image_name_prefix(view_layer))

    def correct_duplicated_output_images(self, images: set):
        self.output.correct_duplicated_output_images(images)
        for elem in self.render_elements:
            elem.output.correct_duplicated_output_images(images)

    @staticmethod
    def on_save_pre():
        ViewLayerLineOutputs.correct_image_names()
        for view_layer in itertools.chain.from_iterable(scene.view_layers for scene in bpy.data.scenes):
            view_layer.pencil4_line_outputs.fix_output_after_load = False

    @staticmethod
    def on_load_post():
        fix_output = False
        for view_layer in itertools.chain.from_iterable(scene.view_layers for scene in bpy.data.scenes):
            if view_layer.pencil4_line_outputs.fix_output_after_load:
                fix_output = True
                break
        if fix_output:
            for scene in bpy.data.scenes:
                for view_layer in scene.view_layers:
                    if view_layer.pencil4_line_outputs.fix_output_after_load:
                        image = bpy.data.images.get(get_image_name(view_layer))
                        if image is not None:
                            view_layer.pencil4_line_outputs.output.main = image
                            print(f"Pencil+ 4 Line Output Fixed. ({view_layer} / {image})")
    
    @staticmethod
    def correct_image_names():
        for view_layer in itertools.chain.from_iterable(scene.view_layers for scene in bpy.data.scenes):
            view_layer.pencil4_line_outputs.rename_images(view_layer)


def register_props():
    bpy.types.ViewLayer.pencil4_line_outputs = bpy.props.PointerProperty(type=ViewLayerLineOutputs)

def unregister_props():
    del(bpy.types.ViewLayer.pencil4_line_outputs)

def new_image(name:str) -> bpy.types.Image:
    image = bpy.data.images.new(name, width=8, height=8, alpha=True, float_buffer=True)
    image.generated_color = [0, 0, 0, 0]
    setup_image(image, width=image.size[0], height=image.size[1])
    return image


def get_image(view_layer: bpy.types.ViewLayer) -> bpy.types.Image:
    if view_layer is None:
        return None
    if view_layer.pencil4_line_outputs.output.main is not None:
        if view_layer.pencil4_line_outputs.output.main.name != "" and\
        not view_layer.pencil4_line_outputs.output.main in set(bpy.data.images):
            view_layer.pencil4_line_outputs.output.main = None
    if view_layer.pencil4_line_outputs.output.main is None:
        view_layer.pencil4_line_outputs.output.main = new_image(get_image_name(view_layer))
    return view_layer.pencil4_line_outputs.output.main


def new_element_image(view_layer: bpy.types.ViewLayer) -> bpy.types.Image:
    if view_layer is None:
        return None
    new_element:RenderElement = view_layer.pencil4_line_outputs.render_elements.add()
    new_element.output.main = new_image(get_element_image_name_prefix(view_layer))
    return new_element.output.main


def setup_image(image: bpy.types.Image, width: int, height: int):
    if image is None:
        return

    if image.source != "GENERATED":
        image.source = "GENERATED"
    if not image.use_generated_float:
        image.use_generated_float = True
    colorspace = "Linear" if "Linear" in bpy.types.ColorManagedInputColorspaceSettings.bl_rna.properties["name"].enum_items else "Linear Rec.709"
    if image.colorspace_settings.name != colorspace:
        image.colorspace_settings.name = colorspace
    if image.alpha_mode != "PREMUL":
        image.alpha_mode = "PREMUL"
    if image.size[0] != width or image.size[1] != height:
        image.scale(image.size[0] if width <= 0 else width, image.size[1] if height <= 0 else height)


def setup_images(scene: bpy.types.Scene):
    width = scene.render.resolution_x * scene.render.resolution_percentage // 100
    height = scene.render.resolution_y * scene.render.resolution_percentage // 100
    for view_layer in scene.view_layers:
        (image, element_dict) = enumerate_images_from_compositor_nodes(view_layer)
        setup_image(image, width, height)
        for i in element_dict.keys():
            setup_image(i, width, height)


def unpack_images(scene: bpy.types.Scene):
    def unpack_image(image: bpy.types.Image):
        if image is not None:
            image.pack()
            if image.packed_file is not None:
                image.unpack(method='REMOVE')
    for view_layer in scene.view_layers:
        (image, element_dict) = enumerate_images_from_compositor_nodes(view_layer)
        unpack_image(image)
        for i in element_dict.keys():
            unpack_image(i)


def reset_image(image: bpy.types.Image):
    if image is None:
        return

    image.reload()
    if image.source == 'GENERATED':
        image.generated_color = [0, 0, 0, 0]
    else:
        image.pixels = [0] * (image.size[0] * image.size[1] * 4)


def iterate_all_pencil_image_nodes(node_tree: bpy.types.NodeTree) -> Iterable[bpy.types.Node]:
    for node in node_tree.nodes:
        if node.type == "IMAGE" and node.image is not None:
            for view_layer in itertools.chain.from_iterable(scene.view_layers for scene in bpy.data.scenes):
                if (view_layer.pencil4_line_outputs.contains_in_render_elements(node.image) or
                    view_layer.pencil4_line_outputs.output.main == node.image):
                    yield node
                    break
    

def enumerate_images_from_compositor_nodes(view_layer: bpy.types.ViewLayer, check_image_size: Tuple[int, int] = None) -> Tuple[bpy.types.Image, dict[bpy.types.Image, cpp.line_render_element]]:
    main_image = None
    element_dict = {}

    if bpy.context.scene.node_tree is not None:
        for image in [node.image for node in bpy.context.scene.node_tree.nodes if node.type == "IMAGE" and node.image]:
            if check_image_size is not None and (image.size[0] != check_image_size[0] or image.size[1] != check_image_size[1]):
                continue
            if image == view_layer.pencil4_line_outputs.output.main:
                main_image = image
            elif view_layer.pencil4_line_outputs.contains_in_render_elements(image):
                py_element = view_layer.pencil4_line_outputs.get_render_element_from_image(image)
                cpp_element = cpp.line_render_element()
                cpp_ulits.copy_props(py_element, cpp_element)
                cpp_element._image = image
                element_dict[image] = cpp_element

    return (main_image, element_dict)


def enumerate_vector_outputs_from_compositor_nodes(view_layer: bpy.types.ViewLayer, create_folder: bool = False) -> list[cpp.vector_output]:
    if bpy.context.scene.node_tree is not None:
        for image in [node.image for node in bpy.context.scene.node_tree.nodes if node.type == "IMAGE" and node.image]:
            if image == view_layer.pencil4_line_outputs.output.main:
                outputs = []
                for py_output in view_layer.pencil4_line_outputs.vector_outputs:
                    if not py_output.on:
                        continue
                    cpp_output = cpp.vector_output()
                    cpp_ulits.copy_props(py_output, cpp_output)

                    dir = os.path.dirname(cpp_output.output_path)
                    if create_folder:
                        if not os.path.exists(dir):
                            try:
                                os.makedirs(dir)
                            except Exception as e:
                                continue
                    if not os.access(dir, os.W_OK):
                        continue
                    
                    outputs.append(cpp_output)
                return outputs

    return []


def correct_duplicated_output_images(scene: bpy.types.Scene):
    images = set()
    for view_layer in scene.view_layers:
        view_layer.pencil4_line_outputs.correct_duplicated_output_images(images)