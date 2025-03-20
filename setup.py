from setuptools import setup, Extension
import os
import sys
from configparser import ConfigParser

# Load build configurations
config = ConfigParser()
config.read("setup.cfg")

include_dirs = config.get("build_ext", "include_dirs").split(":")
libraries = config.get("build_ext", "libraries").split()

# INDI Client Extension
ext_module = Extension(
    name="_PyIndi",
    sources=["indiclientpython_wrap.cxx"],
    include_dirs=include_dirs,
    libraries=libraries,
    library_dirs=["/usr/lib", "/usr/lib64", "/lib", "/lib64"],
    extra_compile_args=["-fPIC"],
    extra_link_args=["-shared"],
)

setup(
    name="indy-client",
    version="0.1.0",
    packages=["."],
    zip_safe=False,
    ext_modules=[ext_module],
    py_modules=["PyIndi"],
)
