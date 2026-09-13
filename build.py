from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


# This file describes how to build this project.
# build_api.py contains the reusable compiler/linker machinery.
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import build_api

build_api.set_project_root(PROJECT_ROOT)


PROJECT_NAME = "Lattice Notes"
APPLICATION_OUTPUT = "build/LatticeNotes.exe"

P1UI_SOURCES = [
    "p1ui/P1UI.cpp",
    "p1ui/P1UI_Renderer.cpp",
    "p1ui/P1UI_Media.cpp",
    "p1ui/P1UI_State.cpp",
    "p1ui/P1UI_Composition.cpp",
    "p1ui/P1UI_DataEditing.cpp",
    "p1ui/P1UI_AppFoundation.cpp",
    "p1ui/P1UI_Production.cpp",
]

ENGINE_SOURCES = [
    "engine/Engine.cpp",
    "engine_extensions/Engine_Extensions_win32.cpp",
    "engine_extensions/FontRasterizer_win32.cpp",
]

LATTICE_SOURCES = [
    "src/lattice_notes/LatticeNotesPersistence.cpp",
    "src/lattice_notes/LatticeNotesPanelBaker.cpp",
    "src/lattice_notes/LatticeNotesRenderer.cpp",
    "src/lattice_notes/LatticeNotesAudio.cpp",
    "src/lattice_notes/LatticeNotesUI.cpp",
    "src/lattice_notes/dev_review/DevReview.cpp",
    "src/lattice_notes/dev_review/DevReviewUI.cpp",
    "src/lattice_notes/LatticeNotesApp.cpp",
    "src/lattice_notes/main.cpp",
]

LATTICE_TEST_SOURCES = [
    "src/lattice_notes/LatticeNotesPersistence.cpp",
    "src/lattice_notes/LatticeNotesPanelBaker.cpp",
    "src/lattice_notes/dev_review/DevReview.cpp",
    "tests/LatticeNotes_Tests.cpp",
]

LATTICE_UI_TEST_SOURCES = [
    "src/lattice_notes/LatticeNotesUI.cpp",
    "src/lattice_notes/LatticeNotesPersistence.cpp",
    "src/lattice_notes/LatticeNotesPanelBaker.cpp",
    "src/lattice_notes/dev_review/DevReview.cpp",
    "src/lattice_notes/dev_review/DevReviewUI.cpp",
    "tests/LatticeNotes_UI_Tests.cpp",
]

PORTABLE_P1UI_CORE = [
    "p1ui/P1UI.cpp",
    "p1ui/P1UI_State.cpp",
    "p1ui/P1UI_Composition.cpp",
    "p1ui/P1UI_DataEditing.cpp",
    "p1ui/P1UI_AppFoundation.cpp",
    "p1ui/P1UI_Production.cpp",
]

WIN32_LIBRARIES = [
    "opengl32",
    "gdi32",
    "user32",
    "shell32",
    "comdlg32",
    "winmm",
    "ole32",
]

INCLUDE_DIRECTORIES = [
    ".",
    "p1ui",
    "engine",
    "src/lattice_notes",
    "YOU_CAN_USE_TO_NOT_REINVENT_THE_WHEEL",
]

REQUIRED_FILES = [
    "engine/Engine.h",
    "engine/Engine.cpp",
    "engine/Engine_internal_win32_opengl.h",
    "engine_extensions/Engine_Extensions.h",
    "engine_extensions/Engine_Extensions_win32.cpp",
    "engine_extensions/FontRasterizer_win32.cpp",
    "p1ui/P1UI.h",
    *P1UI_SOURCES,
    *LATTICE_SOURCES,
    "src/lattice_notes/LatticeNotesApp.h",
    "src/lattice_notes/LatticeNotesTextInput.h",
    "src/lattice_notes/LatticeNotesModel.h",
    "src/lattice_notes/dev_review/DevReview.h",
    "src/lattice_notes/dev_review/DevReviewUI.h",
    "YOU_CAN_USE_TO_NOT_REINVENT_THE_WHEEL/stb/image/stb_image.h",
    "YOU_CAN_USE_TO_NOT_REINVENT_THE_WHEEL/stb/image/stb_image_write.h",
    "YOU_CAN_USE_TO_NOT_REINVENT_THE_WHEEL/nlohmann/json.h",
    "tests/LatticeNotes_Tests.cpp",
    "tests/LatticeNotes_UI_Tests.cpp",
    "tests/engine_manifest.sha256",
    "tests/validate_lattice_contracts.py",
]


