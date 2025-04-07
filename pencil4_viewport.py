# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import sys
import platform

__is_reloaded = False

if "bpy" in locals():
    import imp
    imp.reload(pencil4line_for_blender)
    imp.reload(pencil4_render_images)
    imp.reload(pencil4_render_session)
    imp.reload(gpu_utils)
    imp.reload(Translation)
    __is_reloaded = True
else:
    if platform.system() == "Windows":
        if sys.version_info.major == 3 and sys.version_info.minor == 9:
            from .bin import pencil4line_for_blender_win64_39 as pencil4line_for_blender
        elif sys.version_info.major == 3 and sys.version_info.minor == 10:
            from .bin import pencil4line_for_blender_win64_310 as pencil4line_for_blender
        elif sys.version_info.major == 3 and sys.version_info.minor == 11:
            from .bin import pencil4line_for_blender_win64_311 as pencil4line_for_blender
    elif platform.system() == "Darwin":
        if sys.version_info.major == 3 and sys.version_info.minor == 9:
            from .bin import pencil4line_for_blender_mac_39 as pencil4line_for_blender
        elif sys.version_info.major == 3 and sys.version_info.minor == 10:
            from .bin import pencil4line_for_blender_mac_310 as pencil4line_for_blender
        elif sys.version_info.major == 3 and sys.version_info.minor == 11:
            from .bin import pencil4line_for_blender_mac_311 as pencil4line_for_blender
    elif platform.system() == "Linux":
        if sys.version_info.major == 3 and sys.version_info.minor == 9:
            from .bin import pencil4line_for_blender_linux_39 as pencil4line_for_blender
        elif sys.version_info.major == 3 and sys.version_info.minor == 10:
            from .bin import pencil4line_for_blender_linux_310 as pencil4line_for_blender
        elif sys.version_info.major == 3 and sys.version_info.minor == 11:
            from .bin import pencil4line_for_blender_linux_311 as pencil4line_for_blender
    from . import pencil4_render_images
    from . import pencil4_render_session
    from .misc import gpu_utils
    from .i18n import Translation

from .pencil4_render_session import Pencil4RenderSession as RenderSession

import itertools
from typing import Tuple
from typing import Iterable
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from gpu_extras.presets import draw_texture_2d
import blf
from enum import IntEnum
from mathutils import Matrix

class ViewportLineRenderSettings(bpy.types.PropertyGroup):
    rendering_target_items = (
        ("WHOLE_VIEWPORT", "Whole Viewport", "", 0),
        ("CAMERA_AREA", "Camera Area", "", 1),
    )

    enable: bpy.props.BoolProperty(default=False)
    enalbe_background_color: bpy.props.BoolProperty(default=False)
    background_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=4, min=0.0, max=1.0, default=[1.0, 1.0, 1.0, 1.0])
    camera_view_range: bpy.props.EnumProperty(items=rendering_target_items, default="WHOLE_VIEWPORT")
    camera_view_scale: bpy.props.BoolProperty(default=False)
    enalbe_background_color_for_render: bpy.props.BoolProperty(default=False)
    background_color_for_render: bpy.props.FloatVectorProperty(subtype="COLOR", size=4, min=0.0, max=1.0, default=[1.0, 1.0, 1.0, 1.0])

    saved_area_index: bpy.props.IntProperty(default=-1)
    saved_space_index: bpy.props.IntProperty(default=-1)


