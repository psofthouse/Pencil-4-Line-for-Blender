# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import math
from time import perf_counter_ns
from ..node_tree.misc.AttrOverride import get_overrided_attr

# プロパティ種別 (cpp/py のクラスごとに事前分類してキャッシュする)
_KIND_MISSING           = 0   # py_instance に該当プロパティが存在しない
_KIND_PRIMITIVE         = 1
_KIND_PRIMITIVE_ANGLE   = 2
_KIND_PRIMITIVE_PERCENT = 3
_KIND_ENUM              = 4
_KIND_VECTOR            = 5
_KIND_CURVE             = 6
_KIND_SOCKET            = 7
_KIND_SOCKET_MULTI      = 8
_KIND_STRING            = 9
_KIND_OBJECT            = 10
_KIND_COLLECTION        = 11
_KIND_IMAGE             = 12
_KIND_NONE              = 13  # ポインタ系で値が無い等、常にスキップ
_KIND_UNKNOWN           = 14  # 転送条件漏れ

# (type(py_instance), type(cpp_instance)) -> list[(prop_name, kind, extra)]
_PROP_CACHE = {}


# ---- kind 別プロファイラ -------------------------------------------------
# copy_props のループ内で、どの kind に時間が掛かっているかを計測するための仕組み。
# 通常運用では _PROFILE_ENABLED = False のままにする (計測コードを通らない)。
# 使い方:
#   from psoft_pencil4_line.misc import cpp_utils
#   cpp_utils.profile_reset()
#   cpp_utils.profile_enable(True)
#   ... 計測したい処理 (レンダー等) を実行 ...
#   cpp_utils.profile_enable(False)
#   cpp_utils.profile_report()

_PROFILE_ENABLED = False

_KIND_NAMES = {
    _KIND_PRIMITIVE:         "PRIMITIVE",
    _KIND_PRIMITIVE_ANGLE:   "PRIMITIVE_ANGLE",
    _KIND_PRIMITIVE_PERCENT: "PRIMITIVE_PERCENT",
    _KIND_ENUM:              "ENUM",
    _KIND_VECTOR:            "VECTOR",
    _KIND_CURVE:             "CURVE",
    _KIND_SOCKET:            "SOCKET",
    _KIND_SOCKET_MULTI:      "SOCKET_MULTI",
    _KIND_STRING:            "STRING",
    _KIND_OBJECT:            "OBJECT",
    _KIND_COLLECTION:        "COLLECTION",
    _KIND_IMAGE:             "IMAGE",
}

# {kind: [count, total_ns]}
_PROFILE_STATS = {k: [0, 0] for k in _KIND_NAMES}
# [count, total_ns] : py_value 取得 (get_overrided_attr / getattr) のコスト
_PROFILE_GETVAL = [0, 0]


def profile_enable(enabled: bool):
    global _PROFILE_ENABLED
    _PROFILE_ENABLED = bool(enabled)


def profile_reset():
    for v in _PROFILE_STATS.values():
        v[0] = 0
        v[1] = 0
    _PROFILE_GETVAL[0] = 0
    _PROFILE_GETVAL[1] = 0


def profile_report():
    print(f"{'kind':<20} {'calls':>10} {'total_ms':>12} {'avg_us':>10}")
    rows = []
    for k, (n, t) in _PROFILE_STATS.items():
        if n == 0:
            continue
        rows.append((_KIND_NAMES[k], n, t / 1e6, (t / n) / 1e3))
    for name, n, t_ms, avg_us in sorted(rows, key=lambda r: -r[2]):
        print(f"{name:<20} {n:>10} {t_ms:>12.3f} {avg_us:>10.3f}")
    n, t = _PROFILE_GETVAL
    if n:
        print(f"{'(get py_value)':<20} {n:>10} {t/1e6:>12.3f} {(t/n)/1e3:>10.3f}")
# -------------------------------------------------------------------------


