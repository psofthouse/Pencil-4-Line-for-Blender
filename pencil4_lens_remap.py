# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

"""非線形レンズ（パノラマ・魚眼カメラ）向けのライン重ね合わせ処理。

6 面（90° + オーバースキャン）のライン画像を、レンズごとの方向対応表（LUT）に従って
1 枚の画像へ変換する。透視・平行投影のカメラでは使用しない。
"""

from dataclasses import dataclass
import math

import numpy as np

# 面のオーバースキャン倍率（半画角の正接）。面の境界付近の欠けを防ぐ。
FACE_OVERSCAN_TAN = 1.05

# 各面の (前方, 右, 上) をカメラローカル座標で表す（前方 = -Z, 右 = +X, 上 = +Y）
_CUBE_FACES = (
    ((0, 0, -1), (1, 0, 0), (0, 1, 0)),   # 前
    ((0, 0, 1), (-1, 0, 0), (0, 1, 0)),   # 後
    ((1, 0, 0), (0, 0, 1), (0, 1, 0)),    # 右
    ((-1, 0, 0), (0, 0, -1), (0, 1, 0)),  # 左
    ((0, 1, 0), (1, 0, 0), (0, 0, 1)),    # 上
    ((0, -1, 0), (1, 0, 0), (0, 0, -1)),  # 下
)
_FACE_FORWARD = np.array([f for f, _, _ in _CUBE_FACES], dtype=np.float64)
_FACE_RIGHT = np.array([r for _, r, _ in _CUBE_FACES], dtype=np.float64)
_FACE_UP = np.array([u for _, _, u in _CUBE_FACES], dtype=np.float64)

# 方向対応を実装済みのレンズ
SUPPORTED_PANORAMA_TYPES = frozenset({
    "EQUIRECTANGULAR",
    "EQUIANGULAR_CUBEMAP_FACE",
    "MIRRORBALL",
    "FISHEYE_EQUIDISTANT",
    "FISHEYE_EQUISOLID",
    "FISHEYE_LENS_POLYNOMIAL",
    "CENTRAL_CYLINDRICAL",
})


class _PanoramaSettings:
    """パノラマ設定の読み出しを包む。Blender 5.x はカメラ直下、3.x は Cycles 側（camera.cycles）に設定があるため両方を見る。"""

    def __init__(self, camera_data):
        self._data = camera_data

    def has(self, name: str) -> bool:
        if hasattr(self._data, name):
            return True
        cycles = getattr(self._data, "cycles", None)
        return cycles is not None and hasattr(cycles, name)

    def get(self, name: str, default=None):
        return getattr(self, name) if self.has(name) else default

    def __getattr__(self, name):
        data = self._data
        if hasattr(data, name):
            return getattr(data, name)
        cycles = getattr(data, "cycles", None)
        if cycles is not None and hasattr(cycles, name):
            return getattr(cycles, name)
        raise AttributeError(f"camera setting '{name}' is not available")


def _pano_settings(camera_data) -> _PanoramaSettings:
    return camera_data if isinstance(camera_data, _PanoramaSettings) else _PanoramaSettings(camera_data)


# レンズ種別ごとに必要な設定。Blender の版によっては存在しない設定があるため、揃っていない場合は線形描画にフォールバックする
_COMMON_SETTINGS = ("shift_x", "shift_y", "sensor_width", "sensor_height", "sensor_fit", "fisheye_fov")
_REQUIRED_SETTINGS = {
    "EQUIRECTANGULAR": ("longitude_min", "longitude_max", "latitude_min", "latitude_max"),
    "EQUIANGULAR_CUBEMAP_FACE": (),
    "MIRRORBALL": (),
    "FISHEYE_EQUIDISTANT": (),
    "FISHEYE_EQUISOLID": ("fisheye_lens",),
    "FISHEYE_LENS_POLYNOMIAL": ("fisheye_lens", "fisheye_polynomial_k0", "fisheye_polynomial_k1",
                                "fisheye_polynomial_k2", "fisheye_polynomial_k3", "fisheye_polynomial_k4"),
    "CENTRAL_CYLINDRICAL": ("central_cylindrical_range_u_min", "central_cylindrical_range_u_max",
                            "central_cylindrical_range_v_min", "central_cylindrical_range_v_max",
                            "central_cylindrical_radius"),
}
# キャッシュキーに含める数値設定（存在しない場合は 0 として扱う）
_KEY_NUMERIC_SETTINGS = (
    "fisheye_fov", "fisheye_polynomial_k0", "fisheye_polynomial_k1", "fisheye_polynomial_k2",
    "fisheye_polynomial_k3", "fisheye_polynomial_k4", "fisheye_lens",
    "longitude_min", "longitude_max", "latitude_min", "latitude_max",
    "central_cylindrical_range_u_min", "central_cylindrical_range_u_max",
    "central_cylindrical_range_v_min", "central_cylindrical_range_v_max", "central_cylindrical_radius",
    "sensor_width", "sensor_height", "shift_x", "shift_y",
)