class ViewportLineRenderManager:
    in_render_session = False

    __settings_dict = {}
    __timeout2_interval = 0.500

    class RenderMode(IntEnum):
        Initialize = 0
        Normal = 1
        Wait = 2
        Error = -1
        Timeout = -2

    class DictValue:
        def __init__(self) -> None:
            self.collection_index = -1
            self.handle = None
            self.handle_2d = None
            self.render_session_dict = {}

    @staticmethod
    def reset_for_space(space: bpy.types.Space) -> bool:
        modified = False
        dict_value = __class__.get(space)
        if dict_value is not None and dict_value.handle is not None:
            space.draw_handler_remove(dict_value.handle, "WINDOW")
            dict_value.handle = None
            modified = True
        if dict_value is not None and dict_value.handle_2d is not None:
            space.draw_handler_remove(dict_value.handle_2d, "WINDOW")
            dict_value.handle_2d = None
            modified = True
        for session in dict_value.render_session_dict.values():
            if session.registered_timer_func:
                bpy.app.timers.unregister(session.registered_timer_func)
        dict_value.render_session_dict.clear()
        return modified

    @staticmethod
    def reset():
        for space in ViewportLineRenderManager.__settings_dict.keys():
            __class__.reset_for_space(space)
        ViewportLineRenderManager.__settings_dict.clear()

    @staticmethod
    def load():
        __class__.reset()
        for screen in bpy.data.screens:
            for collection_index, settings in enumerate(screen.pencil4_line_viewport_render_settings):
                if settings.saved_area_index < 0 or len(screen.areas) <= settings.saved_area_index:
                    continue
                area = screen.areas[settings.saved_area_index]
                if settings.saved_space_index < 0 or len(area.spaces) <= settings.saved_space_index:
                    continue
                space = area.spaces[settings.saved_space_index]
                __class__.__settings_dict[space] = ViewportLineRenderManager.DictValue()
                dict_value = __class__.__settings_dict[space]
                dict_value.collection_index = collection_index
                if settings.enable:
                    __class__;__class__.enable(space)


    @staticmethod
    def save():
        for screen in bpy.data.screens:
            collection = screen.pencil4_line_viewport_render_settings
            if len(collection) == 0:
                continue
            for setting in collection:
                setting.saved_area_index = -1
                setting.saved_space_index = -1
            for area_index, area in enumerate(screen.areas):
                for space_index, s in enumerate(area.spaces):
                    settings = __class__.get_settings(s)
                    if settings is not None:
                        settings.saved_area_index = area_index
                        settings.saved_space_index = space_index

    @staticmethod
    def get_area_and_screen(space: bpy.types.Space) -> Tuple[bpy.types.Area, bpy.types.Screen]:
        for screen in bpy.data.screens:
            for area in screen.areas:
                for s in area.spaces:
                    if s == space:
                        return [area, screen]
        return [None, None]

    @classmethod
    def get_settings(cls, space: bpy.types.Space) -> ViewportLineRenderSettings:
        value = cls.get(space)
        if value is None:
            return None
        _, screen = cls.get_area_and_screen(space)
        if screen is None:
            return None
        collection = screen.pencil4_line_viewport_render_settings
        return collection[value.collection_index] if 0 <= value.collection_index and value.collection_index < len(collection) else None

    @classmethod
    def get(cls, space: bpy.types.Space) -> DictValue:
        return cls.__settings_dict.get(space)

    @classmethod
    def enable(cls, space: bpy.types.Space):
        modified = False
        area, screen = cls.get_area_and_screen(space)

        dict_value = cls.get(space)
        if dict_value is None:
            cls.__settings_dict[space] = ViewportLineRenderManager.DictValue()
            dict_value = cls.__settings_dict[space]
            modified = True
        if dict_value.handle is None:
            dict_value.handle = space.draw_handler_add(cls.__draw, (space, ), 'WINDOW', 'POST_VIEW')
            modified = True
        if dict_value.handle_2d is None:
            dict_value.handle_2d = space.draw_handler_add(cls.__draw_2d, (space, ), 'WINDOW', 'POST_PIXEL')
            modified = True
        for session in dict_value.render_session_dict.values():
            session.render_mode = cls.RenderMode.Initialize

        settings = cls.get_settings(space)
        if settings is None:
            if screen is not None:
                collection = screen.pencil4_line_viewport_render_settings
                dict_value.collection_index = len(collection)
                settings = collection.add()
                modified = True
        if settings is not None and not settings.enable:
            settings.enable = True
            modified = True
        
        if modified and area is not None:
            area.tag_redraw()

    @classmethod
    def disable(cls, space: bpy.types.Space):
        modified = cls.reset_for_space(space)

        settings = cls.get_settings(space)
        if settings is not None and settings.enable:
            settings.enable = False
            modified = True

        area, _ = cls.get_area_and_screen(space)
        if modified and area is not None:
            area.tag_redraw()

    @classmethod
    def get_render_session(cls, space: bpy.types.SpaceView3D, region_3d: bpy.types.RegionView3D) -> pencil4_render_session.Pencil4RenderSession:
        dict_value = cls.get(space)
        if dict_value is None:
            return None
        regions = space.region_quadviews.values()
        regions.append(space.region_3d)
        del_keys = list(x for x in dict_value.render_session_dict if not x in regions)
        for key in del_keys:
            dict_value.render_session_dict.pop(key)
        if dict_value.render_session_dict.get(region_3d) is None:
            session = RenderSession()
            dict_value.render_session_dict[region_3d] = session
            session.render_mode = cls.RenderMode.Initialize
            session.registered_timer_func = None

        return dict_value.render_session_dict[region_3d]

    @classmethod
    def get_render_session_mode(cls, space: bpy.types.SpaceView3D) -> RenderMode:
        dict_value = cls.get(space)
        if dict_value is None:
            return None
        ret = cls.RenderMode.Normal
        for render_session in dict_value.render_session_dict.values():
            if render_session.render_mode < ret:
                ret = render_session.render_mode
        return ret      

    @classmethod
    def invalidate_objects_cache(cls):
        for dict_value in cls.__settings_dict.values():
            for render_session in dict_value.render_session_dict.values():
                render_session.objects_cache_valid = False
        

    @classmethod
    def __draw_timeout2(cls, space: bpy.types.SpaceView3D, region: bpy.types.Region, region_3d: bpy.types.RegionView3D):
        render_session = cls.get_render_session(space, region_3d)
        render_session.registered_timer_func = None

        # ライン描画がタイムアウトした場合、
        # ビューポートの再描画が落ち着いた場合により長いタイムアウト時間でライン描画を試行する
        if render_session.render_mode == __class__.RenderMode.Wait:
            render_session.render_mode = cls.RenderMode.Initialize
            region.tag_redraw()

    @staticmethod
    def camera_border(scene: bpy.types.Scene, region: bpy.types.Region, space: bpy.types.SpaceView3D, rv3d: bpy.types.RegionView3D):
        from bpy_extras.view3d_utils import location_3d_to_region_2d
        camera = space.camera if space.camera is not None and space.camera.type == "CAMERA" else scene.camera
        frame = [rv3d.view_matrix.inverted() @ v for v in camera.data.view_frame(scene=scene)]
        return [location_3d_to_region_2d(region, rv3d, v) for v in frame]

    @classmethod
    def __draw(cls, space: bpy.types.Space):
        if bpy.context.space_data != space:
            return

        settings = cls.get_settings(space)
        if settings is None or not settings.enable:
            return

        region: bpy.types.Region = bpy.context.region
        region_3d: bpy.types.RegionView3D = bpy.context.region_data
        render_session = cls.get_render_session(space, region_3d)
        pixels = None
        width = region.width
        height = region.height
        draw_texture_origin = None
        draw_texture_size = None

        #　ライン描画の実行
        if render_session.render_mode >= 0 and render_session.render_mode != cls.RenderMode.Wait:
            if cls.in_render_session or PCL4_OT_ViewportRender.is_rendering():
                # Blenderのレンダリング実行中/ビューポートレンダリング出力中は強制的にライン描画を待機状態にする
                render_session.render_mode = cls.RenderMode.Wait
            else:
                depsgraph = bpy.context.evaluated_depsgraph_get()
                if depsgraph is None:
                    return

                # 描画
                draw_option = render_session.get_draw_option(new_if_none = True)
                draw_option.timeout = 0.100 if render_session.render_mode != cls.RenderMode.Initialize else\
                    bpy.context.preferences.addons[__package__].preferences.viewport_render_timeout
                draw_option.objects_cache_valid = render_session.objects_cache_valid if render_session.render_mode != cls.RenderMode.Initialize else False
                matrix_override_func = None
                if region_3d.view_perspective == "CAMERA" and settings.camera_view_range == "CAMERA_AREA":
                    width, height = pencil4_render_session.get_render_size(depsgraph)
                    border = cls.camera_border(bpy.context.scene, region, space, region_3d)
                    draw_texture_origin = (border[2][0] / region.width, border[1][1] / region.height)
                    draw_texture_size = ((border[0][0] - border[2][0]) / region.width, (border[0][1] - border[1][1]) / region.height)
                    def matrix_override(camera_matrix, window_matrix):
                        return _calc_matrix_override(width, height, region, region_3d, depsgraph, camera_matrix, window_matrix)
                    matrix_override_func = matrix_override
                    draw_option.line_scale = 1.0
                    draw_option.linesize_relative_target_width = 0
                    draw_option.linesize_relative_target_height = 0
                    draw_option.linesize_absolute_scale = 1.0
                elif region_3d.view_perspective == "CAMERA" and settings.camera_view_scale:
                    border = cls.camera_border(bpy.context.scene, region, space, region_3d)
                    border_height = border[0][1] - border[1][1]
                    render_height = depsgraph.scene.render.resolution_y * depsgraph.scene.render.resolution_percentage * 0.01
                    draw_option.line_scale = border_height / render_height
                    draw_option.linesize_relative_target_width, draw_option.linesize_relative_target_height = pencil4_render_session.get_render_size(depsgraph)
                    draw_option.linesize_absolute_scale = 1.0
                else:
                    draw_option.line_scale = 1.0
                    draw_option.linesize_relative_target_width = 0
                    draw_option.linesize_relative_target_height = 0
                    draw_option.linesize_absolute_scale = bpy.context.preferences.system.ui_scale / bpy.context.preferences.view.ui_scale

                draw_ret = render_session.draw_line_for_viewport(depsgraph, width, height, space, region_3d, matrix_override_func)
                render_session.cleanup_frame()

                if draw_ret == pencil4line_for_blender.draw_ret.success or draw_ret == pencil4line_for_blender.draw_ret.success_without_license:
                    pixels = render_session.get_viewport_image_buffer()
                    render_session.render_mode = cls.RenderMode.Normal
                    render_session.objects_cache_valid = True
                elif draw_ret == pencil4line_for_blender.draw_ret.timeout:
                    render_session.objects_cache_valid = False
                    if render_session.render_mode == cls.RenderMode.Initialize:
                        # 長い設定時間にも関わらずタイムアウトした場合、以降のライン描画を停止する
                        render_session.render_mode = cls.RenderMode.Timeout
                        bpy.app.timers.register(lambda: RedrawPanel(), first_interval=0) 
                    else:
                        # 短い設定時間でタイムアウトした場合、
                        # 操作のレスポンス向上のためエリア内の全ライン描画を待機状態にする
                        for session in cls.get(space).render_session_dict.values():
                            session.render_mode = cls.RenderMode.Wait
                else:
                    render_session.render_mode = cls.RenderMode.Error
                    bpy.app.timers.register(lambda: RedrawPanel(), first_interval=0) 

        if render_session.render_mode == cls.RenderMode.Wait:
            # 通常の描画でタイムアウトした場合、より長いタイムアウト時間で描画を試行するためタイマーを設定する
            if render_session.registered_timer_func:
                bpy.app.timers.unregister(render_session.registered_timer_func)

            render_session.registered_timer_func = lambda: cls.__draw_timeout2(space, region, region_3d)
            bpy.app.timers.register(
                render_session.registered_timer_func,
                first_interval=cls.__timeout2_interval)

        with gpu.matrix.push_pop():
            with gpu.matrix.push_pop_projection():
                gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(Matrix.Identity(4))

                draw_line = pixels is not None and len(pixels) == width * height * 4

                if settings.enalbe_background_color:
                    color = list(settings.background_color)
                    if not draw_line:
                        color[3] *= 0.3
                    if color[3] != 1.0:
                        color = [color[0] * color[3], color[1] * color[3], color[2] * color[3], color[3]]
                    gpu.state.blend_set("ALPHA")
                    __class__.__draw_color(space, color)

                if draw_line:
                    pixels = gpu.types.Buffer("FLOAT", width * height * 4, pixels)
                    tex = gpu.types.GPUTexture((width, height), data=pixels)
                    gpu.state.blend_set("ALPHA")
                    __class__.__draw_texture(space, tex, draw_texture_origin, draw_texture_size)
                    del tex

    @staticmethod
    def __create_shader(vertex_source:str,
                  fragment_source:str,
                  params:gpu_utils.ShaderParameters,
                  ) -> gpu.types.GPUShader:
        params.add_vert_input("VEC2", "pos")
        params.add_constant("MAT4", "viewProjectionMatrix")
        params.add_constant("FLOAT", "isSRGB")
        params.add_constant("FLOAT", "isXYZ")
        params.add_constant("FLOAT", "isNone")
        params.add_constant("FLOAT", "exposure")
        params.add_constant("FLOAT", "gamma")
        params.add_frag_output("VEC4", "FragColor")
        fragment_source = '''
        vec3 linear_to_srgb(vec3 c)
        {
            c = max(c, vec3(0.0));
            c = mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
            return c;
        }
        vec3 linear_to_xyz(vec3 c)
        {
            return vec3(
                dot(c, vec3(0.4124, 0.3576, 0.1805)),
                dot(c, vec3(0.2126, 0.7152, 0.0722)),
                dot(c, vec3(0.0193, 0.1192, 0.9505))
            );
        }
        vec4 correct_color_for_framebuffer_space(vec4 linear)
        {
            vec3 c = linear.rgb / max(linear.a, 0.00001);
            c *= pow(2.0, exposure);
            c = isSRGB * linear_to_srgb(c) +
                isXYZ * linear_to_xyz(c) +
                isNone * c;
            c = pow(c, vec3(2.2 / gamma));
            return vec4(c, linear.a);
        }
        ''' + fragment_source
        return gpu_utils.create_shader(vertex_source, fragment_source, params)  

    __draw_color_shader = None
    @staticmethod
    def __get_draw_color_shader():
        if __class__.__draw_color_shader is None:
            params = gpu_utils.ShaderParameters()
            params.add_constant("VEC4", "color")
            __class__.__draw_color_shader = __class__.__create_shader(
                '''
                void main()
                {
                    gl_Position = viewProjectionMatrix * vec4(pos, 0.0, 1.0);
                }
                ''',
                '''
                void main()
                {
                    FragColor = correct_color_for_framebuffer_space(color);
                }
                ''',
                params
            )
        return __class__.__draw_color_shader
    
    __draw_tex_shader = None
    @staticmethod
    def __get_draw_tex_shader():
        if __class__.__draw_tex_shader is None:
            params = gpu_utils.ShaderParameters()
            params.add_constant("VEC2", "origin")
            params.add_constant("VEC2", "size")
            params.add_sampler("FLOAT_2D", "image")
            params.add_vert_output("VEC2", "uvInterp")
            __class__.__draw_tex_shader = __class__.__create_shader(
                '''
                void main()
                {
                    gl_Position = viewProjectionMatrix * vec4((pos - vec2(-1, -1)) * size + 2 * origin + vec2(-1, -1), 0.0, 1.0);
                    uvInterp = pos * 0.5 + 0.5;
                }
                ''',
                '''
                void main()
                {
                    FragColor = correct_color_for_framebuffer_space(texture(image, uvInterp));
                }
                ''',
                params
            )
        return __class__.__draw_tex_shader
    
    @staticmethod
    def __get_shader_batch(shader: gpu.types.GPUShader):
        return batch_for_shader(shader,
            'TRIS',
            {"pos": ((-1, -1), (1, -1), (-1, 1), (1, 1)),},
            indices=((0, 1, 2), (2, 1, 3)))

    @staticmethod
    def __setup_shader_common(shader: gpu.types.GPUShader, space: bpy.types.SpaceView3D):
        batch = batch_for_shader(shader,
            'TRIS',
            {"pos": ((-1, -1), (1, -1), (-1, 1), (1, 1)),},
            indices=((0, 1, 2), (2, 1, 3)))
        shader.uniform_float("viewProjectionMatrix", gpu.matrix.get_projection_matrix())
        if bpy.context.scene.view_settings.view_transform == "Raw":
            shader.uniform_float("isSRGB", 0.0)
            shader.uniform_float("isXYZ", 0.0)
            shader.uniform_float("isNone", 1.0)
        else:
            display_device = bpy.context.scene.display_settings.display_device
            if not display_device in ("sRGB", "XYZ", "None"):
                display_device = "sRGB"
            shader.uniform_float("isSRGB", 1.0 if display_device == "sRGB" else 0.0)
            shader.uniform_float("isXYZ", 1.0 if display_device == "XYZ" else 0.0)
            shader.uniform_float("isNone", 1.0 if display_device == "None" else 0.0)
        if space.shading.type == "RENDERED" or space.shading.type == "MATERIAL":
            shader.uniform_float("exposure", bpy.context.scene.view_settings.exposure)
            shader.uniform_float("gamma", max(bpy.context.scene.view_settings.gamma, 1e-6))
        else:
            shader.uniform_float("exposure", 0.0)
            shader.uniform_float("gamma", 1.0)

    @staticmethod
    def __draw_color(space: bpy.types.SpaceView3D, color: list[float]):
        shader = __class__.__get_draw_color_shader()
        shader.bind()
        __class__.__setup_shader_common(shader, space)
        shader.uniform_float("color", color)
        __class__.__get_shader_batch(shader).draw(shader)

    @staticmethod
    def __draw_texture(space: bpy.types.SpaceView3D, tex: gpu.types.GPUTexture, origin: Tuple[float, float] = None, size: Tuple[float, float] = None):
        shader = __class__.__get_draw_tex_shader()
        shader.bind()
        __class__.__setup_shader_common(shader, space)
        shader.uniform_sampler("image", tex)
        shader.uniform_float("origin", origin if origin is not None else (0.0, 0.0))
        shader.uniform_float("size", size if size is not None else (1.0, 1.0))
        __class__.__get_shader_batch(shader).draw(shader)


    @classmethod
    def __draw_2d(cls, space: bpy.types.Space):
        if bpy.context.space_data != space:
            return

        settings = cls.get_settings(space)
        if settings is None or not settings.enable:
            return

        region: bpy.types.Region = bpy.context.region
        region_3d: bpy.types.RegionView3D = bpy.context.region_data
        render_session = cls.get_render_session(space, region_3d)

        font_id = 0
        msg = None
        if render_session.render_mode == cls.RenderMode.Wait:
            msg = "Waiting..."
            blf.color(font_id, 1, 1, 0, 1)
        elif render_session.render_mode == cls.RenderMode.Timeout:
            msg = "Timeout..."
            blf.color(font_id, 1, 0, 0, 1)
        elif render_session.render_mode == cls.RenderMode.Error:
            msg = "Error"
            blf.color(font_id, 1, 0, 0, 1)

        if msg is not None:
            is_error = render_session.render_mode != cls.RenderMode.Wait
            msg = "Timeout" if render_session.render_mode == cls.RenderMode.Timeout else\
                "Error" if is_error else "Waiting..."
            msg = "Pencil+ 4 Line : " + msg
            blf.position(font_id, 12, 12, 0)
            if bpy.app.version < (4, 0, 0):
                blf.size(font_id, 12, 72)
            else:
                blf.size(font_id, 12)
            blf.color(font_id, 1, 0 if is_error else 1, 0, 1)
            blf.enable(font_id, blf.SHADOW)
            blf.shadow(font_id, 5, 0, 0, 0, 1)
            blf.shadow_offset(font_id, 1, -1)
            blf.draw(font_id, msg)


