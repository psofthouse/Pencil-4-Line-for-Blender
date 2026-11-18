# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import platform
from mathutils import Matrix

if "bpy" in locals():
    import importlib
    importlib.reload(cpp_module_loader)
    pencil4line_for_blender = cpp_module_loader.load_cpp_module(__package__, ".bin")
    importlib.reload(pencil4line_for_blender)
    importlib.reload(pencil4_render_images)
    importlib.reload(pencil4_lens_remap)
    importlib.reload(cpp_utils)
else:
    import bpy
    from .misc import cpp_module_loader
    pencil4line_for_blender = cpp_module_loader.load_cpp_module(__package__, ".bin")
    from . import pencil4_render_images
    from . import pencil4_lens_remap
    from .misc import cpp_utils

from .node_tree import PencilNodeTree
from .node_tree.misc.DataUtils import line_object_types

import bpy
import itertools
import os
import time

import numpy as np

_dll_valid = False
def get_dll_valid():
    return _dll_valid

def show_render_error(message = ""):
    print( f"Pencil+ 4 Line Render Error : {message}")

def get_render_size(depsgraph: bpy.types.Depsgraph) -> tuple[int, int]:
    return get_scene_render_size(depsgraph.scene)

def get_scene_render_size(scene: bpy.types.Scene) -> tuple[int, int]:
    width = scene.render.resolution_x * scene.render.resolution_percentage // 100
    height = scene.render.resolution_y * scene.render.resolution_percentage // 100
    return (width, height)

def is_lens_compositor_scene(scene: bpy.types.Scene) -> bool:
    """シーン内に非線形レンズのカメラがあり、現在のレンダラーで非線形レンズのライン描画が有効かを判定する。マーカーでのカメラ切り替えに備えて全カメラを対象にする。"""
    if not pencil4_lens_remap.is_lens_line_available_for_renderer(scene.render.engine, bpy.app.version):
        return False
    return any(obj.type == "CAMERA" and pencil4_lens_remap.is_supported_camera(obj.data) for obj in scene.objects)

def get_max_compositor_target_count(scene: bpy.types.Scene) -> int:
    """全ビューレイヤーのうち、ライン描画の出力先（メイン画像と要素画像）の最大数を返す。"""
    (width, height) = get_scene_render_size(scene)
    max_count = 0
    for view_layer in scene.view_layers:
        (image, element_dict) = pencil4_render_images.enumerate_images_from_compositor_nodes(view_layer, (width, height), check_node_mute = True)
        max_count = max(max_count, (1 if image is not None else 0) + len(element_dict))
    return max_count

