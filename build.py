from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import build_api


PROJECT_NAME = "Lattice Notes"


def create_project(options: build_api.StandardBuildOptions):
    project = build_api.Project(PROJECT_NAME, PROJECT_ROOT)
    project.apply_options(options)

    project.cpp_standard = "C++20"
    project.optimization = "maximum"

    project.add_include_directory(".")
    project.add_include_directory("p1ui")
    project.add_include_directory("engine")
    project.add_include_directory("src/lattice_notes")
    project.add_include_directory("YOU_CAN_USE_TO_NOT_REINVENT_THE_WHEEL")

    project.require_file("engine/Engine.h")
    project.require_file("engine/Engine_internal_win32_opengl.h")
    project.require_file("engine_extensions/Engine_Extensions.h")
    project.require_file("p1ui/P1UI.h")
    project.require_file("src/lattice_notes/LatticeNotesApp.h")
    project.require_file("src/lattice_notes/LatticeNotesTextInput.h")
    project.require_file("src/lattice_notes/LatticeNotesModel.h")
    project.require_file("src/lattice_notes/dev_review/DevReview.h")
    project.require_file("src/lattice_notes/dev_review/DevReviewUI.h")
    project.require_file("YOU_CAN_USE_TO_NOT_REINVENT_THE_WHEEL/stb/image/stb_image.h")
    project.require_file("YOU_CAN_USE_TO_NOT_REINVENT_THE_WHEEL/stb/image/stb_image_write.h")
    project.require_file("YOU_CAN_USE_TO_NOT_REINVENT_THE_WHEEL/nlohmann/json.h")
    project.require_file("tests/engine_manifest.sha256")

    project.add_python_validation(
        "tests/validate_lattice_contracts.py",
        "Lattice Notes source contracts",
    )

    return project


def create_p1ui_library(project: build_api.Project):
    p1ui = project.static_library("P1UI")
    p1ui.link_time_optimization = True

    p1ui.add_compilation_unit("p1ui/P1UI.cpp")
    p1ui.add_compilation_unit("p1ui/P1UI_Renderer.cpp")
    p1ui.add_compilation_unit("p1ui/P1UI_Media.cpp")
    p1ui.add_compilation_unit("p1ui/P1UI_State.cpp")
    p1ui.add_compilation_unit("p1ui/P1UI_Composition.cpp")
    p1ui.add_compilation_unit("p1ui/P1UI_DataEditing.cpp")
    p1ui.add_compilation_unit("p1ui/P1UI_AppFoundation.cpp")
    p1ui.add_compilation_unit("p1ui/P1UI_Production.cpp")

    return p1ui


def create_application(project: build_api.Project, p1ui: build_api.StaticLibrary):
    app = project.executable("LatticeNotes")
    app.windows_only = True
    app.link_time_optimization = True
    app.static_runtime = True
    app.console_application = True

    app.add_compilation_unit("engine/Engine.cpp")
    app.add_compilation_unit("engine_extensions/Engine_Extensions_win32.cpp")
    app.add_compilation_unit("engine_extensions/FontRasterizer_win32.cpp")

    app.add_compilation_unit("src/lattice_notes/LatticeNotesPersistence.cpp")
    app.add_compilation_unit("src/lattice_notes/LatticeNotesPanelBaker.cpp")
    app.add_compilation_unit("src/lattice_notes/LatticeNotesRenderer.cpp")
    app.add_compilation_unit("src/lattice_notes/LatticeNotesAudio.cpp")
    app.add_compilation_unit("src/lattice_notes/LatticeNotesUI.cpp")
    app.add_compilation_unit("src/lattice_notes/dev_review/DevReview.cpp")
    app.add_compilation_unit("src/lattice_notes/dev_review/DevReviewUI.cpp")
    app.add_compilation_unit("src/lattice_notes/LatticeNotesApp.cpp")
    app.add_compilation_unit("src/lattice_notes/main.cpp")

    app.add_static_library(p1ui)

    app.add_library("opengl32")
    app.add_library("gdi32")
    app.add_library("user32")
    app.add_library("shell32")
    app.add_library("comdlg32")
    app.add_library("winmm")
    app.add_library("ole32")

    return app


def create_core_tests(project: build_api.Project):
    tests = project.executable(
        "LatticeNotes_Tests",
        output_directory="build/tests",
    )
    tests.optimization = "none"

    tests.add_compilation_unit("src/lattice_notes/LatticeNotesPersistence.cpp")
    tests.add_compilation_unit("src/lattice_notes/LatticeNotesPanelBaker.cpp")
    tests.add_compilation_unit("src/lattice_notes/dev_review/DevReview.cpp")
    tests.add_compilation_unit("tests/LatticeNotes_Tests.cpp")

    return tests


def create_ui_tests(project: build_api.Project):
    tests = project.executable(
        "LatticeNotes_UI_Tests",
        output_directory="build/tests",
    )
    tests.optimization = "none"

    tests.add_compilation_unit("p1ui/P1UI.cpp")
    tests.add_compilation_unit("p1ui/P1UI_State.cpp")
    tests.add_compilation_unit("p1ui/P1UI_Composition.cpp")
    tests.add_compilation_unit("p1ui/P1UI_DataEditing.cpp")
    tests.add_compilation_unit("p1ui/P1UI_AppFoundation.cpp")
    tests.add_compilation_unit("p1ui/P1UI_Production.cpp")

    tests.add_compilation_unit("src/lattice_notes/LatticeNotesUI.cpp")
    tests.add_compilation_unit("src/lattice_notes/LatticeNotesPersistence.cpp")
    tests.add_compilation_unit("src/lattice_notes/LatticeNotesPanelBaker.cpp")
    tests.add_compilation_unit("src/lattice_notes/dev_review/DevReview.cpp")
    tests.add_compilation_unit("src/lattice_notes/dev_review/DevReviewUI.cpp")
    tests.add_compilation_unit("tests/LatticeNotes_UI_Tests.cpp")

    return tests


def main() -> int:
    options = build_api.read_standard_build_options(PROJECT_NAME)
    build_api.print_build_heading(PROJECT_NAME, options)

    project = create_project(options)

    if options.clean:
        project.clean()

    project.validate()

    if options.build_tests:
        core_tests = create_core_tests(project)
        ui_tests = create_ui_tests(project)

        core_tests.build()
        ui_tests.build()

        if options.run_after_build:
            core_tests.run(timeout_seconds=90)
            ui_tests.run(timeout_seconds=120)

        print("LATTICE NOTES TEST BUILD: PASS")
        return 0

    p1ui = create_p1ui_library(project)
    app = create_application(project, p1ui)

    executable = app.build()
    print(f"Built {PROJECT_NAME}: {executable.relative_to(PROJECT_ROOT)}")

    if options.run_after_build:
        app.run(wait=False)

    print("LATTICE NOTES BUILD: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