def build_links_map(node_trees):
    """ノードツリー群のリンクを (to_socket -> 接続先 node) の辞書に展開する。

    PencilSocketMixin.get_connected_node(ignore_muted_link=True) と同等の解決を
    行い、Reroute も解決して最終的な接続先ノードを返す。copy_props に links_map
    として渡すと、SOCKET / SOCKET_MULTI 分岐内の socket.links 参照
    (Blender 内部で全リンク走査になる) を回避できる。

    引数 node_trees はノードツリーの iterable。
    """
    m = {}
    decided = set()
    for tree in node_trees:
        for link in tree.links:
            to_sock = link.to_socket
            if to_sock in decided:
                continue
            if link.is_muted:
                continue
            decided.add(to_sock)
            cur = link
            node = cur.from_socket.node
            ok = True
            while isinstance(node, bpy.types.NodeReroute):
                ins = node.inputs[0]
                if not ins.is_linked or cur.is_muted:
                    ok = False
                    break
                cur = ins.links[0]
                node = cur.from_socket.node
            if ok:
                m[to_sock] = node
    return m


def _pointer_fixed_identifier(py_prop):
    fixed = getattr(py_prop, "fixed_type", None)
    if fixed is None:
        return None
    ident = getattr(fixed, "identifier", None)
    if ident is not None:
        return ident
    bl_rna = getattr(fixed, "bl_rna", None)
    return getattr(bl_rna, "identifier", None)


def _classify_prop(prop_name, py_instance, cpp_instance, py_rna_props):
    if not hasattr(py_instance, prop_name):
        return (_KIND_MISSING, None)

    cpp_value = getattr(cpp_instance, prop_name)
    cpp_type = type(cpp_value)
    py_prop = py_rna_props.get(prop_name)

    if cpp_type in (bool, int, float):
        subtype = py_prop.subtype if py_prop is not None else "NONE"
        if subtype == "ANGLE":
            return (_KIND_PRIMITIVE_ANGLE, None)
        if subtype == "PERCENTAGE":
            return (_KIND_PRIMITIVE_PERCENT, None)
        return (_KIND_PRIMITIVE, None)

    if cpp_type.__name__.startswith("pcl4_enum_"):
        id_to_value = {item.identifier: item.value for item in py_prop.enum_items}
        return (_KIND_ENUM, (cpp_type, id_to_value))

    if cpp_type is str:
        return (_KIND_STRING, None)

    if cpp_type is list:
        if py_prop is None:
            return (_KIND_UNKNOWN, None)
        ptype = py_prop.type
        if ptype == "COLLECTION":
            return (_KIND_COLLECTION, None)
        if ptype == "STRING":
            if len(cpp_value) > 1 and "curve" in prop_name:
                return (_KIND_CURVE, len(cpp_value))
            return (_KIND_SOCKET_MULTI, py_prop.default)
        if getattr(py_prop, "is_array", False) and py_prop.array_length == len(cpp_value):
            return (_KIND_VECTOR, None)
        return (_KIND_UNKNOWN, None)

    if cpp_type is type(None):
        if py_prop is None:
            return (_KIND_NONE, None)
        ptype = py_prop.type
        if ptype == "STRING":
            return (_KIND_SOCKET, py_prop.default)
        if ptype == "POINTER":
            ident = _pointer_fixed_identifier(py_prop)
            if ident == "Object":
                return (_KIND_OBJECT, None)
            if ident == "Image":
                return (_KIND_IMAGE, None)
        return (_KIND_NONE, None)

    return (_KIND_UNKNOWN, None)


