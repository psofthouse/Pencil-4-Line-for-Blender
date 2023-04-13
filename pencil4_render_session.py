# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import sys
import platform

if "bpy" in locals():
    import imp
    imp.reload(pencil4line_for_blender)
    imp.reload(pencil4_render_images)
else:
    if platform.system() == "Windows":
        if sys.version_info.major == 3 and sys.version_info.minor == 9:
            from .bin import pencil4line_for_blender_win64_39 as pencil4line_for_blender
        elif sys.version_info.major == 3 and sys.version_info.minor == 10:
            from .bin import pencil4line_for_blender_win64_310 as pencil4line_for_blender
    elif platform.system() == "Darwin":
        if sys.version_info.major == 3 and sys.version_info.minor == 9:
            from .bin import pencil4line_for_blender_mac_39 as pencil4line_for_blender
        elif sys.version_info.major == 3 and sys.version_info.minor == 10:
            from .bin import pencil4line_for_blender_mac_310 as pencil4line_for_blender
    from . import pencil4_render_images

from .node_tree import PencilNodeTree
from .node_tree.misc.DataUtils import line_object_types

import bpy
import itertools

def ShowErrorMessage(message = ""):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = "Pencil+ 4 Line Render Error", icon = "ERROR")
    print(f"Pencil+ 4 Line Render Error : {message}")