@dataclass(frozen=True)
class BuildOptions:
    clean: bool
    debug: bool
    show_warnings: bool
    run_after_build: bool
    build_tests: bool


def read_command_line(arguments: Sequence[str]) -> BuildOptions:
    parser = argparse.ArgumentParser(
        description=f"Build {PROJECT_NAME}.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove build/ before building. Normally unnecessary because builds are incremental.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Build with debug information and debug-friendly optimization.",
    )
    parser.add_argument(
        "--show-warnings",
        action="store_true",
        help="Print compiler and linker warnings to the terminal. Warnings are always written to build/build.log.",
    )
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="Build only; do not launch the application or test executables.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Build the portable core/UI tests instead of the Windows application.",
    )

    parsed = parser.parse_args(arguments)
    return BuildOptions(
        clean=parsed.clean,
        debug=parsed.debug,
        show_warnings=parsed.show_warnings,
        run_after_build=not parsed.no_run,
        build_tests=parsed.test,
    )


def print_build_heading(options: BuildOptions) -> None:
    build_kind = "Debug" if options.debug else "Release"
    target = "Tests" if options.build_tests else "Application"
    print("=" * 60)
    print(f" {PROJECT_NAME} - {build_kind} {target} Build")
    print("=" * 60)
    print()


def clean_build_directory_if_requested(options: BuildOptions) -> None:
    if options.clean:
        build_api.clean_directory("build")


def verify_required_project_files() -> None:
    missing_files = [
        filename
        for filename in REQUIRED_FILES
        if not (PROJECT_ROOT / filename).is_file()
    ]

    if not missing_files:
        return

    print("BUILD ERROR: required project files are missing:")
    for filename in missing_files:
        print(f"  - {filename}")
    raise SystemExit(1)


