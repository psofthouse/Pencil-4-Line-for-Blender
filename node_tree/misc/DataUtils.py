# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

from typing import Iterable
import bpy

class ObjectElement(bpy.types.PropertyGroup):
    content: bpy.props.PointerProperty(type=bpy.types.Object)


class MaterialElement(bpy.types.PropertyGroup):
    content: bpy.props.PointerProperty(type=bpy.types.Material)


def collection_element_type(data, property:str):
    return data.__class__.bl_rna.properties[property].fixed_type

def collection_content_type(data, property:str):
    for prop in collection_element_type(data, property).bl_rna.properties:
        if prop.name == "content" and prop.type == "POINTER":
            return prop.fixed_type



line_object_types = frozenset({"MESH", "SURFACE", "META", "CURVE", "FONT"})

def collect_objects_in_data():
    return [x for x in bpy.data.objects if x.type in line_object_types]


def collect_objects_in_scene(scene:bpy.types.Scene):
    return set(x for x in list(scene.objects) if x.type in line_object_types)

def collect_objects_in_scenes():
    objects = set()
    for scene in bpy.data.scenes:
        objects |= collect_objects_in_scene(scene)
    return objects

def collect_materials_in_objects(objects:Iterable[bpy.types.Object]):
    materials = set()
    for object in objects:
        materials |= set(ms.material for ms in object.material_slots if ms.material is not None)
    return materials


def append_collection_element(data, property:str, items:Iterable[bpy.types.ID]):
    value = getattr(data, property)
    for item in items:
        value.add().content = item

def replace_collection_element(data, property:str, replace_dict:dict[bpy.types.ID, bpy.types.ID]):
    value = getattr(data, property)
    for elem in value:
        elem.content = replace_dict.get(elem.content, elem.content)

def remove_collection_element_included_in_items(data, property:str, items:Iterable[bpy.types.ID]):
    value = getattr(data, property)
    remove_indices = [i for i, x in enumerate(value) if x.content in items]

    offset = 0
    for i in remove_indices:
        value.remove(i - offset)
        offset += 1

def remove_none_or_duplicated_collection_element(data, property:str):
    value = getattr(data, property)
    remove_indices = []
    contents = set()
    for i, x in enumerate(value):
        if x.content is None or x.content in contents:
            remove_indices.append(i)
        else:
            contents.add(x.content)

    offset = 0
    for i in remove_indices:
        value.remove(i - offset)
        offset += 1


def remove_collection_element_not_included_in_items(data, property:str, items:Iterable[bpy.types.ID]):
    remove_collection_element_included_in_items(data, property, set(x for x in enumerate_ids_from_collection(data, property) if not x in items))


def enumerate_ids_from_collection(data, property:str):
    value = getattr(data, property)
    ids = []    
    listed_set = set()
    for x in (x.content for x in value if x.content not in listed_set and x.content is not None):
        listed_set.add(x)
        ids.append(x)
    return ids