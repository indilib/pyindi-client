"""Setup file for packaging pyindi-client"""

from os.path import join, dirname, abspath, isfile
from sys import exit

try:
    from distutils.command.build import build
    from setuptools.command.install import install
    from setuptools import setup, Extension
except:
    from distutils.command.build import build
    from distutils.command.install import install
    from distutils import setup, Extension

march = ""
try:
    import sysconfig

    march = sysconfig.get_config_var("MULTIARCH")
except:
    import sys

    march = getattr(sys, "implementation", sys)._multiarch

###

VERSION = "v1.9.1"
root_dir = abspath(dirname(__file__))

# Add search paths here for libindiclient.a
libindisearchpaths = [
    "/usr/lib/" + march,
    "/usr/lib",
    "/usr/lib64",
    "/lib",
    "/lib64",
    "/usr/local/lib/" + march,
    "/usr/local/lib",
]

libindipath = ""

for lindipath in libindisearchpaths:
    if isfile(join(lindipath, "libindiclient.a")):
        libindipath = lindipath
        break

if libindipath == "":
    print("Unable to find libindiclient.a in " + str(libindisearchpaths))
    print("Please specify a path where to find libindiclient.a in the setup.py script")
    print("Exiting")
    exit(1)

pyindi_module = Extension(
    "_PyIndi",
    sources=["indiclientpython.i"],
    language="c++",
    extra_compile_args=["-std=c++11"],
    extra_objects=[join(libindipath, "libindiclient.a")],
)

# Be sure to run build_ext in order to run swig prior to install/build
# see http://stackoverflow.com/questions/12491328/python-distutils-not-include-the-swig-generated-module
class CustomBuild(build):
    def run(self):
        self.run_command("build_ext")
        build.run(self)


class CustomInstall(install):
    def run(self):
        self.run_command("build_ext")
        install.run(self)


# readme = open(join(root_dir, 'README.rst'))
descr = """
An INDI Client Python API, auto-generated from the official C++ API using SWIG.

Installation

Use pip (recommended): pip install pyindi-client

Alternatively download a release, extract it and run: python setup.py install

The file setup.cfg contains configuration options (mainly concerning libindi installation path).
The file setup.py searchs for the libindiclient.a library in some predefined directories.
If not found, the script fails. Locate this library (try locate lindiclient.a from the command line)
and add its path to the libindisearchpaths variable in the setup script.

Dependencies

For the above installation to work, you need to have installed from your distribution repositories the following packages: Python setup tools, Python development files, libindi development files and swig.
- On an Ubuntu-like distribution, you may use:
apt-get install python-setuptools python-dev libindi-dev swig
- On a Fedora-like distribution, you may use (dnf or yum):
dnf install python-setuptools python-devel libindi-devel swig
"""
setup(
    version=VERSION,
    name="pyindi-client",
    author="geehalel",
    author_email="geehalel@gmail.com",
    url="https://github.com/indilib/pyindi-client",
    license="GNU General Public License v3 or later (GPLv3+)",
    description="""Third party Python API for INDI client""",
    # long_description=readme.read(),
    long_description=descr,
    keywords=["libindi client wrapper"],
    cmdclass={"build": CustomBuild, "install": CustomInstall},
    ext_modules=[pyindi_module],
    py_modules=["PyIndi"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Development Status :: 3 - Alpha",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: Unix",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Astronomy",
    ],
)
# readme.close()
