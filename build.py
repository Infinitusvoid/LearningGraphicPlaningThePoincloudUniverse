from pathlib import Path

import build_api


def build_project() -> int:
    # ------------------------------------------------------------
    # Project configuration
    # ------------------------------------------------------------

    project_name = "Lattice Notes"
    project_root = Path(__file__).resolve().parent

    options = build_api.read_standard_build_options(project_name)
    build_api.print_build_heading(
        project_name,
        options,
        application_name="Application",
        tests_name="Tests",
    )

    project = build_api.Project(project_name, project_root)
    project.apply_options(options)

    project.cpp_standard = "C++20"
    project.optimization = "maximum"

    project.add_include_directory(".")
    project.add_include_directory("p1ui")
    project.add_include_directory("engine")
    project.add_include_directory("src/lattice_notes")
    project.add_include_directory("YOU_CAN_USE_TO_NOT_REINVENT_THE_WHEEL")


    # ------------------------------------------------------------
    # Files that must already exist
    # ------------------------------------------------------------

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


    # ------------------------------------------------------------
    # Prepare the build
    # ------------------------------------------------------------

    # build_api creates build/, object directories, dependency files,
    # logs, libraries, and executable output directories as needed.
    # A clean build is only performed when --clean is explicitly requested.
    if options.clean:
        project.clean()

    project.validate()


    # ------------------------------------------------------------
    # Build and run tests when --test is requested
    # ------------------------------------------------------------

    if options.build_tests:
        core_tests = project.executable(
            "LatticeNotes_Tests",
            output_directory="build/tests",
        )
        core_tests.optimization = "none"

        core_tests.add_compilation_unit("src/lattice_notes/LatticeNotesPersistence.cpp")
        core_tests.add_compilation_unit("src/lattice_notes/LatticeNotesPanelBaker.cpp")
        core_tests.add_compilation_unit("src/lattice_notes/dev_review/DevReview.cpp")
        core_tests.add_compilation_unit("tests/LatticeNotes_Tests.cpp")

        ui_tests = project.executable(
            "LatticeNotes_UI_Tests",
            output_directory="build/tests",
        )
        ui_tests.optimization = "none"

        ui_tests.add_compilation_unit("p1ui/P1UI.cpp")
        ui_tests.add_compilation_unit("p1ui/P1UI_State.cpp")
        ui_tests.add_compilation_unit("p1ui/P1UI_Composition.cpp")
        ui_tests.add_compilation_unit("p1ui/P1UI_DataEditing.cpp")
        ui_tests.add_compilation_unit("p1ui/P1UI_AppFoundation.cpp")
        ui_tests.add_compilation_unit("p1ui/P1UI_Production.cpp")

        ui_tests.add_compilation_unit("src/lattice_notes/LatticeNotesUI.cpp")
        ui_tests.add_compilation_unit("src/lattice_notes/LatticeNotesPersistence.cpp")
        ui_tests.add_compilation_unit("src/lattice_notes/LatticeNotesPanelBaker.cpp")
        ui_tests.add_compilation_unit("src/lattice_notes/dev_review/DevReview.cpp")
        ui_tests.add_compilation_unit("src/lattice_notes/dev_review/DevReviewUI.cpp")
        ui_tests.add_compilation_unit("tests/LatticeNotes_UI_Tests.cpp")

        core_tests.build()
        ui_tests.build()

        if options.run_after_build:
            core_tests.run(timeout_seconds=90)
            ui_tests.run(timeout_seconds=120)

        print("LATTICE NOTES TEST BUILD: PASS")
        return 0


    # ------------------------------------------------------------
    # Build P1UI static library
    # ------------------------------------------------------------

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


    # ------------------------------------------------------------
    # Build Lattice Notes application
    # ------------------------------------------------------------

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

    executable = app.build()
    print(f"Built {project_name}: {executable.relative_to(project_root)}")


    # ------------------------------------------------------------
    # Run the application
    # ------------------------------------------------------------

    if options.run_after_build:
        app.run(wait=False)

    print("LATTICE NOTES BUILD: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(build_project())
