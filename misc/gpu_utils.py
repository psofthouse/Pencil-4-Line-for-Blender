# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

from typing import Tuple
from typing import Iterable
import gpu

def __type_to_str(type:str) -> str:
    if type == "FLOAT_2D":
        return "sampler2D"
    else:
        return type.lower()


class ShaderParameters:
    def __init__(self):
        self.__vert_inputs = []
        self.__vert_outputs = []
        self.__frag_outputs = []
        self.__constants = []
        self.__samplers = []
        
    @property
    def vert_inputs(self) -> Iterable[Tuple[str, str]]:
        return self.__vert_inputs

    @property
    def vert_outputs(self) -> Iterable[Tuple[str, str]]:
        return self.__vert_outputs
    
    @property
    def frag_outputs(self) -> Iterable[Tuple[str, str]]:
        return self.__frag_outputs
    
    @property
    def constants(self) -> Iterable[Tuple[str, str]]:
        return self.__constants
    
    @property
    def samplers(self) -> Iterable[Tuple[str, str]]:
        return self.__samplers
    
    def add_vert_input(self, type:str, name:str):
        self.__vert_inputs.append((type, name))
    
    def add_vert_output(self, type:str, name:str):
        self.__vert_outputs.append((type, name))

    def add_frag_output(self, type:str, name:str):
        self.__frag_outputs.append((type, name))

    def add_constant(self, type:str, name:str):
        self.__constants.append((type, name))

    def add_sampler(self, type:str, name:str):
        self.__samplers.append((type, name))


def create_shader(vertex_source:str, fragment_source:str, params:ShaderParameters ) -> gpu.types.GPUShader:
        if hasattr(gpu.types, "GPUShaderCreateInfo"):
            shader_info = gpu.types.GPUShaderCreateInfo()
            if len(params.vert_outputs) > 0:
                vert_out  = gpu.types.GPUStageInterfaceInfo("my_interface")
                for type, name in params.vert_outputs:
                    vert_out.smooth(type, name)
                shader_info.vertex_out(vert_out)
            for type, name in params.constants:
                shader_info.push_constant(type, name)
            for i, (type, name) in enumerate(params.samplers):
                shader_info.sampler(i, type, name)
            for i, (type, name) in enumerate(params.vert_inputs):
                shader_info.vertex_in(i, type, name)
            for i, (type, name) in enumerate(params.frag_outputs):
                shader_info.fragment_out(i, type, name)
            shader_info.vertex_source(vertex_source)
            shader_info.fragment_source(fragment_source)
            shader = gpu.shader.create_from_info(shader_info)
            if len(params.vert_outputs) > 0:
                del vert_out
            del shader_info
            return shader
        else:
            vertex_prefix = ""
            fragmetn_prefix = ""
            for type, name in params.constants:
                str = f"uniform {__type_to_str(type)} {name};\n"
                vertex_prefix += str
                fragmetn_prefix += str
            for type, name in params.vert_outputs:
                vertex_prefix += f"out {__type_to_str(type)} {name};\n"
                fragmetn_prefix += f"in {__type_to_str(type)} {name};\n"
            for type, name in params.samplers:
                fragmetn_prefix += f"uniform {__type_to_str(type)} {name};\n"
            for type, name in params.vert_inputs:
                vertex_prefix += f"in {__type_to_str(type)} {name};\n"
            for type, name in params.frag_outputs:
                fragmetn_prefix += f"out {__type_to_str(type)} {name};\n"
            shader = gpu.types.GPUShader(vertex_prefix + vertex_source, fragmetn_prefix + fragment_source)
            return shader