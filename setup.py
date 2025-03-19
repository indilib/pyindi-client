from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import os

class CustomBuildExt(build_ext):
    def run(self):
        # Run SWIG to generate PyIndi.py and indiclientpython_wrap.cpp
        self.announce("Running SWIG...", level=2)
        os.system("swig -python -v -Wall -c++ -threads -I/usr/include -I/usr/include/libindi -I/usr/local/include/libindi -o indiclientpython_wrap.cpp indiclientpython.i")
        
        # Continue with the regular build_ext process
        build_ext.run(self)

# Define the extension module
ext_module = Extension(
    name="_PyIndi",
    sources=["indiclientpython_wrap.cpp"],
    include_dirs=["/usr/include", "/usr/include/libindi", "/usr/local/include/libindi"],
    libraries=["z", "cfitsio", "nova", "indiclient"],
    language="c++",
)

# This setup function will be called by setuptools.build_meta
setup(
    ext_modules=[ext_module],
    py_modules=["PyIndi"],
    cmdclass={"build_ext": CustomBuildExt},
)
