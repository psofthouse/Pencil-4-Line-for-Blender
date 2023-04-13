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
    imp.reload(Translation)
    __is_reloaded = True
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
    from . import pencil4_render_session
    from .i18n import Translation

from .pencil4_render_session import Pencil4RenderSession as RenderSession

from typing import Tuple
import bpy
import gpu
import bgl
import blf
import time
from struct import pack
from enum import IntEnum
from gpu_extras.batch import batch_for_shader

class ViewportLineRenderSettings(bpy.types.PropertyGroup):
    enable: bpy.props.BoolProperty(default=False)
    enalbe_background_color: bpy.props.BoolProperty(default=False)
    background_color: bpy.props.FloatVectorProperty(subtype="COLOR", size=4, min=0.0, max=1.0, default=[1.0, 1.0, 1.0, 1.0])
    camera_view_scale: bpy.props.BoolProperty(default=False)

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
            self.tex_buffer = None
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
        if dict_value is not None and dict_value.tex_buffer is not None:
            bgl.glDeleteTextures(1, dict_value.tex_buffer)
            dict_value.tex_buffer = None
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

    shader = None
    batch = None
    uniform_bg = None

    @classmethod
    def __setup_shader(cls):
        if cls.shader is None:
            vertex_shader = '''
                in vec2 position;
                in vec2 uv;

                out vec2 uvInterp;

                void main()
                {
                    uvInterp = uv;
                    gl_Position = vec4(position, 0.0, 1.0);
                }
            '''

            fragment_shader = '''
                uniform sampler2D image;
                uniform float alpha;
                uniform vec4 bg;

                in vec2 uvInterp;

                out vec4 FragColor;

                void main()
                {
                    vec4 line = alpha * texture(image, uvInterp);
                    FragColor.rgb = bg.rgb * bg.a * (1 - line.a) + line.rgb;
                    FragColor.a = 1 - (1 - bg.a) * (1 - line.a);
                }
            '''
            if bpy.app.version < (3, 1):
                fragment_shader = fragment_shader.replace("out vec4 FragColor", "")
                fragment_shader = fragment_shader.replace("FragColor", "gl_FragColor")

            cls.shader = gpu.types.GPUShader(vertex_shader, fragment_shader)
            cls.batch = batch_for_shader(
                cls.shader, 'TRI_FAN',
                {
                    "position": ((-1, -1), (1, -1), (1, 1), (-1, 1)),
                    "uv": ((0, 0), (1, 0), (1, 1), (0, 1)),
                },
            )
            cls.uniform_bg = cls.shader.uniform_from_name("bg")

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
        dict_value = cls.get(space)
        if dict_value.tex_buffer is None:
            dict_value.tex_buffer = bgl.Buffer(bgl.GL_INT, 1)
            bgl.glGenTextures(1, dict_value.tex_buffer)
            bgl.glActiveTexture(bgl.GL_TEXTURE0)
            bgl.glBindTexture(bgl.GL_TEXTURE_2D, dict_value.tex_buffer.to_list()[0])
            bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_MIN_FILTER, bgl.GL_LINEAR)
            bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_MAG_FILTER, bgl.GL_LINEAR)
        tex = dict_value.tex_buffer.to_list()[0]
        if tex is None:
            return

        region: bpy.types.Region = bpy.context.region
        region_3d: bpy.types.RegionView3D = bpy.context.region_data
        render_session = cls.get_render_session(space, region_3d)
        pixels = None

        #　ライン描画の実行
        if render_session.render_mode >= 0 and render_session.render_mode != cls.RenderMode.Wait:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            if depsgraph is None:
                return

            if cls.in_render_session:
                # Blenderのレンダリング実行中は強制的にライン描画を待機状態にする
                render_session.render_mode = cls.RenderMode.Wait
            else:
                # 描画
                draw_option = render_session.get_draw_option(new_if_none = True)
                draw_option.timeout = 0.100 if render_session.render_mode != cls.RenderMode.Initialize else\
                    bpy.context.preferences.addons[__package__].preferences.viewport_render_timeout
                draw_option.objects_cache_valid = render_session.objects_cache_valid if render_session.render_mode != cls.RenderMode.Initialize else False
                if region_3d.view_perspective == "CAMERA" and settings.camera_view_scale:
                    border = cls.camera_border(bpy.context.scene, region, space, region_3d)
                    border_height = border[0][1] - border[1][1]
                    render_height = depsgraph.scene.render.resolution_y * depsgraph.scene.render.resolution_percentage * 0.01
                    draw_option.line_scale = border_height / render_height
                    draw_option.linesize_relative_target_width = depsgraph.scene.render.resolution_x * depsgraph.scene.render.resolution_percentage // 100
                    draw_option.linesize_relative_target_height = depsgraph.scene.render.resolution_y * depsgraph.scene.render.resolution_percentage // 100
                else:
                    draw_option.line_scale = 1.0
                    draw_option.linesize_relative_target_width = 0
                    draw_option.linesize_relative_target_height = 0

                draw_ret = render_session.draw_line_for_viewport(depsgraph, region, space, region_3d)
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

        bg_r = settings.background_color[0] if settings.enalbe_background_color else 0
        bg_g = settings.background_color[1] if settings.enalbe_background_color else 0
        bg_b = settings.background_color[2] if settings.enalbe_background_color else 0
        bg_a = settings.background_color[3] if settings.enalbe_background_color else 0

        cls.__setup_shader()
        shader = cls.shader
        batch = cls.batch

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_ONE, bgl.GL_ONE_MINUS_SRC_ALPHA)
        bgl.glActiveTexture(bgl.GL_TEXTURE0)
        shader.bind()
        width = region.width
        height = region.height
        if pixels is not None and len(pixels) == width * height * 4:
            pixels = bgl.Buffer(bgl.GL_BYTE, width * height * 4, pixels)
            bgl.glBindTexture(bgl.GL_TEXTURE_2D, tex)
            bgl.glTexImage2D(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, width, height, 0,\
                bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, pixels)
            shader.uniform_float("alpha", 1.0)
        else:
            bgl.glBindTexture(bgl.GL_TEXTURE_2D, 0)
            shader.uniform_float("alpha", 0.0)
            bg_a *= 0.3
        shader.uniform_float("image", 0)
        shader.uniform_vector_float(cls.uniform_bg, pack("4f", bg_r, bg_g, bg_b, bg_a), 4)
        batch.draw(shader)


    @classmethod
    def __draw_2d(cls, space: bpy.types.Space):
        if bpy.context.space_data != space:
            return

        settings = cls.get_settings(space)
        if settings is None or not settings.enable:
            return
        tex = cls.get(space).tex_buffer.to_list()[0]
        if tex is None:
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
            blf.size(font_id, 12, 72)
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

