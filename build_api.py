from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class BuildError(RuntimeError):
    pass


def create_directory_if_missing(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _find_tool(name: str) -> str:
    found = shutil.which(name)
    if found is None:
        raise BuildError(f"Required build tool was not found in PATH: {name}")
    return found


def _run(command: list[str], working_directory: Path) -> None:
    print(" ".join(command), flush=True)

    result = subprocess.run(
        command,
        cwd=working_directory,
        shell=False,
    )

    if result.returncode != 0:
        raise BuildError(
            f"Command failed with exit code {result.returncode}: "
            + " ".join(command)
        )


def _cpp_standard_flag(cpp_standard: str) -> str:
    normalized = cpp_standard.strip().upper().replace(" ", "")

    standards = {
        "C++17": "-std=c++17",
        "C++20": "-std=c++20",
        "C++23": "-std=c++23",
    }

    if normalized not in standards:
        raise BuildError(
            f"Unsupported C++ standard: {cpp_standard}. "
            "Use C++17, C++20, or C++23."
        )

    return standards[normalized]


class Compiler:
    def __init__(self, working_directory: str | Path):
        self.working_directory = Path(working_directory)
        self.compiler = "g++"
        self.cpp_standard = "C++20"
        self.compilation_units: list[tuple[Path, Path]] = []

    def add_compilation_unit(
        self,
        source_file: str | Path,
        object_file: str | Path,
    ) -> None:
        self.compilation_units.append(
            (Path(source_file), Path(object_file))
        )

    def run(self) -> None:
        compiler = _find_tool(self.compiler)
        standard = _cpp_standard_flag(self.cpp_standard)

        for source_file, object_file in self.compilation_units:
            source = self.working_directory / source_file
            output = self.working_directory / object_file

            if not source.is_file():
                raise BuildError(f"Source file does not exist: {source_file}")

            output.parent.mkdir(parents=True, exist_ok=True)

            command = [
                compiler,
                standard,
                "-Wall",
                "-Wextra",
                "-c",
                str(source),
                "-o",
                str(output),
            ]

            _run(command, self.working_directory)


class StaticLibrary:
    def __init__(self, working_directory: str | Path):
        self.working_directory = Path(working_directory)
        self.archiver = "ar"
        self.output_file: Path | None = None
        self.object_files: list[Path] = []

    def add_object_file(self, object_file: str | Path) -> None:
        self.object_files.append(Path(object_file))

    def run(self) -> None:
        if self.output_file is None:
            raise BuildError("StaticLibrary.output_file was not set.")

        archiver = _find_tool(self.archiver)
        output = self.working_directory / self.output_file
        output.parent.mkdir(parents=True, exist_ok=True)

        objects = []
        for object_file in self.object_files:
            path = self.working_directory / object_file

            if not path.is_file():
                raise BuildError(f"Object file does not exist: {object_file}")

            objects.append(str(path))

        command = [
            archiver,
            "rcs",
            str(output),
            *objects,
        ]

        _run(command, self.working_directory)


class Linker:
    def __init__(self, working_directory: str | Path):
        self.working_directory = Path(working_directory)
        self.linker = "g++"
        self.output_file: Path | None = None
        self.object_files: list[Path] = []
        self.static_libraries: list[Path] = []

    def add_object_file(self, object_file: str | Path) -> None:
        self.object_files.append(Path(object_file))

    def add_static_library(self, library_file: str | Path) -> None:
        self.static_libraries.append(Path(library_file))

    def run(self) -> None:
        if self.output_file is None:
            raise BuildError("Linker.output_file was not set.")

        linker = _find_tool(self.linker)
        output = self.working_directory / self.output_file
        output.parent.mkdir(parents=True, exist_ok=True)

        inputs: list[str] = []

        for object_file in self.object_files:
            path = self.working_directory / object_file

            if not path.is_file():
                raise BuildError(f"Object file does not exist: {object_file}")

            inputs.append(str(path))

        for library_file in self.static_libraries:
            path = self.working_directory / library_file

            if not path.is_file():
                raise BuildError(
                    f"Static library does not exist: {library_file}"
                )

            # This is the exact library file path.
            # No -lNAME search and no hidden .lib/.a lookup is performed.
            inputs.append(str(path))

        command = [
            linker,
            *inputs,
            "-o",
            str(output),
        ]

        _run(command, self.working_directory)


def run_program(
    working_directory: str | Path,
    executable_file: str | Path,
) -> None:
    working_directory = Path(working_directory)
    executable = working_directory / executable_file

    if not executable.is_file():
        raise BuildError(f"Executable does not exist: {executable_file}")

    _run([str(executable)], working_directory)