class PCL4_OT_EnableViewportLineRender(bpy.types.Operator):
    bl_idname = "pcl4.enable_viewport_line_render"
    bl_label = "On"
    bl_options = {'REGISTER'}
    bl_translation_context = Translation.ctxt

    def execute(self, context):
        ViewportLineRenderManager.enable(context.space_data)
        return {'FINISHED'}

class PCL4_OT_RetryViewportLineRender(bpy.types.Operator):
    bl_idname = "pcl4.retry_viewport_line_render"
    bl_label = "Retry"
    bl_options = {'REGISTER'}
    bl_translation_context = Translation.ctxt

    def execute(self, context):
        ViewportLineRenderManager.disable(context.space_data)
        ViewportLineRenderManager.enable(context.space_data)
        return {'FINISHED'}

class PCL4_OT_DisableViewportLineRender(bpy.types.Operator):
    bl_idname = "pcl4.disable_viewport_line_render"
    bl_label = "Off"
    bl_options = {'REGISTER'}
    bl_translation_context = Translation.ctxt

    def execute(self, context):
        ViewportLineRenderManager.disable(context.space_data)
        return {'FINISHED'}

class PCL4_PT_ViewportLinePreview(bpy.types.Panel):
    bl_idname = "PCL4_PT_viewport_line_preview"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"
    bl_label = "Viewport Display"
    bl_translation_context = Translation.ctxt
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        settings = ViewportLineRenderManager.get_settings(context.space_data)
        mode = ViewportLineRenderManager.get_render_session_mode(context.space_data) if settings is not None else 0
        if mode < 0:
            layout.alert = True
            if pencil4_render_session.get_dll_valid():
                is_timeouted = mode == ViewportLineRenderManager.RenderMode.Timeout
                layout.label(text="Timeout" if is_timeouted else "Error", icon="ERROR", translate=False)
                if is_timeouted:
                    layout.operator("pcl4.show_preferences", icon="PREFERENCES", text="Adjust Timeout Period", text_ctxt=Translation.ctxt)
                else:
                    layout.operator("pcl4.show_preferences", icon="PREFERENCES")
                layout.operator(PCL4_OT_RetryViewportLineRender.bl_idname, icon="FILE_REFRESH")
            else:
                layout.label(text="Add-on install error", icon="ERROR", text_ctxt=Translation.ctxt)
                layout.operator("pcl4.show_preferences", icon="PREFERENCES", text="Show Details", text_ctxt=Translation.ctxt)
            layout.alert = False
            layout.separator()
        enable = settings is not None and settings.enable
        layout.box().operator((PCL4_OT_DisableViewportLineRender if enable else PCL4_OT_EnableViewportLineRender).bl_idname,
                              text="Line Preview", icon='VIEW3D', depress=enable)
        if not enable or mode < 0:
            return
        layout.separator()

        def prop(prop_name, label_text):
            col.prop(settings, prop_name, text=label_text, text_ctxt=Translation.ctxt)
        col = layout.column(align=True)
        prop("enalbe_background_color", "Background Color")
        col = col.column()
        col.enabled = settings.enalbe_background_color
        prop("background_color", "")
        layout.separator()
        col = layout.column(heading="Camera View Options", heading_ctxt=Translation.ctxt)
        col.enabled = context.space_data.region_3d.view_perspective == "CAMERA"
        prop("camera_view_range", "Range")
        if settings.camera_view_range == "WHOLE_VIEWPORT":
            prop("camera_view_scale", "Line Size Adjustment")

