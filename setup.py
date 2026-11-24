"""Builds the vsg._framedecoder pybind11 extension against system FFmpeg (via pkg-config)."""

import shlex
import subprocess

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import find_packages, setup

FFMPEG_LIBS = ["libavformat", "libavcodec", "libavutil", "libswscale"]


def pkg_config(flag):
    out = subprocess.check_output(["pkg-config", flag, *FFMPEG_LIBS], text=True)
    return shlex.split(out)


ext = Pybind11Extension(
    "vsg._framedecoder",
    ["csrc/frame_decoder.cpp"],
    cxx_std=17,
    extra_compile_args=pkg_config("--cflags") + ["-O3"],
    extra_link_args=pkg_config("--libs"),
)

setup(
    name="video-scene-graph",
    version="0.1.0",
    packages=find_packages(),
    ext_modules=[ext],
    cmdclass={"build_ext": build_ext},
)