class Pencil4RenderSession:
    def __init__(self):
        pencil4_render_images.ViewLayerLineOutputs.correct_output_images()
        self.__interm_context = pencil4line_for_blender.interm_context()
        # 非線形レンズ用の 6 面分のコンテキスト。面ごとに描画結果のキャッシュを保持するため分けている
        self.__lens_interm_contexts: list[pencil4line_for_blender.interm_context] = []
        self.__lens_face_textures = [None] * 6
        self.__lens_face_texture_size = None
        self.__lens_face_cache_version = None
        self.__lens_face_cache_update = None
        # 通常のビューポート描画用のテクスチャキャッシュ。描画成功時のみ C++ の画像バージョンを確定する
        self.__viewport_texture = None
        self.__viewport_texture_size = None
        self.__viewport_texture_version = None
        self.__viewport_texture_update = None
        # 非線形レンズ用の一時画像。レンダリング開始時に確保し、フレーム間で再利用する
        self.__lens_temp_images: list[bpy.types.Image] = []
        self.__curve_data = dict()
        self.__processed_view_layers = set()

    def prepare_lens_temp_images(self, scene: bpy.types.Scene):
        """レンダリング開始前に、全ビューレイヤーの出力先の最大数を求めて一時画像を確保する。"""
        if self.__lens_temp_images or not is_lens_compositor_scene(scene):
            return
        target_count = get_max_compositor_target_count(scene)
        if target_count == 0:
            return
        width, height = get_scene_render_size(scene)
        face_size = max(width, height)
        self.__lens_temp_images = [bpy.data.images.new(f"pencil4_lens_face_{i}", face_size, face_size, alpha=True, float_buffer=True)
                                   for i in range(target_count)]


    def cleanup_frame(self):
        self.__interm_context.cleanup_frame()
        self.__curve_data.clear()
        self.__processed_view_layers.clear()

    def cleanup_all(self):
        self.cleanup_frame()
        self.clear_texture_caches()

        for lens_context in self.__lens_interm_contexts:
            lens_context.cleanup_all()
        self.__lens_interm_contexts = []

        for temp in self.__lens_temp_images:
            bpy.data.images.remove(temp)
        self.__lens_temp_images = []

        self.__interm_context.cleanup_all()
        self.__interm_context = None

    def prepare_lens_face_texture_cache(self, face_size: int):
        if self.__lens_face_texture_size != face_size:
            self.clear_lens_face_texture_cache()
            self.__lens_face_texture_size = face_size

    def get_lens_face_textures(self):
        return self.__lens_face_textures

    def set_lens_face_texture(self, face_index: int, texture):
        self.__lens_face_textures[face_index] = texture

    def has_lens_face_texture_cache(self, version, face_size: int) -> bool:
        return (version is not None and version == self.__lens_face_cache_version and
                self.__lens_face_texture_size == face_size and
                all(texture is not None for texture in self.__lens_face_textures))

    def invalidate_lens_face_texture_cache(self):
        self.__lens_face_cache_version = None
        self.__lens_face_cache_update = None

    def begin_lens_face_texture_update(self):
        self.invalidate_lens_face_texture_cache()
        self.__lens_face_cache_update = object()
        return self.__lens_face_cache_update

    def finish_lens_face_texture_update(self, token, version):
        if token is None or token is not self.__lens_face_cache_update:
            raise RuntimeError("Lens face texture cache was invalidated during the update.")
        if any(texture is None for texture in self.__lens_face_textures):
            raise RuntimeError("Lens face texture cache is incomplete.")
        if version is not None and (not self.__lens_interm_contexts or
                                    getattr(self.__lens_interm_contexts[0], "viewport_image_version", None) != version):
            raise RuntimeError("Lens face image changed during the texture update.")
        self.__lens_face_cache_version = version
        self.__lens_face_cache_update = None

    def clear_lens_face_texture_cache(self):
        self.__lens_face_textures = [None] * 6
        self.__lens_face_texture_size = None
        self.invalidate_lens_face_texture_cache()

    def get_viewport_texture(self):
        return self.__viewport_texture

    def set_viewport_texture(self, texture, width: int, height: int):
        self.__viewport_texture = texture
        self.__viewport_texture_size = (width, height)

    def has_viewport_texture_cache(self, version, width: int, height: int) -> bool:
        return (version is not None and version == self.__viewport_texture_version and
                self.__viewport_texture_size == (width, height) and
                self.__viewport_texture is not None)

    def invalidate_viewport_texture_cache(self):
        self.__viewport_texture_version = None
        self.__viewport_texture_update = None

    def begin_viewport_texture_update(self):
        self.invalidate_viewport_texture_cache()
        self.__viewport_texture_update = object()
        return self.__viewport_texture_update

    def finish_viewport_texture_update(self, token, version):
        if token is None or token is not self.__viewport_texture_update:
            raise RuntimeError("Viewport texture cache was invalidated during the update.")
        if self.__viewport_texture is None:
            raise RuntimeError("Viewport texture cache is incomplete.")
        if version is not None and getattr(self.__interm_context, "viewport_image_version", None) != version:
            raise RuntimeError("Viewport image changed during the texture update.")
        self.__viewport_texture_version = version
        self.__viewport_texture_update = None

    def clear_viewport_texture_cache(self):
        self.__viewport_texture = None
        self.__viewport_texture_size = None
        self.invalidate_viewport_texture_cache()

    def clear_texture_caches(self):
        self.clear_viewport_texture_cache()
        self.clear_lens_face_texture_cache()


    def draw_line(self, depsgraph: bpy.types.Depsgraph):
        if depsgraph.view_layer.name in self.__processed_view_layers:
            return pencil4line_for_blender.draw_ret.success
        self.__processed_view_layers.add(depsgraph.view_layer.name)
        width, height = get_render_size(depsgraph)

        # コンポジットノードで使用されているPencil+ 4のImageを列挙する
        # Imageが何もなければ処理を抜ける
        (image, element_dict) = pencil4_render_images.enumerate_images_from_compositor_nodes(depsgraph.view_layer, (width, height), check_node_mute = True)
        if image is None and len(element_dict) == 0:
            return pencil4line_for_blender.draw_ret.success

        # 描画
        ret = pencil4line_for_blender.draw_ret.error_unknown
        try:
            target_count = (1 if image is not None else 0) + len(element_dict)
            if self.__is_lens_compositor_target(depsgraph) and len(self.__lens_temp_images) >= target_count:
                ret = self.__draw_line_for_lens(depsgraph, width, height, image, element_dict,
                                                is_cycles = depsgraph.scene.render.engine == "CYCLES",
                                                is_eevee_next = depsgraph.scene.render.engine == "BLENDER_EEVEE_NEXT")
            else:
                if self.__is_lens_compositor_target(depsgraph):
                    # 開始時に一時画像を確保していない場合（レンダリング中にレンズが変わった場合など）は従来のライン描画で処理する
                    print("Pencil+ 4 Line Render Warning : lens temporary images are not prepared. Falling back to linear line rendering.")
                ret = self.__draw_line(depsgraph, width, height, image, element_dict,
                                       is_cycles = depsgraph.scene.render.engine == "CYCLES",
                                       is_eevee_next = depsgraph.scene.render.engine == "BLENDER_EEVEE_NEXT")
        finally:
            if ret != pencil4line_for_blender.draw_ret.success and ret != pencil4line_for_blender.draw_ret.success_without_license:
                pencil4_render_images.reset_image(image)
                for i in element_dict.keys():
                    pencil4_render_images.reset_image(i)

            if ret != pencil4line_for_blender.draw_ret.success:
                show_render_error(ret)

                if bpy.context.preferences.addons[__package__].preferences.abort_rendering_if_error_occur:
                    if platform.system() == "Windows":
                        import ctypes
                        ctypes.windll.user32.keybd_event(0x1B)
                    elif platform.system() == "Darwin":
                        pencil4line_for_blender.simulate_esc_key_press()
                    show_render_error("Rendering aborted.")
                
            return ret


    def __is_lens_compositor_target(self, depsgraph: bpy.types.Depsgraph) -> bool:
        """シーンカメラが非線形レンズで、かつ現在のレンダラーがその経路の対象かを判定する。"""
        camera = depsgraph.scene_eval.camera
        return (camera is not None and camera.type == "CAMERA" and
                pencil4_lens_remap.is_supported_camera(camera.data) and
                pencil4_lens_remap.is_lens_line_available_for_renderer(depsgraph.scene.render.engine, bpy.app.version))

    def __draw_line_for_lens(self, depsgraph: bpy.types.Depsgraph, width: int, height: int,
                             image: bpy.types.Image,
                             element_dict: dict[bpy.types.Image, pencil4line_for_blender.line_render_element],
                             is_cycles: bool, is_eevee_next: bool) -> pencil4line_for_blender.draw_ret:
        """非線形レンズ用に、6 面のライン画像を描画して Python 側で 1 枚の画像へリマップし、出力画像へ書き込む。"""
        # ライン描画設定がない場合は通常経路と同じく何もせず終了する（一時画像を使う前に判定する）
        (line_nodes, _) = PencilNodeTree.generate_cpp_nodes(depsgraph)
        if len(line_nodes) == 0:
            return self.__draw_line(depsgraph, width, height, image, element_dict,
                                    is_cycles = is_cycles, is_eevee_next = is_eevee_next)

        scene_camera = depsgraph.scene_eval.camera
        camera_data = scene_camera.data
        face_size = max(width, height)
        base_matrix = get_camera_matrix(scene_camera)
        projection = pencil4_lens_remap.get_face_projection(camera_data.clip_start, camera_data.clip_end)
        if not self.__lens_interm_contexts:
            self.__lens_interm_contexts = [pencil4line_for_blender.interm_context() for _ in range(6)]

        # 出力先（メイン画像と要素画像）ごとに一時画像を 1 枚ずつ作り、面間で再利用する
        targets = [(image, None)] if image is not None else []
        targets += [(orig, element) for orig, element in element_dict.items()]

        ret = pencil4line_for_blender.draw_ret.success
        outputs = []
        # 一時画像はレンダリング開始時に確保済み（prepare_lens_temp_images）。ここでは生成・削除を行わない
        temp_images = self.__lens_temp_images[:len(targets)]
        try:
            # 中間 (outputs) は出力画像のサイズ分のみ保持する（面ごとのバッファは持たない）
            lut = pencil4_lens_remap.get_lens_lut(camera_data, width, height, face_size)
            outputs = [pencil4_lens_remap.remap_begin(lut) for _ in targets]

            for face_index in range(6):
                face_matrix = base_matrix @ pencil4_lens_remap.get_face_rotation(face_index)
                face_context = self.__lens_interm_contexts[face_index]
                face_context.draw_options = self.__interm_context.draw_options

                # 要素の出力先を一時画像へ差し替えてから面を描画する
                face_element_dict = {}
                face_main = None
                for target_index, (orig, element) in enumerate(targets):
                    temp = temp_images[target_index]
                    if element is None:
                        face_main = temp
                    else:
                        element._image = temp
                        face_element_dict[temp] = element

                face_ret = self.__draw_line(depsgraph, face_size, face_size, face_main, face_element_dict,
                                            is_cycles = is_cycles, is_eevee_next = is_eevee_next,
                                            interm_context = face_context,
                                            lens_face_camera = (face_matrix, projection, camera_data.clip_start, camera_data.clip_end))
                if face_ret != pencil4line_for_blender.draw_ret.success and face_ret != pencil4line_for_blender.draw_ret.success_without_license:
                    return face_ret
                if face_ret == pencil4line_for_blender.draw_ret.success_without_license:
                    ret = face_ret

                # 読み出した面は即座に出力へ加算し、面のバッファは次の面で解放される
                for target_index, temp in enumerate(temp_images):
                    face_pixels = read_image_pixels(temp, face_size)
                    pencil4_lens_remap.remap_accumulate_face(outputs[target_index], face_pixels, lut, face_index)
                face_context.cleanup_frame()

            for (orig, _), out in zip(targets, outputs):
                orig.pixels.foreach_set(pencil4_lens_remap.remap_finish(out, lut))
                orig.update()
        finally:
            for (orig, element) in targets:
                if element is not None:
                    element._image = orig
        return ret

    def draw_line_for_viewport(self, depsgraph: bpy.types.Depsgraph, width: int, height: int, space: bpy.types.SpaceView3D, region_3d: bpy.types.RegionView3D,
                               matrix_override = None, interm_context: pencil4line_for_blender.interm_context = None):
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
        camera_matrix = region_3d.view_matrix.inverted(False)
        if camera_matrix is False:
            return pencil4line_for_blender.draw_ret.error_unknown
        window_matrix = region_3d.window_matrix
        if matrix_override is not None:
            camera_matrix, window_matrix = matrix_override(camera_matrix, window_matrix)
        interm_camera = pencil4line_for_blender.interm_camera(clip_start,
                            clip_end,
                            get_line_size_relative_type(depsgraph) if draw_option is not None and draw_option.linesize_relative_target_width > 0 else 0,
                            camera_matrix,
                            window_matrix)
        return self.__draw_line(depsgraph, width, height, None, dict(),
                                viewport_camera = interm_camera,
                                space = space,
                                is_cycles = depsgraph.scene.render.engine == "CYCLES" and space.shading.type == "RENDERED",
                                is_eevee_next = (depsgraph.scene.render.engine == "BLENDER_EEVEE_NEXT" and (space.shading.type == "RENDERED" or space.shading.type == "MATERIAL")) or
                                                (depsgraph.scene.render.engine == "CYCLES" and space.shading.type == "MATERIAL" and "BLENDER_EEVEE_NEXT" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()),
                                interm_context = interm_context)


    def draw_line_for_viewport_lens(self, depsgraph: bpy.types.Depsgraph, width: int, height: int, space: bpy.types.SpaceView3D,
                                    region_3d: bpy.types.RegionView3D, camera: bpy.types.Object):
        """非線形レンズ用に6面を描画し、再利用できる場合は先頭面の判定だけを行う。

        戻り値は (draw_ret, (面バッファまたは None, LUT, 面サイズ, 先頭版, 更新トークン) or None)。
        """
        lens_data = None
        # タイムアウトは6面全体の処理時間とするため、面ごとに残り時間を設定し、終了後に元の値へ戻す
        draw_options = self.__interm_context.draw_options
        total_timeout = draw_options.timeout if draw_options is not None else 0
        start_time = time.perf_counter()
        try:
            face_size = max(width, height)
            self.prepare_lens_face_texture_cache(face_size)
            base_matrix = get_camera_matrix(camera)
            camera_data = camera.data
            projection = pencil4_lens_remap.get_face_projection(camera_data.clip_start, camera_data.clip_end)
            if not self.__lens_interm_contexts:
                self.__lens_interm_contexts = [pencil4line_for_blender.interm_context() for _ in range(6)]
            face_buffers = []
            first_version = None
            update_token = None
            draw_ret = pencil4line_for_blender.draw_ret.success
            for face_index in range(6):
                face_matrix = base_matrix @ pencil4_lens_remap.get_face_rotation(face_index)

                def matrix_override(camera_matrix, window_matrix, face_matrix=face_matrix):
                    return face_matrix, projection

                # 面ごとに別のコンテキストを使い、各面の描画パラメータのキャッシュを独立させる
                face_context = self.__lens_interm_contexts[face_index]
                face_context.draw_options = draw_options
                if total_timeout > 0:
                    remaining = total_timeout - (time.perf_counter() - start_time)
                    # C++ 側は 0 以下を無制限として扱うため、残り時間がなければここで打ち切る
                    if remaining <= 0:
                        return pencil4line_for_blender.draw_ret.timeout, None
                    draw_options.timeout = remaining
                draw_ret = self.draw_line_for_viewport(depsgraph, face_size, face_size, space, region_3d, matrix_override,
                                                       interm_context = face_context)
                self.cleanup_frame()
                face_context.cleanup_frame()
                if draw_ret != pencil4line_for_blender.draw_ret.success and draw_ret != pencil4line_for_blender.draw_ret.success_without_license:
                    return draw_ret, None
                if face_index == 0:
                    first_version = getattr(face_context, "viewport_image_version", None)
                    if self.has_lens_face_texture_cache(first_version, face_size):
                        lut = pencil4_lens_remap.get_lens_lut(camera_data, width, height, face_size)
                        lens_data = (None, lut, face_size, first_version, None)
                        return draw_ret, lens_data
                    update_token = self.begin_lens_face_texture_update()

                face_buffer = np.asarray(face_context.get_viewport_image_buffer(), dtype=np.float32)
                if face_buffer.size == 0:
                    # ライン描画設定がない場合は空のバッファが返るため、描画なしとして扱う
                    return draw_ret, None
                if face_buffer.size != face_size * face_size * 4:
                    return pencil4line_for_blender.draw_ret.error_unknown, None
                face_buffers.append(face_buffer)

            lut = pencil4_lens_remap.get_lens_lut(camera_data, width, height, face_size)
            lens_data = (face_buffers, lut, face_size, first_version, update_token)
            return draw_ret, lens_data
        finally:
            if total_timeout > 0:
                draw_options.timeout = total_timeout
            if lens_data is None:
                self.invalidate_lens_face_texture_cache()



    def get_viewport_image_buffer(self):
            return self.__interm_context.get_viewport_image_buffer()

    def get_viewport_line_data(self, width: int, height: int):
        """直前に成功した通常のビューポート描画の結果を返す。

        戻り値は (画像バッファまたは None, 版, 更新トークン) or None。
        版が確定済みのテクスチャと一致する場合は画像バッファのコピーを省略して None を返す。
        """
        viewport_data = None
        try:
            version = getattr(self.__interm_context, "viewport_image_version", None)
            if self.has_viewport_texture_cache(version, width, height):
                viewport_data = (None, version, None)
                return viewport_data
            update_token = self.begin_viewport_texture_update()
            pixels = self.get_viewport_image_buffer()
            if len(pixels) != width * height * 4:
                return None
            viewport_data = (pixels, version, update_token)
            return viewport_data
        finally:
            if viewport_data is None:
                self.invalidate_viewport_texture_cache()


    def __draw_line(self,
                    depsgraph: bpy.types.Depsgraph,
                    width: int,
                    height: int,
                    image: bpy.types.Image,
                    element_dict: dict[bpy.types.Image, pencil4line_for_blender.line_render_element],
                    viewport_camera: pencil4line_for_blender.interm_camera = None,
                    space: bpy.types.SpaceView3D = None,
                    is_cycles: bool = False,
                    is_eevee_next: bool = False,
                    interm_context: pencil4line_for_blender.interm_context = None,
                    lens_face_camera: tuple = None) -> pencil4line_for_blender.draw_ret:
        if interm_context is None:
            interm_context = self.__interm_context
        # ライン描画設定が何もなければライン描画せず終了
        (line_nodes, line_function_nodes) = PencilNodeTree.generate_cpp_nodes(depsgraph)
        if len(line_nodes) == 0:
            pencil4_render_images.reset_image(image)
            for i in element_dict.keys():
                pencil4_render_images.reset_image(i)
            self.invalidate_viewport_texture_cache()
            self.invalidate_lens_face_texture_cache()
            interm_context.clear_viewport_image_buffer()
            return pencil4line_for_blender.draw_ret.success
        
        # DLLが有効でなければライン描画せず終了
        if not _dll_valid:
            print("Pencil+ 4 Line Render Error : DLL is not valid.")
            return pencil4line_for_blender.draw_ret.error_unknown

        # 
        is_viewport = viewport_camera is not None
        material_override = depsgraph.view_layer_eval.material_override if depsgraph.scene.render.engine == "CYCLES" else None

        # Holdout設定
        holdout_objects_from_collection = set()
        check_holdout = depsgraph.scene.render.engine != "BLENDER_WORKBENCH"
        if is_viewport and space and space.shading.type in ["WIREFRAME", "SOLID"]:
            check_holdout = False
        if check_holdout:
            for object in itertools.chain.from_iterable([c.collection.objects for c in flatten_hierarchy(depsgraph.view_layer_eval.layer_collection) if c.holdout]):
                holdout_objects_from_collection.add(object)

        # 描画用オブジェクトのインスタンスの生成
        render_instances = []
        ungrouped_objects = set()
        mesh_color_attributes = {}
        object_to_mesh_dict = {}

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
            if (is_cycles or is_eevee_next) and not obj.visible_camera:
                continue
            if is_viewport:
                if object_instance.parent is not None:
                    if not object_instance.parent.visible_get(view_layer=depsgraph.view_layer_eval, viewport=space):
                        continue
                elif not obj.visible_get(view_layer=depsgraph.view_layer_eval, viewport=space):
                    continue
            src_object = obj.original

            # オブジェクトのメッシュを取得
            mesh: bpy.types.Mesh = None
            if obj.type == "MESH":
                mesh = obj.data
                if mesh.is_editmode:
                    mesh = obj.to_mesh()
            elif obj.type in line_object_types:
                if src_object in system_tessellated_objects:
                    continue
                if obj in object_to_mesh_dict:
                    mesh = object_to_mesh_dict[obj]
                else:
                    mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
                    if mesh is None:
                        continue
                    object_to_mesh_dict[obj] = mesh
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

                if check_holdout:
                    holdout = obj.is_holdout
                    if not holdout:
                        holdout = (object_instance.parent if object_instance.parent is not None else obj) in holdout_objects_from_collection
                else:
                    holdout = False

                object_materials = ()
                if material_override is None and any([ms.link == "OBJECT" for ms in obj.material_slots]):
                    object_materials = tuple([ms.material for ms in obj.material_slots])
                
                render_Instance = pencil4line_for_blender.interm_render_Instance(src_object, object_instance.matrix_world, mesh, holdout, object_materials)
                render_instances.append(render_Instance)

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
        elif lens_face_camera is not None:
            face_matrix, face_projection, face_clip_start, face_clip_end = lens_face_camera
            interm_camera = pencil4line_for_blender.interm_camera(face_clip_start,
                                face_clip_end,
                                get_line_size_relative_type(depsgraph),
                                face_matrix,
                                face_projection)
        else:
            scene_camera = depsgraph.scene_eval.camera
            projection = scene_camera.calc_matrix_camera(depsgraph,
                                scale_x= depsgraph.scene.render.pixel_aspect_x,
                                scale_y= depsgraph.scene.render.pixel_aspect_y)
            interm_camera = pencil4line_for_blender.interm_camera(scene_camera.data.clip_start,
                                scene_camera.data.clip_end,
                                get_line_size_relative_type(depsgraph),
                                get_camera_matrix(scene_camera),
                                projection)

        # グループ設定
        groups = []
        def collect_group(collection: bpy.types.Collection):
            if collection is None:
                return
            for child in collection.children:
                collect_group(child)
            for object in collection.objects:
                if object.type == "EMPTY" and object.instance_type == "COLLECTION":
                    collect_group(object.instance_collection)
            if collection.pcl4_line_merge_group:
                objects = set()
                for x in collection.all_objects:
                    x = x if x.override_library is None else x.override_library.reference
                    if x in ungrouped_objects:
                        objects.add(x)
                if len(objects) > 0:
                    groups.append(list(objects))
                    ungrouped_objects.difference_update(objects)
        collect_group(depsgraph.scene.collection)

        # 描画
        pencil4line_for_blender.set_blender_version(bpy.app.version[0], bpy.app.version[1], bpy.app.version[2])
        pencil4line_for_blender.set_render_app_path(bpy.context.preferences.addons[__package__].preferences.render_app_path)

        if mesh_color_attributes is None:
            interm_context.mesh_color_attributes_on = False
        else:
            interm_context.mesh_color_attributes_on = True
            interm_context.mesh_color_attributes = [(mesh, attr) for mesh, attr in mesh_color_attributes.items() if len(attr) > 0]

        interm_context.platform = f"Blender {bpy.app.version_string}"

        task_name = interm_context.platform
        task_name += f" : {bpy.path.basename(bpy.data.filepath)}"
        if is_viewport:
            task_name += f" : viewport"
            interm_context.task_name = task_name
            return interm_context.draw_for_viewport(width, height,
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
            interm_context.task_name = task_name
            return interm_context.draw(image,
                                        interm_camera,
                                        render_instances,
                                        material_override,
                                        list(self.__curve_data.items()),
                                        line_nodes,
                                        line_function_nodes,
                                        list(element_dict.values()),
                                        # 面ごとの描画はベクター出力の対象外（非線形レンズの投影と一致しないため）
                                        [] if lens_face_camera is not None else pencil4_render_images.enumerate_vector_outputs_from_compositor_nodes(depsgraph.view_layer, True),
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


def read_image_pixels(image: bpy.types.Image, size: int) -> np.ndarray:
    buffer = np.empty(size * size * 4, dtype=np.float32)
    image.pixels.foreach_get(buffer)
    return buffer.reshape(size, size, 4)


def get_camera_matrix(camera: bpy.types.Object) -> Matrix:
    camera_matrix = camera.matrix_world.transposed()
    camera_matrix[0].xyz = camera_matrix[0].xyz.normalized()
    camera_matrix[1].xyz = camera_matrix[1].xyz.normalized()
    camera_matrix[2].xyz = camera_matrix[2].xyz.normalized()
    camera_matrix.transpose()
    return camera_matrix
    

def flatten_hierarchy(o):
    yield o
    for child in o.children:
        yield from flatten_hierarchy(child)


def create_previews(preview_size: int,
                    stroke_preview_width: int,
                    brush_detail_node,
                    stroke_preview_brush_size: float,
                    stroke_preview_scale: float,
                    color: tuple[float, float, float, float],
                    bg_color: tuple[float, float, float, float],
                    hash_prev):
    error_ret = (None, None, None)
    # DLLが有効でなければ描画せず終了
    if not _dll_valid:
        return error_ret
    
    if brush_detail_node is None:
        return error_ret
    node_dict = {brush_detail_node: pencil4line_for_blender.brush_detail_node()}
    if brush_detail_node.filtered_socket_id("brush_map", context=bpy.context) != "":
        brush_map_node = brush_detail_node.find_connected_from_node("brush_map")
        if brush_map_node is not None:
            node_dict[brush_map_node] = pencil4line_for_blender.texture_map_node()
        
    for py_node, cpp_node in node_dict.items():
        cpp_utils.copy_props(py_node, cpp_node, node_dict, context=bpy.context)

    pencil4line_for_blender.set_blender_version(bpy.app.version[0], bpy.app.version[1], bpy.app.version[2])
    pencil4line_for_blender.set_render_app_path(bpy.context.preferences.addons[__package__].preferences.render_app_path)
    return pencil4line_for_blender.create_previews(preview_size, stroke_preview_width,
                                                   node_dict[brush_detail_node],
                                                   stroke_preview_brush_size, stroke_preview_scale,
                                                   color, bg_color, hash_prev)


def register():
    global _dll_valid
    _dll_valid = False
    if hasattr(pencil4line_for_blender, "get_commit_hash"):
        with open(os.path.join(os.path.dirname(os.path.abspath(pencil4line_for_blender.__file__)), "commitHash.txt"), 'r', encoding='utf-8') as file:
            if file.read().strip() == pencil4line_for_blender.get_commit_hash():
                _dll_valid = True
