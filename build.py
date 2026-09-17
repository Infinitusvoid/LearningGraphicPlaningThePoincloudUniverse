import build_api



def build_project():
    # ------------------------------------------------------------------
    # Where this project lives
    # ------------------------------------------------------------------

    project_directory = build_api.get_directory_containing_file(__file__)
    
    # ------------------------------------------------------------------
    # Folders that must exist
    # ------------------------------------------------------------------

    build_api.create_directory_if_missing(project_directory / "application")
    build_api.create_directory_if_missing(project_directory / "application" / "sketches")
    build_api.create_directory_if_missing(project_directory / "build")
    build_api.create_directory_if_missing(project_directory / "third_party")
    
    
    # ------------------------------------------------------------------
    # Compile every C++ source file into an explicit object file
    # ------------------------------------------------------------------

    compiler = build_api.Compiler(project_directory)
    compiler.compiler = "g++"
    compiler.cpp_standard = "C++20"

    # Search here when a C++ source file uses: #include "..."
    # This does not compile anything inside the directory.
    compiler.add_include_directory("third_party/stb")

    compiler.add_compilation_unit(
        "application/my_lib.cpp",
        "build/my_lib.o",
    )

    compiler.add_compilation_unit(
        "application/engine.cpp",
        "build/engine.o",
    )

    compiler.add_compilation_unit(
        "application/application.cpp",
        "build/application.o",
    )

    compiler.add_compilation_unit(
        "application/main.cpp",
        "build/main.o",
    )

    compiler.add_compilation_unit(
        "application/tests.cpp",
        "build/tests.o",
    )
    
    compiler.add_compilation_unit(
        "application/ImageRGBA.cpp",
        "build/ImageRGBA.o",
    )
    
    compiler.add_compilation_unit(
        "application/FfmpegWriter.cpp",
        "build/FfmpegWriter.o"
    )
    
    compiler.run()

    # Notes
    # .cpp = human-readable source code
    # .o = previously compiled binary object code
    # .a = binary archive containing one or more .o files ( think .lib on windows)
    # .exe = final linked executable

    # add_include_directory() does not compile the directory.
    # It only adds a place where the compiler can search for included headers.

    # ------------------------------------------------------------------
    # Create one explicit static library file
    #
    # Nothing is searched for.
    # We create exactly: build/my_lib.a
    # ------------------------------------------------------------------

    my_lib = build_api.StaticLibrary(project_directory)
    my_lib.archiver = "ar"
    my_lib.output_file = "build/my_lib.a"

    my_lib.add_object_file("build/my_lib.o")

    my_lib.run()


    # ------------------------------------------------------------------
    # Link the application
    #
    # The static library is given by its exact file path.
    # There is no hidden "find a library named my_lib" behavior.
    # ------------------------------------------------------------------

    application = build_api.Linker(project_directory)
    application.linker = "g++"
    application.output_file = "build/application.exe"

    application.add_object_file("build/engine.o")
    application.add_object_file("build/application.o")
    application.add_object_file("build/main.o")
    application.add_object_file("build/ImageRGBA.o")
    application.add_object_file("build/FfmpegWriter.o")

    application.add_static_library("build/my_lib.a")

    application.run()

    # ------------------------------------------------------------------
    # Link the tests
    # ------------------------------------------------------------------

    tests = build_api.Linker(project_directory)
    tests.linker = "g++"
    tests.output_file = "build/tests.exe"

    tests.add_object_file("build/engine.o")
    tests.add_object_file("build/tests.o")

    tests.add_static_library("build/my_lib.a")

    tests.run()


    # ------------------------------------------------------------------
    # Run the tests
    # ------------------------------------------------------------------

    build_api.run_program(
        project_directory,
        "build/tests.exe",
    )


    # ------------------------------------------------------------------
    # Run the application
    # ------------------------------------------------------------------

    build_api.run_program(
        project_directory,
        "build/application.exe",
    )


if __name__ == "__main__":
    build_project()
