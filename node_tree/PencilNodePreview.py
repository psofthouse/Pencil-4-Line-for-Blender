# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import time
from typing import Iterable
from typing import Tuple
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix
from mathutils import Vector
from ..misc import gpu_utils
from ..i18n import Translation
from .PencilNodeTree import PencilNodeTree
from .nodes.BrushSettingsNode import BrushSettingsNode
from .nodes.BrushDetailNode import BrushDetailNode
from .misc.AttrOverride import get_overrided_attr
from .. import pencil4_render_session


class PreviewCache:
    def __init__(self):
        self.hash = None
        self.brush_preview_texture = None
        self.stroke_preview_texture = None
        self.preview_size = 0
        self.stroke_preview_width = 0
        self.node_location = None
        self.node_dimensions = None
        self.node_name = None
        self.registered_timer_func = None
        self.prev_update_time = time.time() - 100
        self.draw_origin = None
    
    def __del__(self):
        self.__delete_textures()
        if self.registered_timer_func is not None:
            bpy.app.timers.unregister(self.registered_timer_func)
            self.registered_timer_func = None
    
    def __delete_textures(self):
        del self.brush_preview_texture
        del self.stroke_preview_texture
        self.brush_preview_texture = None
        self.stroke_preview_texture = None
        self.hash = None
    
    def _update(self, preview_size: int, stroke_preview_width: int, brush_detail_node, stroke_preview_brush_size, stroke_preview_scale):
        self.prev_update_time = time.time()
        if self.registered_timer_func is not None:
            bpy.app.timers.unregister(self.registered_timer_func)
            self.registered_timer_func = None
        hash_obj, brush_pixels, stroke_pixels = pencil4_render_session.create_previews(
            preview_size, stroke_preview_width, brush_detail_node,
            stroke_preview_brush_size, stroke_preview_scale,
            (0, 0, 0, 1), (1, 1, 1, 1), self.hash)
        if brush_detail_node is not None:
            self.node_location = Vector(brush_detail_node.location)
            self.node_dimensions = Vector(brush_detail_node.dimensions)
            self.node_name = brush_detail_node.name
        if self.hash == hash_obj:
            return
        self.__delete_textures()
        self.preview_size = preview_size
        self.stroke_preview_width = stroke_preview_width
        self.hash = hash_obj
        if self.hash is not None:
            pixels = gpu.types.Buffer("FLOAT", preview_size * preview_size * 4, brush_pixels)
            self.brush_preview_texture = gpu.types.GPUTexture((preview_size, preview_size), data=pixels)
            pixels = gpu.types.Buffer("FLOAT", stroke_preview_width * preview_size * 4, stroke_pixels)
            self.stroke_preview_texture = gpu.types.GPUTexture((stroke_preview_width, preview_size), data=pixels)