def is_nonlinear_camera(camera_data) -> bool:
    return camera_data.type == "PANO"


def is_supported_camera(camera_data) -> bool:
    if not is_nonlinear_camera(camera_data):
        return False
    settings = _pano_settings(camera_data)
    if not settings.has("panorama_type"):
        return False
    panorama_type = settings.panorama_type
    if panorama_type not in SUPPORTED_PANORAMA_TYPES:
        return False
    required = _COMMON_SETTINGS + _REQUIRED_SETTINGS.get(panorama_type, ())
    return all(settings.has(name) for name in required)


def is_lens_line_available_for_renderer(renderer: str, blender_version: tuple) -> bool:
    """非線形レンズのライン描画を行うレンダラーか判定する。EEVEE は Blender 5.3 以降、Cycles は常に対象とする。"""
    if renderer.startswith("BLENDER_EEVEE"):
        return tuple(blender_version) >= (5, 3, 0)
    return renderer == "CYCLES"


def get_face_rotation(face_index: int):
    """面カメラのローカル→カメラ座標の回転行列（mathutils.Matrix）を返す。"""
    from mathutils import Matrix
    forward, right, up = _CUBE_FACES[face_index]
    # ローカルの X, Y, Z 軸（Z は前方の逆向き）を列として並べる
    return Matrix((
        (right[0], up[0], -forward[0], 0.0),
        (right[1], up[1], -forward[1], 0.0),
        (right[2], up[2], -forward[2], 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))


def get_face_projection(clip_start: float, clip_end: float):
    """面カメラの対称透視投影行列（mathutils.Matrix）を返す。"""
    from mathutils import Matrix
    n = clip_start
    f = clip_end
    a = -(f + n) / (f - n)
    b = -2.0 * f * n / (f - n)
    s = 1.0 / FACE_OVERSCAN_TAN
    return Matrix((
        (s, 0.0, 0.0, 0.0),
        (0.0, s, 0.0, 0.0),
        (0.0, 0.0, a, b),
        (0.0, 0.0, -1.0, 0.0),
    ))


def _sensor_extent_mm(camera_data, width: int, height: int):
    """EEVEE と同じ規則で、フレーム全体に対応するセンサーサイズ (mm) を求める。

    EEVEE は「幅/高さ基準のセンサー」を 1 辺にし、もう一辺はフレームのアスペクト比で決める。
    """
    size = camera_data.sensor_height if camera_data.sensor_fit == "VERTICAL" else camera_data.sensor_width
    use_vertical = camera_data.sensor_fit == "VERTICAL" or (
        camera_data.sensor_fit == "AUTO" and width < height)
    if use_vertical:
        return size * width / height, size
    return size, size * height / width


def _pixel_to_direction(camera_data, width: int, height: int):
    """出力画素中心に対応する、カメラローカル（-Z 前方）の視線方向を求める。

    EEVEE の panoramic 投影（eevee_camera_lib の *_to_direction）と同一の式を用いる。
    戻り値は (方向 (H*W, 3), 有効フラグ (H*W,))。
    """
    # 画素中心の uv（0〜1、下が 0）。行 0 は GL テクスチャと同じく画面の下端に対応する。シフトはフレーム uv に加算される
    u = (np.arange(width) + 0.5) / width
    v = (np.arange(height) + 0.5) / height
    uu, vv = np.meshgrid(u, v)
    camera_data = _pano_settings(camera_data)
    uu = uu.ravel() + float(camera_data.shift_x)
    vv = vv.ravel() + float(camera_data.shift_y)

    fov = float(camera_data.fisheye_fov)
    lens = camera_data.panorama_type
    if lens == "EQUIRECTANGULAR":
        # EEVEE と同じく、経度・緯度の範囲を uv に対して線形に割り当てる
        lon_min = float(camera_data.longitude_min)
        lon_max = float(camera_data.longitude_max)
        lat_min = float(camera_data.latitude_min)
        lat_max = float(camera_data.latitude_max)
        phi = uu * (lon_min - lon_max) + (-lon_min + math.pi / 2.0)
        theta = vv * (lat_min - lat_max) + (-lat_min + math.pi / 2.0)
        sin_theta = np.sin(theta)
        direction = np.stack((
            sin_theta * np.cos(phi),
            np.cos(theta),
            -sin_theta * np.sin(phi),
        ), axis=1)
        return direction, np.ones(direction.shape[0], dtype=bool)

    if lens == "EQUIANGULAR_CUBEMAP_FACE":
        tan_u = np.tan((0.5 - uu) * math.pi / 2.0)
        tan_v = np.tan((vv - 0.5) * math.pi / 2.0)
        direction = np.stack((-tan_u, tan_v, -np.ones_like(tan_u)), axis=1)
        direction /= np.linalg.norm(direction, axis=1, keepdims=True)
        return direction, np.ones(direction.shape[0], dtype=bool)

    if lens == "CENTRAL_CYLINDRICAL":
        radius = float(camera_data.central_cylindrical_radius)
        range_x0 = -float(camera_data.central_cylindrical_range_u_min)
        range_x1 = -float(camera_data.central_cylindrical_range_u_max)
        range_y0 = float(camera_data.central_cylindrical_range_v_min) / radius
        range_y1 = float(camera_data.central_cylindrical_range_v_max) / radius
        theta = range_x0 + uu * (range_x1 - range_x0)
        height = range_y0 + vv * (range_y1 - range_y0)
        direction = np.stack((-np.sin(theta), height, -np.cos(theta)), axis=1)
        direction /= np.linalg.norm(direction, axis=1, keepdims=True)
        return direction, np.ones(direction.shape[0], dtype=bool)

    if lens == "MIRRORBALL":
        # 鏡面球の法線から、正面向きの光線を反射して視線方向を得る
        nx = uu * 2.0 - 1.0
        ny = vv * 2.0 - 1.0
        r2 = nx * nx + ny * ny
        valid = r2 <= 1.0
        s = np.sqrt(np.clip(1.0 - r2, 0.0, None))
        direction = np.stack((2.0 * s * nx, 2.0 * s * ny, 1.0 - 2.0 * s * s), axis=1)
        return direction, valid

    if lens == "FISHEYE_EQUIDISTANT":
        # 正規化座標（-1〜1）で θ = r * fov / 2
        nx = (uu - 0.5) * 2.0
        ny = (vv - 0.5) * 2.0
        r = np.hypot(nx, ny)
        theta = r * fov / 2.0
        valid = r <= 1.0
    else:
        # 他のレンズはセンサー上の mm 単位で扱う
        sensor_x, sensor_y = _sensor_extent_mm(camera_data, width, height)
        mx = (uu - 0.5) * sensor_x
        my = (vv - 0.5) * sensor_y
        nx, ny = mx, my
        r = np.hypot(mx, my)
        if lens == "FISHEYE_EQUISOLID":
            # r = 2f * sin(θ / 2)
            lens_mm = float(camera_data.fisheye_lens)
            rmax = 2.0 * lens_mm * math.sin(fov / 4.0)
            valid = r <= rmax
            theta = 2.0 * np.arcsin(np.clip(r / (2.0 * lens_mm), -1.0, 1.0))
        elif lens == "FISHEYE_LENS_POLYNOMIAL":
            # θ = -(k0 + k1 r + k2 r^2 + k3 r^3 + k4 r^4)
            k0 = camera_data.fisheye_polynomial_k0
            k1 = camera_data.fisheye_polynomial_k1
            k2 = camera_data.fisheye_polynomial_k2
            k3 = camera_data.fisheye_polynomial_k3
            k4 = camera_data.fisheye_polynomial_k4
            theta = -(k0 + r * (k1 + r * (k2 + r * (k3 + r * k4))))
            valid = np.abs(theta) <= fov / 2.0
        else:
            raise ValueError(f"未対応のパノラマ投影です: {lens}")

    # 画像中心からの方向（r=0 のときは光軸）
    safe_r = np.where(r > 0.0, r, 1.0)
    cos_phi = np.where(r > 0.0, nx / safe_r, 1.0)
    sin_phi = np.where(r > 0.0, ny / safe_r, 0.0)
    sin_theta = np.sin(theta)
    direction = np.stack((
        sin_theta * cos_phi,
        sin_theta * sin_phi,
        -np.cos(theta),
    ), axis=1)
    return direction, valid


@dataclass(frozen=True)
class LensLut:
    """出力画素ごとの、面画像からのバイリニア参照情報。"""
    indices: np.ndarray    # (H*W, 4) int64、面画像のフラットインデックス
    weights: np.ndarray    # (H*W, 4) float32
    valid: np.ndarray      # (H*W,) bool、レンズの有効範囲内か
    atlas_base: np.ndarray # (H*W, 2) float32、面を 3x2 に並べたアトラス上の左上の参照位置
    frac: np.ndarray       # (H*W, 2) float32、バイリニア補間の小数部（x, y）


def build_lens_lut(camera_data, width: int, height: int, face_size: int) -> LensLut:
    direction, valid = _pixel_to_direction(camera_data, width, height)

    # 方向を最も正面に近い面に割り当てる
    dots = direction @ _FACE_FORWARD.T
    face = np.argmax(dots, axis=1)
    depth = dots[np.arange(len(face)), face]
    local_x = np.sum(direction * _FACE_RIGHT[face], axis=1)
    local_y = np.sum(direction * _FACE_UP[face], axis=1)

    # 面内の正規化座標（-1〜1）を、画素中心基準の連続座標へ変換する
    u = local_x / (depth * FACE_OVERSCAN_TAN)
    v = local_y / (depth * FACE_OVERSCAN_TAN)
    fx = np.clip((u + 1.0) / 2.0 * face_size - 0.5, 0.0, face_size - 1.0)
    # 面の画像も行 0 が下端（GL 規則）
    fy = np.clip((v + 1.0) / 2.0 * face_size - 0.5, 0.0, face_size - 1.0)

    x0 = np.floor(fx).astype(np.int64)
    y0 = np.floor(fy).astype(np.int64)
    x1 = np.minimum(x0 + 1, face_size - 1)
    y1 = np.minimum(y0 + 1, face_size - 1)
    tx = (fx - x0).astype(np.float32)
    ty = (fy - y0).astype(np.float32)

    base = face.astype(np.int64) * face_size * face_size
    indices = np.stack((
        base + y0 * face_size + x0,
        base + y0 * face_size + x1,
        base + y1 * face_size + x0,
        base + y1 * face_size + x1,
    ), axis=1)
    weights = np.stack((
        (1.0 - ty) * (1.0 - tx),
        (1.0 - ty) * tx,
        ty * (1.0 - tx),
        ty * tx,
    ), axis=1).astype(np.float32)
    # 面 k はアトラスの (列 k%3, 行 k//3) に配置する
    atlas_x = ((face % 3) * face_size + x0).astype(np.float32)
    atlas_y = ((face // 3) * face_size + y0).astype(np.float32)
    atlas_base = np.stack((atlas_x, atlas_y), axis=1)
    frac = np.stack((tx, ty), axis=1).astype(np.float32)
    return LensLut(indices=indices, weights=weights, valid=valid, atlas_base=atlas_base, frac=frac)


_lut_cache_key = None
_lut_cache_value = None


def get_lens_lut(camera_data, width: int, height: int, face_size: int) -> LensLut:
    # 直前の 1 件だけ保持し、メモリ使用量を抑える
    global _lut_cache_key, _lut_cache_value
    camera_data = _pano_settings(camera_data)
    key = (
        camera_data.get("panorama_type", ""),
        tuple(float(camera_data.get(name, 0.0)) for name in _KEY_NUMERIC_SETTINGS),
        camera_data.sensor_fit,
        width,
        height,
        face_size,
    )
    if key != _lut_cache_key:
        _lut_cache_value = build_lens_lut(camera_data, width, height, face_size)
        _lut_cache_key = key
    return _lut_cache_value


def build_lut_texture_data(lut: LensLut) -> np.ndarray:
    """GPU 用の LUT データを返す。画素ごとの RGBA は (アトラス上の x, y, 補間 x, 補間 y)。無効画素は x を -1 にする。"""
    data = np.empty((lut.atlas_base.shape[0], 4), dtype=np.float32)
    data[:, 0:2] = lut.atlas_base
    data[:, 2:4] = lut.frac
    data[~lut.valid, 0] = -1.0
    return data.reshape(-1)


def remap_begin(lut: LensLut) -> np.ndarray:
    """面単位のリマップ用に、出力画像分の累積バッファ (H*W, 4) を用意する。"""
    return np.zeros((lut.indices.shape[0], 4), dtype=np.float32)


def remap_accumulate_face(out: np.ndarray, face: np.ndarray, lut: LensLut, face_index: int) -> None:
    """1 面の RGBA 画像 (N, N, 4) のうち、LUT が参照する画素の寄与だけを out に加算する。

    全面を同時に保持せず、面を 1 枚ずつ渡して順に呼び出す。
    """
    face_pixels = face.shape[0] * face.shape[1]
    flat = face.reshape(-1, 4)
    base = face_index * face_pixels
    for corner in range(4):
        index = lut.indices[:, corner]
        mask = (index >= base) & (index < base + face_pixels)
        out[mask] += flat[index[mask] - base] * lut.weights[mask, corner, None]


def remap_finish(out: np.ndarray, lut: LensLut) -> np.ndarray:
    """累積結果のうち無効画素を 0 にし、出力画像の RGBA フラット配列を返す。"""
    out[~lut.valid] = 0.0
    return out.reshape(-1)