class PCL4_PT_ViewportLineRender(bpy.types.Panel):
    bl_idname = "PCL4_PT_viewport_line_render"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"
    bl_label = "Viewport Render"
    bl_translation_context = Translation.ctxt
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        props = box.operator("pcl4.viewport_render", text="Render Image", icon='RENDER_STILL',)
        props.animation = False
        props.render_keyed_only = False
        props = box.operator("pcl4.viewport_render", text="Render Animation", icon='RENDER_ANIMATION',)
        props.animation = True
        props.render_keyed_only = False
        props = box.operator("pcl4.viewport_render", text="Render Keyframes", icon='RENDER_ANIMATION',)
        props.animation = True
        props.render_keyed_only = True
        layout.separator()

        def prop(prop_name, label_text):
            col.prop(context.scene, prop_name, text=label_text, text_ctxt=Translation.ctxt)
        col = layout.column(align=True)
        prop("pencil4_line_viewport_render_background_color_enable", "Background Color")
        col = col.column()
        col.enabled = context.scene.pencil4_line_viewport_render_background_color_enable
        prop("pencil4_line_viewport_render_background_color", "")

class PCL4_OT_ViewportRender(bpy.types.Operator):
    bl_idname = "pcl4.viewport_render"
    bl_label = "Viewport Render"
    bl_options = {'REGISTER'}
    bl_translation_context = Translation.ctxt

    animation: bpy.props.BoolProperty(default=False)
    render_keyed_only: bpy.props.BoolProperty(default=False)

    __timer = None

    @staticmethod
    def is_rendering():
        return __class__.__timer is not None
    
    @staticmethod
    def create_render_result_override_image(file_path: str) -> bpy.types.Image:
        __class__.delete_render_result_override_image()
        image = bpy.data.images.load(file_path, check_existing=True)
        image.name = "Render Result (Pencil+ 4)"
        image["is_pcl4_render_result"] = True
        return image

    @staticmethod
    def delete_render_result_override_image():
        while True:
            image = next((image for image in bpy.data.images if image.get("is_pcl4_render_result", False)), None)
            if image is not None:
                bpy.data.images.remove(image)
            else:
                break

    @staticmethod
    def get_render_result_override_image() -> bpy.types.Image:
        return next((image for image in bpy.data.images if image.get("is_pcl4_render_result", False)), None)
    
    @staticmethod
    def set_render_view_image(image: bpy.types.Image):
        for window in bpy.context.window_manager.windows:
            if window.screen.is_temporary and len(window.screen.areas) == 1 and window.screen.areas[0].type == "IMAGE_EDITOR":
                if window.screen.areas[0].spaces[0].image != image:
                    window.screen.areas[0].spaces[0].image = image

    def cleanup(self, context):
        output_image = __class__.get_render_result_override_image()
        if output_image is not None:
            output_image.pack()
            output_image.unpack(method="REMOVE")
        context.window_manager.event_timer_remove(__class__.__timer)
        __class__.__timer = None
        context.window.cursor_modal_restore()
        if self.animation:
            context.scene.frame_set(self.original_frame_current)

    def modal(self, context, event):
        if event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}
        if event.type == 'TIMER':
            frame_current = context.scene.frame_current
            frame_path = context.scene.render.frame_path(frame=frame_current)
            if context.scene.render.is_movie_format:
                frame_path += ".tmp"
            output_image = __class__.get_render_result_override_image()

            # 必要がある場合のみレンダリングを実行する
            if not self.animation or self.render_frames is None or frame_current in self.render_frames:
                space: bpy.types.SpaceView3D = bpy.context.space_data
                region: bpy.types.Region = bpy.context.region
                region_3d: bpy.types.RegionView3D = space.region_3d

                # Blenderのビューポートレンダリングを実行し、レンダリング結果を取得する
                bpy.ops.render.opengl()
                context.window.cursor_modal_set('WAIT')
                render_image = next(image for image in bpy.data.images if image.type == "RENDER_RESULT")
                render_image.save_render(frame_path)
                if output_image is None:
                    output_image = __class__.create_render_result_override_image(frame_path)
                    self.image_alpha_mode = output_image.alpha_mode
                    __class__.set_render_view_image(output_image)
                else:
                    if output_image.packed_file is not None:
                        output_image.unpack(method="REMOVE")
                    output_image.source = "FILE"
                    output_image.alpha_mode = self.image_alpha_mode
                    output_image.filepath = frame_path
                display_device = context.scene.display_settings.display_device
                if (display_device in bpy.types.ColorManagedInputColorspaceSettings.bl_rna.properties["name"].enum_items and
                    context.scene.view_settings.view_transform != "Raw"):
                    output_image.colorspace_settings.name = display_device
                else:
                    output_image.colorspace_settings.name = "Linear" if "Linear" in bpy.types.ColorManagedInputColorspaceSettings.bl_rna.properties["name"].enum_items else "Linear Rec.709"
                    if context.scene.view_settings.view_transform == "Raw":
                        output_image.use_view_as_render = True

                # ライン描画を実行する
                if self.session is None:
                    self.session = RenderSession()
                depsgraph = context.evaluated_depsgraph_get()
                width, height = pencil4_render_session.get_render_size(depsgraph)
                def matrix_override(camera_matrix, window_matrix):
                    return _calc_matrix_override(width, height, region, region_3d, depsgraph, camera_matrix, window_matrix)
                draw_ret = self.session.draw_line_for_viewport(context.evaluated_depsgraph_get(), width, height, space, region_3d, matrix_override)
                if draw_ret != pencil4line_for_blender.draw_ret.success and draw_ret != pencil4line_for_blender.draw_ret.success_without_license:
                    self.report({'ERROR'}, "Failed to render lines.")
                    self.cancel(context)
                    return {'CANCELLED'}
                
                # レンダリング結果にライン描画結果を合成する
                if bpy.app.version >= (3, 1, 0):
                    offscreen = gpu.types.GPUOffScreen(width, height, format='RGBA16F')
                else:
                    offscreen = gpu.types.GPUOffScreen(width, height)
                with offscreen.bind():
                    fb = gpu.state.active_framebuffer_get()
                    fb.clear(color=(0.0, 0.0, 0.0, 0.0))
                    with gpu.matrix.push_pop():
                        with gpu.matrix.push_pop_projection():
                            gpu.matrix.load_matrix(Matrix.Identity(4))
                            gpu.matrix.load_projection_matrix(Matrix.Identity(4))
                            tex = gpu.texture.from_image(output_image)
                            tex.read()
                            gpu.state.blend_set("NONE" if self.image_alpha_mode == "PREMUL" else "ALPHA")
                            draw_texture_2d(tex, (-1, -1), 2, 2)
                            del tex
                            if self.enalbe_background_color:
                                tex = gpu.types.GPUTexture((8, 8))
                                tex.clear(format="FLOAT", value=self.background_color)
                                gpu.state.blend_set("ALPHA")
                                draw_texture_2d(tex, (-1, -1), 2, 2)
                                del tex
                            if len(self.session.get_viewport_image_buffer()) == width * height * 4:
                                pixels = gpu.types.Buffer("FLOAT", width * height * 4, self.session.get_viewport_image_buffer())
                                tex = gpu.types.GPUTexture((width, height), data=pixels)
                                gpu.state.blend_set("ALPHA_PREMULT")
                                draw_texture_2d(tex, (-1, -1), 2, 2)
                                del tex
                    buffer = fb.read_color(0, 0, width, height, 4, 0, 'FLOAT')
                offscreen.free()
                buffer.dimensions = width * height * 4
                pencil4_render_images.setup_image(output_image, width, height)
                output_image.pixels = buffer
            
            # レンダリング結果を保存する
            if output_image is None:
                self.report({'ERROR'}, "Failed to Pencil+ 4 Line Viewport Render.")
                self.cancel(context)
                return {'CANCELLED'}
            output_image.save_render(frame_path)
            if not self.animation or frame_current >= context.scene.frame_end:
                self.cleanup(context)
                return {'FINISHED'}
            if self.animation:
                context.scene.frame_set(frame_current + context.scene.frame_step)
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if __class__.is_rendering():
            return {'CANCELLED'}
        if context.scene.render.is_movie_format and self.animation:
            self.report({'ERROR'}, "Movie format is not supported.")
            return {'CANCELLED'}
        self.render_frames = None
        self.session = None
        self.image_alpha_mode = None
        self.original_frame_current = context.scene.frame_current
        self.background_color = context.scene.pencil4_line_viewport_render_background_color
        self.enalbe_background_color = context.scene.pencil4_line_viewport_render_background_color_enable
        context.window_manager.modal_handler_add(self)
        context.window.cursor_modal_set('WAIT')
        __class__.__timer = context.window_manager.event_timer_add(0.01, window=context.window)
        if self.animation:
            context.scene.frame_set(context.scene.frame_start)
            if self.render_keyed_only:
                self.render_frames = set([context.scene.frame_start])
                for object in context.selected_objects:
                    if object.animation_data is not None and object.animation_data.action is not None:
                        for curve in object.animation_data.action.fcurves:
                            for keyframe in curve.keyframe_points:
                                self.render_frames.add(int(keyframe.co[0]))
        __class__.delete_render_result_override_image()
        bpy.ops.render.view_show('INVOKE_DEFAULT')
        __class__.set_render_view_image(None)
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        self.cleanup(context)