class Pencil4RenderSession:
    def __init__(self):
        pencil4_render_images.ViewLayerLineOutputs.correct_image_names()
        self.__interm_context = pencil4line_for_blender.interm_context()
        self.__converted_objects = dict()
        self.__curve_data = dict()
        self.__processed_view_layers = set()


    def cleanup_frame(self):
        self.__interm_context.cleanup_frame()

        for obj in self.__converted_objects.keys():
            obj.to_mesh_clear()
        self.__converted_objects.clear()
        self.__curve_data.clear()
        self.__processed_view_layers.clear()

    def cleanup_all(self):
        self.cleanup_frame()

        self.__interm_context.cleanup_all()
        self.__interm_context = None


    def draw_line(self, depsgraph: bpy.types.Depsgraph):
        if depsgraph.view_layer.name in self.__processed_view_layers:
            return pencil4line_for_blender.draw_ret.success
        self.__processed_view_layers.add(depsgraph.view_layer.name)

        # コンポジットノードで使用されているPencil+ 4のImageを列挙する
        # Imageが何もなければ処理を抜ける
        (image, element_dict) = pencil4_render_images.enumerate_images_from_compositor_nodes(depsgraph.view_layer)
        if image is None and len(element_dict) == 0:
            return pencil4line_for_blender.draw_ret.success

        # 描画
        ret = pencil4line_for_blender.draw_ret.error_unknown
        try:
            width = depsgraph.scene.render.resolution_x * depsgraph.scene.render.resolution_percentage // 100
            height = depsgraph.scene.render.resolution_y * depsgraph.scene.render.resolution_percentage // 100
            ret = self.__draw_line(depsgraph, width, height, image, element_dict, is_cycles = depsgraph.scene.render.engine == "CYCLES")
        finally:
            if ret != pencil4line_for_blender.draw_ret.success and ret != pencil4line_for_blender.draw_ret.success_without_license:
                pencil4_render_images.reset_image(image)
                for i in element_dict.keys():
                    pencil4_render_images.reset_image(i)

            if ret != pencil4line_for_blender.draw_ret.success:
                bpy.app.timers.register(lambda: ShowErrorMessage(f"{ret}"), first_interval=0)

                if bpy.context.preferences.addons[__package__].preferences.abort_rendering_if_error_occur:
                    import ctypes
                    ctypes.windll.user32.keybd_event(0x1B)
                    bpy.app.timers.register(lambda: ShowErrorMessage("Rendering aborted."), first_interval=0)
                
            return ret


    def draw_line_for_viewport(self, depsgraph: bpy.types.Depsgraph, region: bpy.types.Region, space: bpy.types.SpaceView3D, region_3d: bpy.types.RegionView3D):
        if region_3d.view_perspective == "CAMERA" and space.camera is not None and space.camera.type == "CAMERA":
            camera: bpy.types.Camera = space.camera.data
            clip_start = camera.clip_start
            clip_end = camera.clip_end
        elif region_3d.is_perspective:
            clip_start = space.clip_start
            clip_end = space.clip_end
        else:
            clip_start = -3e38
            clip_end = 3e38
        draw_option = self.get_draw_option(new_if_none = False)
        interm_camera = pencil4line_for_blender.interm_camera(clip_start,
                            clip_end,
                            get_line_size_relative_type(depsgraph) if draw_option is not None and draw_option.linesize_relative_target_width > 0 else 0,
                            region_3d.view_matrix.inverted(),
                            region_3d.window_matrix)
        return self.__draw_line(depsgraph, region.width, region.height, None, {},
            viewport_camera = interm_camera,
            space = space,
            is_cycles = space.shading.type == "RENDERED" and depsgraph.scene.render.engine == "CYCLES")


    def get_viewport_image_buffer(self):
            return self.__interm_context.get_viewport_image_buffer()


    def __draw_line(self,
                    depsgraph: bpy.types.Depsgraph,
                    width: int,
                    height: int,
                    image: bpy.types.Image,
                    element_dict: dict[bpy.types.Image, pencil4line_for_blender.line_render_element],
                    viewport_camera: pencil4line_for_blender.interm_camera = None,
                    space: bpy.types.SpaceView3D = None,
                    is_cycles: bool = False):
        # ライン描画設定が何もなければライン描画せず終了
        (line_nodes, line_function_nodes) = PencilNodeTree.generate_cpp_nodes()
        if len(line_nodes) == 0:
            pencil4_render_images.reset_image(image)
            for i in element_dict.keys():
                pencil4_render_images.reset_image(i)
            self.__interm_context.clear_viewport_image_buffer()
            return pencil4line_for_blender.draw_ret.success

        # 
        is_viewport = viewport_camera is not None

        # 描画用オブジェクトのインスタンスの生成
        holdout_objects = set()
        render_instances = []
        ungrouped_objects = set()
        mesh_color_attributes = {}

        system_tessellated_objects = set()
        object_instance: bpy.types.DepsgraphObjectInstance
        for object_instance in depsgraph.object_instances:
            obj = object_instance.object
            src_object = obj.original
            if obj.type == "MESH" and src_object.type != "MESH":
                system_tessellated_objects.add(src_object)

        for object_instance in depsgraph.object_instances:
            if not object_instance.show_self:
                continue

            obj = object_instance.object
            if is_cycles and not obj.visible_camera:
                continue
            if is_viewport:
                if object_instance.parent is not None:
                    if not object_instance.parent.visible_get(view_layer=depsgraph.view_layer_eval, viewport=space):
                        continue
                elif not obj.visible_get(view_layer=depsgraph.view_layer_eval, viewport=space):
                    continue
            src_object = obj.original

            # オブジェクトのメッシュを取得
            mesh: bpy.types.Mesh = self.__converted_objects.get(src_object)
            if mesh is None:
                if obj.type == "MESH":
                    mesh = obj.data
                    if mesh.is_editmode:
                        mesh = obj.to_mesh()
                        self.__converted_objects[src_object] = mesh
                elif obj.type in line_object_types:
                    if src_object in system_tessellated_objects:
                        continue
                    mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
                    if mesh is None:
                        continue
                    self.__converted_objects[src_object] = mesh

                    if obj.type == "CURVE" and len(mesh.polygons) == 0:
                        # カーブをメッシュに変換したとき、押し出し量が0の場合だとエッジのみが生成されポリゴンは生成されない
                        # このとき、もともとのカーブに付随していたマテリアルの情報は失われてしまう
                        # ライン描画にはマテリアルの情報が必要になる場合もあるので、欠損した情報を付加する必要がある
                        curve: bpy.types.Curve = obj.data
                        self.__curve_data[mesh] = pencil4line_for_blender.interm_curve_data(curve.materials, [x.material_index for x in curve.splines])
            
            if mesh is not None:
                override_library = src_object.override_library
                src_object = override_library.reference if override_library is not None else src_object

                ungrouped_objects.add(src_object)
                render_Instance = pencil4line_for_blender.interm_render_Instance(src_object, object_instance.matrix_world, mesh)

                render_instances.append(render_Instance)

                if obj.is_holdout:
                    holdout_objects.add(src_object)

                if mesh_color_attributes is not None and mesh not in mesh_color_attributes:
                    attr = getattr(mesh, "color_attributes", None)
                    if attr is None:
                        mesh_color_attributes = None
                    else:
                        mesh_color_attributes[mesh] = list(attr)

        # 描画用カメラ情報の生成
        interm_camera = None
        if viewport_camera is not None:
            interm_camera = viewport_camera
        else:
            scene_camera = depsgraph.scene_eval.camera
            projection = scene_camera.calc_matrix_camera(depsgraph,
                                scale_x= depsgraph.scene.render.pixel_aspect_x,
                                scale_y= depsgraph.scene.render.pixel_aspect_y)
            interm_camera = pencil4line_for_blender.interm_camera(scene_camera.data.clip_start,
                                scene_camera.data.clip_end,
                                get_line_size_relative_type(depsgraph),
                                scene_camera.matrix_world,
                                projection)

        # 出力Imageのセットアップ
        pencil4_render_images.setup_image(image, width, height)
        for i in element_dict.keys():
            pencil4_render_images.setup_image(i, width, height)

        # Holdout設定
        if depsgraph.scene.render.engine != "BLENDER_WORKBENCH":
            for object in itertools.chain.from_iterable([c.collection.objects for c in flatten_hierarchy(depsgraph.view_layer.layer_collection) if c.holdout]):
                holdout_objects.add(object)
            
            # Holdout対象のオブジェクトがある場合、何も描画を行わないダミーのラインセットを生成しオブジェクトを登録する
            if len(holdout_objects) > 0:
                line_set = pencil4line_for_blender.line_set_node()
                line_set.objects = list(holdout_objects)

                for line_node in line_nodes:
                    line_sets = line_node.line_sets
                    line_sets.insert(0, line_set)
                    line_node.line_sets = line_sets
        
        # グループ設定
        groups = []
        def collect_group(collection: bpy.types.Collection):
            for child in collection.children:
                collect_group(child)
            if collection.pcl4_line_merge_group:
                objects = list(x for x in collection.all_objects if x in ungrouped_objects)
                if len(objects) > 0:
                    groups.append(objects)
                    ungrouped_objects.difference_update(objects)
        collect_group(depsgraph.scene.collection)

        # 描画
        pencil4line_for_blender.set_blender_version(bpy.app.version[0], bpy.app.version[1], bpy.app.version[2])

        material_override = depsgraph.view_layer_eval.material_override if depsgraph.scene.render.engine == "CYCLES" else None
        self.__interm_context.render_app_path = bpy.context.preferences.addons[__package__].preferences.render_app_path

        if mesh_color_attributes is None:
            self.__interm_context.mesh_color_attributes_on = False
        else:
            self.__interm_context.mesh_color_attributes_on = True
            self.__interm_context.mesh_color_attributes = [(mesh, attr) for mesh, attr in mesh_color_attributes.items() if len(attr) > 0]

        task_name = f"Blender {bpy.app.version_string}"
        task_name += f" : {bpy.path.basename(bpy.data.filepath)}"
        if is_viewport:
            task_name += f" : viewport"
            self.__interm_context.task_name = task_name
            return self.__interm_context.draw_for_viewport(width, height,
                                        interm_camera,
                                        render_instances,
                                        material_override,
                                        list(self.__curve_data.items()),
                                        line_nodes,
                                        line_function_nodes,
                                        groups)
        else:
            task_name += f" : {depsgraph.view_layer.name}"
            task_name += f" : frame {depsgraph.scene.frame_current}"
            self.__interm_context.task_name = task_name
            return self.__interm_context.draw(image,
                                        interm_camera,
                                        render_instances,
                                        material_override,
                                        list(self.__curve_data.items()),
                                        line_nodes,
                                        line_function_nodes,
                                        list(element_dict.values()),
                                        groups)
    
    def get_draw_option(self, new_if_none:bool = False):
        if new_if_none and self.__interm_context.draw_options is None:
            self.__interm_context.draw_options = pencil4line_for_blender.draw_options()
        return self.__interm_context.draw_options

    def clear_draw_option(self):
        self.__interm_context.draw_options = None


def get_line_size_relative_type(depsgraph: bpy.types.Depsgraph) -> int:
    camera = depsgraph.scene_eval.camera
    return ["AUTO", "HORIZONTAL", "VERTICAL"].index(camera.data.sensor_fit) if camera is not None else 0


def flatten_hierarchy(o):
    yield o
    for child in o.children:
        yield from flatten_hierarchy(child)