def validate_project_contracts() -> None:
    validator = PROJECT_ROOT / "tests" / "validate_lattice_contracts.py"
    print("VALIDATE Lattice Notes source contracts", flush=True)

    result = subprocess.run(
        [sys.executable, str(validator)],
        cwd=PROJECT_ROOT,
        shell=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def create_cpp_compiler(options: BuildOptions, *, optimized: bool) -> build_api.Compiler:
    compiler = build_api.Compiler()
    compiler.cpp_standard = build_api.CppStandard.CPP20
    compiler.optimization = choose_optimization(options, optimized=optimized)
    compiler.debug_information = options.debug
    compiler.link_time_optimization = optimized and not options.debug
    compiler.show_warnings = options.show_warnings
    compiler.include_directories.extend(INCLUDE_DIRECTORIES)
    compiler.init()
    return compiler


def choose_optimization(
    options: BuildOptions,
    *,
    optimized: bool,
) -> build_api.Optimization:
    if options.debug:
        return build_api.Optimization.DEBUG
    if optimized:
        return build_api.Optimization.MAXIMUM
    return build_api.Optimization.NONE


def create_linker(
    options: BuildOptions,
    *,
    optimized: bool,
    static_runtime: bool = False,
) -> build_api.Linker:
    linker = build_api.Linker()
    linker.link_time_optimization = optimized and not options.debug
    linker.static_runtime = static_runtime
    linker.console_application = True
    linker.show_warnings = options.show_warnings
    linker.init()
    return linker


def compile_sources(
    compiler: build_api.Compiler,
    sources: Sequence[str],
    object_folder: str,
    object_prefix: str,
) -> list[Path]:
    objects: list[Path] = []

    for index, source in enumerate(sources):
        source_name = Path(source).stem
        object_file = f"build/{object_folder}/{object_prefix}{index:02d}_{source_name}.o"
        objects.append(compiler.compile(source, object_file))

    return objects


def build_p1ui_library(options: BuildOptions) -> Path:
    print("BUILD P1UI library", flush=True)
    compiler = create_cpp_compiler(options, optimized=True)
    objects = compile_sources(compiler, P1UI_SOURCES, "obj/p1ui", "p1ui_")
    linker = create_linker(options, optimized=True)
    return linker.link_static_library(objects, "build/lib/libP1UI.a")


def build_lattice_notes_tests(options: BuildOptions) -> tuple[Path, Path]:
    print("BUILD Lattice Notes tests", flush=True)
    compiler = create_cpp_compiler(options, optimized=False)
    linker = create_linker(options, optimized=False)
    executable_suffix = ".exe" if os.name == "nt" else ""

    core_objects = compile_sources(
        compiler,
        LATTICE_TEST_SOURCES,
        "obj/tests_core",
        "core_",
    )
    core_executable = linker.link_executable(
        core_objects,
        f"build/tests/LatticeNotes_Tests{executable_suffix}",
        [],
    )

    p1ui_objects = compile_sources(
        compiler,
        PORTABLE_P1UI_CORE,
        "obj/tests_p1ui",
        "p1ui_",
    )
    ui_objects = compile_sources(
        compiler,
        LATTICE_UI_TEST_SOURCES,
        "obj/tests_ui",
        "ui_",
    )
    ui_executable = linker.link_executable(
        [*p1ui_objects, *ui_objects],
        f"build/tests/LatticeNotes_UI_Tests{executable_suffix}",
        [],
    )

    if options.run_after_build:
        build_api.run_program(core_executable, timeout_seconds=90)
        build_api.run_program(ui_executable, timeout_seconds=120)

    print("LATTICE NOTES TEST BUILD: PASS")
    return core_executable, ui_executable


def build_lattice_notes_application(options: BuildOptions) -> Path:
    if os.name != "nt":
        raise SystemExit(
            "BUILD ERROR: LatticeNotes.exe uses the Win32/OpenGL 4.6 backend and "
            "must be built on Windows. Run `python build.py --test` here for "
            "portable validation."
        )

    print("BUILD Lattice Notes application", flush=True)
    p1ui_library = build_p1ui_library(options)

    compiler = create_cpp_compiler(options, optimized=True)
    engine_objects = compile_sources(
        compiler,
        ENGINE_SOURCES,
        "obj/engine",
        "engine_",
    )
    application_objects = compile_sources(
        compiler,
        LATTICE_SOURCES,
        "obj/lattice",
        "lattice_",
    )

    linker = create_linker(
        options,
        optimized=True,
        static_runtime=True,
    )
    executable = linker.link_executable(
        [*engine_objects, *application_objects, p1ui_library],
        APPLICATION_OUTPUT,
        WIN32_LIBRARIES,
    )

    print(f"Built {PROJECT_NAME}: {executable.relative_to(PROJECT_ROOT)}")

    if options.run_after_build:
        build_api.run_program(executable, wait=False)

    return executable


def build_project(options: BuildOptions) -> None:
    clean_build_directory_if_requested(options)
    verify_required_project_files()
    validate_project_contracts()

    if options.build_tests:
        build_lattice_notes_tests(options)
    else:
        build_lattice_notes_application(options)


def main(arguments: Sequence[str] | None = None) -> int:
    options = read_command_line(sys.argv[1:] if arguments is None else arguments)
    print_build_heading(options)
    build_project(options)
    print(f"{PROJECT_NAME.upper()} BUILD: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