def _calc_matrix_override(width: int, height: int, region, region_3d, depsgraph, camera_matrix, window_matrix):
    base_size = max(width, height)
    scale = min(base_size / region.width, base_size / region.height)
    window_matrix = Matrix(window_matrix) @ Matrix(((scale * region.width / width, 0, 0, 0), (0, scale * region.height / height, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    if region_3d.view_perspective == "CAMERA":
        scene_camera = depsgraph.scene_eval.camera
        camera_matrix = pencil4_render_session.get_camera_matrix(scene_camera)
        sensor_size = max(width, height) if scene_camera.data.sensor_fit == "AUTO" else (width if scene_camera.data.sensor_fit == "HORIZONTAL" else height)
        window_matrix = scene_camera.calc_matrix_camera(depsgraph,
                            scale_x= depsgraph.scene.render.pixel_aspect_x * width / sensor_size,
                            scale_y= depsgraph.scene.render.pixel_aspect_y * height / sensor_size)
    return camera_matrix, window_matrix


def RedrawPanel():
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)


def register_props():
    bpy.types.Screen.pencil4_line_viewport_render_settings = bpy.props.CollectionProperty(type=ViewportLineRenderSettings)
    bpy.types.Scene.pencil4_line_viewport_render_background_color = bpy.props.FloatVectorProperty(subtype="COLOR", size=4, min=0.0, max=1.0, default=[1.0, 1.0, 1.0, 1.0])
    bpy.types.Scene.pencil4_line_viewport_render_background_color_enable = bpy.props.BoolProperty(default=False)
    if __is_reloaded:
        bpy.app.timers.register(
                    lambda: ViewportLineRenderManager.load(),
                    first_interval=0.0)
        

def unregister_props():
    ViewportLineRenderManager.save()
    ViewportLineRenderManager.reset()
    del(bpy.types.Scene.pencil4_line_viewport_render_background_color_enable)
    del(bpy.types.Scene.pencil4_line_viewport_render_background_color)
    del(bpy.types.Screen.pencil4_line_viewport_render_settings)


def on_save_pre():
    ViewportLineRenderManager.save()


def on_load_post():
    ViewportLineRenderManager.load()