class PreviewManager:
    __preview_caches = {}

    @staticmethod
    def __get_cahce(node_tree: PencilNodeTree) -> Tuple[BrushDetailNode, float]:
        tree_name = node_tree.name_full
        cache = __class__.__preview_caches.get(tree_name)
        if cache is None:
            cache = PreviewCache()
            __class__.__preview_caches[tree_name] = cache
        return cache
    
    @staticmethod
    def __cleanup_unused_caches():
        node_tree_names = set(x.name_full for x in bpy.data.node_groups if isinstance(x, PencilNodeTree))
        for name, _ in list(__class__.__preview_caches.items()):
            if name not in node_tree_names:
                del __class__.__preview_caches[name]

    @staticmethod
    def __get_preview_target_node(node_tree: PencilNodeTree) -> Tuple[BrushDetailNode, float]:
        nodes = node_tree.get_node_hierarchy_in_panel()
        brush_detail = next((n for n in nodes if isinstance(n, BrushDetailNode)), None)
        brush_settings = next((n for n in nodes if isinstance(n, BrushSettingsNode)), None)
        if brush_settings is not None and brush_detail is None:
            if brush_settings.find_connected_from_node("brush_detail") is not None:
                brush_detail = brush_settings.find_connected_from_node("brush_detail")
        elif brush_detail is not None and brush_settings is None:
            if len(brush_detail.find_connected_to_nodes()) > 0:
                brush_settings = brush_detail.find_connected_to_nodes()[0]
        return (brush_detail, get_overrided_attr(brush_settings, "size", context=bpy.context) if brush_settings is not None else 1.0)

    @staticmethod
    def __delay_validate_cache(node_tree_ptr: int, node_tree_name_full: str) -> None:
        node_tree = next((x for x in bpy.data.node_groups if x.as_pointer() == node_tree_ptr and x.name_full == node_tree_name_full), None)
        if node_tree is not None:
            cache = __class__.__get_cahce(node_tree)
            if cache.registered_timer_func is not None:
                bpy.app.timers.unregister(cache.registered_timer_func)
                cache.registered_timer_func = None
            __class__.validate_cache(node_tree, bpy.context)

    @staticmethod
    def validate_cache(node_tree: PencilNodeTree, context: bpy.types.Context) -> None:
        if node_tree is None:
            return
        cache = __class__.__get_cahce(node_tree)
        if cache.registered_timer_func is not None:
            return
        if time.time() < cache.prev_update_time + 0.1:
            node_tree_ptr = node_tree.as_pointer()
            node_tree_name_full = node_tree.name_full
            cache.registered_timer_func = lambda: __class__.__delay_validate_cache(node_tree_ptr, node_tree_name_full)
            bpy.app.timers.register(cache.registered_timer_func, first_interval=0.1)
            return
        preview_size = 64
        stroke_preview_width = 192
        brush_detail, brush_size = __class__.__get_preview_target_node(node_tree)
        scale = 1.0
        if brush_size < 1.0:
            brush_size = 1.0
        elif brush_size > 20.0:
            scale *= 20.0 / brush_size
        if PreviewManager.__update_cache(node_tree, preview_size, stroke_preview_width, brush_detail, brush_size, scale):
            for screen in bpy.data.screens:
                for area in screen.areas:
                    if area != context.area and area.type == "NODE_EDITOR" and area.spaces.active.edit_tree == node_tree:
                        area.tag_redraw()
        # プレビューのタイマーがひとつもない場合は、使われていないキャッシュを削除する
        if all(cache.registered_timer_func is None for cache in __class__.__preview_caches.values()):
            __class__.__cleanup_unused_caches()

    @staticmethod
    def __update_cache(node_tree: PencilNodeTree, preview_size: int, stroke_preview_width: int, brush_detail_node, brush_size: float, stroke_preview_scale: float) -> bool:
        cache = __class__.__get_cahce(node_tree)
        hash_obj = cache.hash
        node_location = cache.node_location
        node_dimensions = cache.node_dimensions
        node_name = cache.node_name
        cache._update(preview_size, stroke_preview_width, brush_detail_node, brush_size, stroke_preview_scale)
        return (cache.hash != hash_obj or
                cache.node_location != node_location or
                cache.node_dimensions != node_dimensions or
                cache.node_name != node_name)

    @staticmethod
    def _draw():
        node_tree = bpy.context.space_data.edit_tree
        if not isinstance(node_tree, PencilNodeTree):
            return
        __class__.validate_cache(node_tree, bpy.context)
        cache = __class__.__preview_caches.get(node_tree.name_full)
        cache.draw_origin = None
        if cache.hash is None:
            return
        brush_detail, _ = __class__.__get_preview_target_node(node_tree)
        if brush_detail is None or brush_detail.name != cache.node_name:
            return
        cache.draw_origin = Vector((
            brush_detail.location.x * bpy.context.preferences.system.ui_scale,
            (brush_detail.location.y + 5) * bpy.context.preferences.system.ui_scale - 0.5 * brush_detail.dimensions[1]))
        origin = bpy.context.region.view2d.view_to_region(cache.draw_origin.x, cache.draw_origin.y, clip=False)
        
        scale = bpy.context.preferences.system.ui_scale
        preview_size = cache.preview_size * scale
        stroke_preview_width = cache.stroke_preview_width * scale
        preview_margin = 16 * scale
        aa_size = 0.5 * scale
        border_width = 1 * scale
        corner_size = 10 * scale

        with gpu.matrix.push_pop():
            with gpu.matrix.push_pop_projection():
                screen_width = bpy.context.region.width
                screen_height = bpy.context.region.height
                # theme = bpy.context.preferences.themes[0]
                boder_color = (0.95,) * 3 + (1.0,) #theme.node_editor.node_active[:] + (1.0,)
                color0 = (0.1,) * 3 + (1.0,)
                color1 = (0.8,) * 3 + (1.0,)
                gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(Matrix.Translation((-1.0, 1.0, 0, 1)) @
                                                  Matrix.Diagonal((2.0 / screen_width, -2.0 / screen_height, 1, 1)))
                gpu.state.blend_set("ALPHA")
                w = preview_size + stroke_preview_width + border_width * 3
                h = preview_size + border_width * 2
                x = origin[0] - w - preview_margin
                y = screen_height - origin[1] - 0.5 * h
                __class__.__draw_color(Vector((x, y)), w, h,
                                       boder_color,
                                       aa_size=aa_size, margin=(corner_size, corner_size, corner_size, corner_size))
                x += border_width
                y += border_width
                corner_size -= border_width
                __class__.__draw_preview(Vector((x, y)), preview_size, preview_size,
                                         cache.brush_preview_texture, color0, color1,
                                         aa_size=aa_size, margin=(corner_size, 0, corner_size, corner_size))
                x += preview_size + border_width
                __class__.__draw_preview(Vector((x, y)), stroke_preview_width, preview_size,
                                         cache.stroke_preview_texture, color0, color1,
                                         aa_size=aa_size, margin=(corner_size, corner_size, corner_size, 0))

    @staticmethod
    def _check_target_node_location():
        # brush_detail.dimensions が _draw で変わり得るので、その変化を検知してキャッシュを更新する
        node_tree = bpy.context.space_data.edit_tree
        if not isinstance(node_tree, PencilNodeTree):
            return
        cache = __class__.__preview_caches.get(node_tree.name_full)
        if cache is None or cache.hash is None:
            return
        brush_detail, _ = __class__.__get_preview_target_node(node_tree)
        if brush_detail is None:
            return
        origin = Vector((
            brush_detail.location.x * bpy.context.preferences.system.ui_scale,
            (brush_detail.location.y + 5) * bpy.context.preferences.system.ui_scale - 0.5 * brush_detail.dimensions[1]))
        if cache.draw_origin is not None and cache.draw_origin != origin:
            __class__.validate_cache(node_tree, bpy.context)

    @staticmethod
    def __create_shader(vertex_source:str,
                  fragment_source:str,
                  params:gpu_utils.ShaderParameters,
                  ) -> gpu.types.GPUShader:
        params.add_constant('VEC2', "ProjectionXY")
        params.add_constant('VEC2', "origin")
        params.add_constant('VEC2', "size")
        params.add_constant('FLOAT', "aaSize")
        params.add_constant('VEC4', "margin")
        params.add_vert_input('VEC2', "uv")
        params.add_vert_output('VEC2', "uvInterp")
        params.add_frag_output('VEC4', "FragColor")
        fragment_source = '''
        float calc_aa()
        {
            vec2 relativePos = uvInterp * abs(size);
            float r = min(uvInterp.x > 0.5 ? margin.y : margin.w, uvInterp.y < 0.5 ? margin.x : margin.z);
            vec2 c = min(max(relativePos, aaSize + r), size - aaSize - r);
            return min(max(1 - (length(relativePos - c) - r) / max(aaSize, 1e-6), 0.0), 1.0);
        }

        ''' + fragment_source

        return gpu_utils.create_shader(vertex_source, fragment_source, params)  

    __draw_color_shader = None
    @staticmethod
    def __get_draw_color_shader():
        if __class__.__draw_color_shader is None:
            params = gpu_utils.ShaderParameters()
            params.add_constant('VEC4', "color")
            __class__.__draw_color_shader = __class__.__create_shader(
                """
                void main()
                {
                    uvInterp = uv;
                    gl_Position = vec4((origin + uv * size) * ProjectionXY + vec2(-1, 1), 0.0, 1.0);
                }
                """,
                """
                void main()
                {
                    FragColor = color;
                    FragColor.a *= calc_aa();
                }
                """,
                params
            )
        return __class__.__draw_color_shader

    __draw_preview_shader = None
    @staticmethod
    def __get_draw_preview_shader():
        if __class__.__draw_preview_shader is None:
            params = gpu_utils.ShaderParameters()
            params.add_constant('VEC4', "color0")
            params.add_constant('VEC4', "color1")
            params.add_sampler("FLOAT_2D", "image")
            __class__.__draw_preview_shader = __class__.__create_shader(
                """
                void main()
                {
                    uvInterp = uv;
                    gl_Position = vec4((origin + uv * size) * ProjectionXY + vec2(-1, 1), 0.0, 1.0);
                }
                """,
                """
                void main()
                {
                    FragColor = color0 + (color1 - color0) * texture(image, uvInterp).r;
                    FragColor.a *= calc_aa();
                }
                """,
                params
            )
        return __class__.__draw_preview_shader

    @staticmethod
    def __get_shader_batch(shader: gpu.types.GPUShader):
        return batch_for_shader(shader,
            'TRIS',
            {"uv": ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0))},
            indices=((0, 1, 2), (2, 1, 3)))

    @staticmethod
    def __setup_shader_common(shader: gpu.types.GPUShader, p: Vector, w: float, h: float, aa_size: float, margin: Iterable[float]):
        shader.uniform_float("ProjectionXY", (gpu.matrix.get_projection_matrix()[0][0], gpu.matrix.get_projection_matrix()[1][1]))
        shader.uniform_float("origin", p)
        shader.uniform_float("size", (w, h,))
        shader.uniform_float("aaSize", aa_size)
        shader.uniform_float("margin", margin)

    @staticmethod
    def __draw_color(p: Vector, w: float, h: float,
                     color: Iterable[float],
                     aa_size: float = 0.0, margin: Iterable[float] = (0.0, 0.0, 0.0, 0.0)):
        shader = __class__.__get_draw_color_shader()
        shader.bind()
        batch = __class__.__get_shader_batch(shader)
        __class__.__setup_shader_common(shader, p, w, h, aa_size, margin)
        shader.uniform_float("color", color)
        batch.draw(shader)

    @staticmethod
    def __draw_preview(p: Vector, w: float, h: float,
                        tex: gpu.types.GPUTexture, color0: Iterable[float], color1: Iterable[float], 
                        aa_size: float = 0.0, margin: Iterable[float] = (0.0, 0.0, 0.0, 0.0)):
        shader = __class__.__get_draw_preview_shader()
        shader.bind()
        batch = __class__.__get_shader_batch(shader)
        __class__.__setup_shader_common(shader, p, w, h, aa_size, margin)
        shader.uniform_float("color0", color0)
        shader.uniform_float("color1", color1)
        shader.uniform_sampler("image", tex)
        batch.draw(shader)


__draw_handler = None
__draw_handler_for_check_location = None
        
def register():
    global __draw_handler, __draw_handler_for_check_location
    __draw_handler = bpy.types.SpaceNodeEditor.draw_handler_add(PreviewManager._draw, (), "WINDOW", "BACKDROP")
    __draw_handler_for_check_location = bpy.types.SpaceNodeEditor.draw_handler_add(PreviewManager._check_target_node_location, (), "WINDOW", "POST_PIXEL")

def unregister():
    global __draw_handler, __draw_handler_for_check_location
    if __draw_handler is not None:
        bpy.types.SpaceNodeEditor.draw_handler_remove(__draw_handler, "WINDOW")
        __draw_handler = None
    if __draw_handler_for_check_location is not None:
        bpy.types.SpaceNodeEditor.draw_handler_remove(__draw_handler_for_check_location, "WINDOW")
        __draw_handler_for_check_location = None