def _build_prop_cache(py_instance, cpp_instance):
    py_rna_props = py_instance.bl_rna.properties
    entries = []
    for prop_name in dir(cpp_instance):
        if prop_name.startswith("_"):
            continue
        kind, extra = _classify_prop(prop_name, py_instance, cpp_instance, py_rna_props)
        if kind == _KIND_MISSING:
            # 該当するプロパティがPython側に存在しない (このコードパスを通るのは基本的に不具合である)
            print(f"Not transferred: {py_instance.name}.{prop_name} - Property not found.")
            continue
        if kind == _KIND_NONE:
            continue
        if kind == _KIND_UNKNOWN:
            # プロパティの転送条件漏れ (このコードパスを通るのは基本的に不具合である)
            py_type = type(getattr(py_instance, prop_name))
            cpp_type = type(getattr(cpp_instance, prop_name))
            print(f"Not transferred: {prop_name} - py:{py_type} -> cpp:{cpp_type}")
            continue
        entries.append((prop_name, kind, extra))
    return entries


def copy_props(py_instance, cpp_instance, instance_dict=None, context: bpy.types.Context=None, depsgraph: bpy.types.Depsgraph=None, links_map=None):
    cache_key = (type(py_instance), type(cpp_instance))
    entries = _PROP_CACHE.get(cache_key)
    if entries is None:
        entries = _build_prop_cache(py_instance, cpp_instance)
        _PROP_CACHE[cache_key] = entries

    use_override = context is not None or depsgraph is not None

    if _PROFILE_ENABLED:
        _copy_props_profiled(py_instance, cpp_instance, instance_dict, context, depsgraph, entries, use_override, links_map)
        return

    for prop_name, kind, extra in entries:
        if use_override:
            py_value = get_overrided_attr(py_instance, prop_name, context=context, depsgraph=depsgraph)
        else:
            py_value = getattr(py_instance, prop_name)

        if kind == _KIND_PRIMITIVE:
            setattr(cpp_instance, prop_name, py_value)
        elif kind == _KIND_PRIMITIVE_ANGLE:
            setattr(cpp_instance, prop_name, math.degrees(py_value))
        elif kind == _KIND_PRIMITIVE_PERCENT:
            setattr(cpp_instance, prop_name, py_value * 0.01)
        elif kind == _KIND_ENUM:
            cpp_type, id_to_value = extra
            setattr(cpp_instance, prop_name, cpp_type(id_to_value[py_value]))
        elif kind == _KIND_VECTOR:
            setattr(cpp_instance, prop_name, py_value)
        elif kind == _KIND_CURVE:
            setattr(cpp_instance, prop_name, py_instance.evaluate_curve(py_value, extra))
        elif kind == _KIND_SOCKET:
            default_socket = extra
            if use_override:
                py_value = py_instance.filtered_socket_id(default_socket, context=context, depsgraph=depsgraph)
            if links_map is not None:
                child_node = next((links_map.get(x) for x in py_instance.inputs if x.identifier == py_value), None)
            else:
                child_node = next((x.get_connected_node(ignore_muted_link=True) for x in py_instance.inputs if x.identifier == py_value), None)
            if instance_dict is not None and child_node is not None and child_node in instance_dict:
                setattr(cpp_instance, prop_name, instance_dict[child_node])
        elif kind == _KIND_SOCKET_MULTI:
            default_socket = extra
            if use_override:
                py_value = py_instance.filtered_socket_id(default_socket, context=context, depsgraph=depsgraph)
            if instance_dict is not None:
                cpp_value = getattr(cpp_instance, prop_name)
                for x in py_instance.inputs:
                    if not x.identifier.startswith(py_value):
                        continue
                    n = links_map.get(x) if links_map is not None else x.get_connected_node(ignore_muted_link=True)
                    if n is None or n not in instance_dict:
                        continue
                    cpp_value.append(instance_dict[n])
                setattr(cpp_instance, prop_name, cpp_value)
        elif kind == _KIND_STRING:
            setattr(cpp_instance, prop_name, py_value)
        elif kind == _KIND_OBJECT:
            if py_value is not None and depsgraph is not None:
                eval_object = next((x.object for x in depsgraph.object_instances if x.object.original.override_library is not None and x.object.original.override_library.reference == py_value), depsgraph.id_eval_get(py_value))
                if eval_object is not None:
                    py_value = eval_object
            setattr(cpp_instance, prop_name, py_value)
        elif kind == _KIND_COLLECTION:
            cpp_value = getattr(cpp_instance, prop_name)
            for o in py_value:
                cpp_value.append(o.content)
            setattr(cpp_instance, prop_name, cpp_value)
        elif kind == _KIND_IMAGE:
            setattr(cpp_instance, prop_name, py_value)