class PCL4_PT_ViewportLineRender(bpy.types.Panel):
    bl_idname = "PCL4_PT_viewport_line_render"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Pencil+ 4 Line"
    bl_label = "Viewport Rendering"
    bl_translation_context = Translation.ctxt

    def draw(self, context):
        layout = self.layout

        settings = ViewportLineRenderManager.get_settings(context.space_data)

        if settings is None or not settings.enable:
            layout.operator(PCL4_OT_EnableViewportLineRender.bl_idname)
            return
        
        mode = ViewportLineRenderManager.get_render_session_mode(context.space_data)
        if mode < 0:
            layout.alert = True
            layout.label(text="Timeout" if mode == ViewportLineRenderManager.RenderMode.Timeout else "Error", icon="ERROR", translate=False)
            layout.operator(PCL4_OT_RetryViewportLineRender.bl_idname, icon="FILE_REFRESH")
            layout.alert = False
            layout.separator()
            layout.operator(PCL4_OT_DisableViewportLineRender.bl_idname)
            return

        layout.operator(PCL4_OT_DisableViewportLineRender.bl_idname)
        layout.separator()

        def prop(prop_name, label_text):
            col.prop(settings, prop_name, text=label_text, text_ctxt=Translation.ctxt)

        col = layout.column(align=True)
        prop("enalbe_background_color", "Background Color")
        col = col.column()
        col.enabled = settings.enalbe_background_color
        prop("background_color", "")

        layout.separator()
        col = layout.column(heading="Camera View Option", heading_ctxt=Translation.ctxt)
        prop("camera_view_scale", "Line Size Adjustment")


def RedrawPanel():
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)


def register_props():
    bpy.types.Screen.pencil4_line_viewport_render_settings = bpy.props.CollectionProperty(type=ViewportLineRenderSettings)
    if __is_reloaded:
        bpy.app.timers.register(
                    lambda: ViewportLineRenderManager.load(),
                    first_interval=0.0)
        

def unregister_props():
    ViewportLineRenderManager.save()
    ViewportLineRenderManager.reset()
    del(bpy.types.Screen.pencil4_line_viewport_render_settings)


def on_save_pre():
    ViewportLineRenderManager.save()


def on_load_post():
    ViewportLineRenderManager.load()