def _copy_props_profiled(py_instance, cpp_instance, instance_dict, context, depsgraph, entries, use_override, links_map):
    for prop_name, kind, extra in entries:
        t0 = perf_counter_ns()
        if use_override:
            py_value = get_overrided_attr(py_instance, prop_name, context=context, depsgraph=depsgraph)
        else:
            py_value = getattr(py_instance, prop_name)
        t1 = perf_counter_ns()
        _PROFILE_GETVAL[0] += 1
        _PROFILE_GETVAL[1] += t1 - t0

        if kind == _KIND_PRIMITIVE:
            setattr(cpp_instance, prop_name, py_value)
        elif kind == _KIND_PRIMITIVE_ANGLE:
            setattr(cpp_instance, prop_name, math.degrees(py_value))
        elif kind == _KIND_PRIMITIVE_PERCENT:
            setattr(cpp_instance, prop_name, py_value * 0.01)
        elif kind == _KIND_ENUM:
            cpp_type, id_to_value = extra
            setattr(cpp_instance, prop_name, cpp_type(id_to_value[py_value]))
        elif kind == _KIND_VECTOR:
            setattr(cpp_instance, prop_name, py_value)
        elif kind == _KIND_CURVE:
            setattr(cpp_instance, prop_name, py_instance.evaluate_curve(py_value, extra))
        elif kind == _KIND_SOCKET:
            default_socket = extra
            if use_override:
                py_value = py_instance.filtered_socket_id(default_socket, context=context, depsgraph=depsgraph)
            if links_map is not None:
                child_node = next((links_map.get(x) for x in py_instance.inputs if x.identifier == py_value), None)
            else:
                child_node = next((x.get_connected_node(ignore_muted_link=True) for x in py_instance.inputs if x.identifier == py_value), None)
            if instance_dict is not None and child_node is not None and child_node in instance_dict:
                setattr(cpp_instance, prop_name, instance_dict[child_node])
        elif kind == _KIND_SOCKET_MULTI:
            default_socket = extra
            if use_override:
                py_value = py_instance.filtered_socket_id(default_socket, context=context, depsgraph=depsgraph)
            if instance_dict is not None:
                cpp_value = getattr(cpp_instance, prop_name)
                for x in py_instance.inputs:
                    if not x.identifier.startswith(py_value):
                        continue
                    n = links_map.get(x) if links_map is not None else x.get_connected_node(ignore_muted_link=True)
                    if n is None or n not in instance_dict:
                        continue
                    cpp_value.append(instance_dict[n])
                setattr(cpp_instance, prop_name, cpp_value)
        elif kind == _KIND_STRING:
            setattr(cpp_instance, prop_name, py_value)
        elif kind == _KIND_OBJECT:
            if py_value is not None and depsgraph is not None:
                eval_object = next((x.object for x in depsgraph.object_instances if x.object.original.override_library is not None and x.object.original.override_library.reference == py_value), depsgraph.id_eval_get(py_value))
                if eval_object is not None:
                    py_value = eval_object
            setattr(cpp_instance, prop_name, py_value)
        elif kind == _KIND_COLLECTION:
            cpp_value = getattr(cpp_instance, prop_name)
            for o in py_value:
                cpp_value.append(o.content)
            setattr(cpp_instance, prop_name, cpp_value)
        elif kind == _KIND_IMAGE:
            setattr(cpp_instance, prop_name, py_value)

        t2 = perf_counter_ns()
        stat = _PROFILE_STATS[kind]
        stat[0] += 1
        stat[1] += t2 - t1    