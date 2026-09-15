from __future__ import annotations

import json
import os
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


def _path_for_command(path: Path, working_directory: Path) -> str:
    """
    Prefer paths relative to the project directory.

    Besides keeping build output readable, this is important for GCC dependency
    files on Windows: relative paths avoid drive-letter colons in the makefile
    target and forward slashes keep the dependency file simple to parse.
    """
    try:
        relative = path.resolve().relative_to(working_directory.resolve())
        return relative.as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _build_information_file(output_file: Path) -> Path:
    return output_file.with_name(output_file.name + ".build.json")


def _file_state(path: Path) -> dict[str, int] | None:
    """Return cheap state used to detect external modification of an artifact."""
    try:
        stat = path.stat()
    except OSError:
        return None

    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _tool_identity(tool: str) -> dict[str, object]:
    """
    Describe the actual build-tool executable, not just its path.

    A compiler/linker can be upgraded in-place while keeping the same filename.
    Recording size and modification time makes that invalidate old outputs too.
    """
    path = Path(tool)

    try:
        stat = path.stat()
    except OSError:
        return {
            "path": str(path),
            "size": None,
            "mtime_ns": None,
        }

    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _build_environment() -> dict[str, str | None]:
    """
    Capture environment variables that can change GCC's search/tool behavior.

    The command line can be identical while CPATH, CPLUS_INCLUDE_PATH, PATH,
    etc. select different headers or subordinate tools. In that case cached
    object files must not silently survive.
    """
    names = [
        "PATH",
        "CPATH",
        "CPLUS_INCLUDE_PATH",
        "C_INCLUDE_PATH",
        "OBJC_INCLUDE_PATH",
        "GCC_EXEC_PREFIX",
        "COMPILER_PATH",
        "LIBRARY_PATH",
    ]
    return {name: os.environ.get(name) for name in names}


def _invalidate_build_information(output_file: Path) -> None:
    """
    Mark an output as untrusted before attempting to replace/rebuild it.

    This is important for failure recovery. A failed compiler or linker is
    allowed to leave its output file behind (possibly partially rewritten).
    Old success metadata must never make that file look valid next time.
    """
    information_file = _build_information_file(output_file)
    try:
        information_file.unlink()
    except FileNotFoundError:
        pass


def _write_build_information(
    output_file: Path,
    kind: str,
    command: list[str],
    tool: str,
    auxiliary_files: list[Path] | None = None,
) -> None:
    information_file = _build_information_file(output_file)
    auxiliary_files = auxiliary_files or []
    information = {
        "version": 3,
        "kind": kind,
        "command": command,
        "tool": _tool_identity(tool),
        "environment": _build_environment(),
        "output_state": _file_state(output_file),
        "auxiliary_files": [
            {
                "path": str(path.resolve()),
                "state": _file_state(path),
            }
            for path in auxiliary_files
        ],
    }

    # Write through a temporary file so a crash cannot leave half-written JSON.
    temporary_file = information_file.with_name(information_file.name + ".tmp")
    temporary_file.write_text(
        json.dumps(information, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_file.replace(information_file)


def _build_information_matches(
    output_file: Path,
    kind: str,
    command: list[str],
    tool: str,
    auxiliary_files: list[Path] | None = None,
) -> bool:
    information_file = _build_information_file(output_file)

    try:
        information = json.loads(information_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    auxiliary_files = auxiliary_files or []
    expected_auxiliary_files = [
        {
            "path": str(path.resolve()),
            "state": _file_state(path),
        }
        for path in auxiliary_files
    ]

    return (
        information.get("version") == 3
        and information.get("kind") == kind
        and information.get("command") == command
        and information.get("tool") == _tool_identity(tool)
        and information.get("environment") == _build_environment()
        and information.get("output_state") == _file_state(output_file)
        and information.get("auxiliary_files") == expected_auxiliary_files
    )


def _is_newer(input_file: Path, output_file: Path) -> bool:
    return input_file.stat().st_mtime_ns > output_file.stat().st_mtime_ns


def _split_makefile_words(text: str) -> list[str]:
    """
    Split the dependency list written by GCC.

    GCC escapes spaces and several makefile-special characters with a
    backslash. A literal dollar sign is emitted as ``$$`` because dollar has a
    special meaning to make. Convert those spellings back to the real path.
    """
    words: list[str] = []
    current: list[str] = []
    index = 0

    while index < len(text):
        character = text[index]

        if character == "\\":
            index += 1
            if index < len(text):
                current.append(text[index])
            else:
                current.append("\\")
            index += 1
            continue

        if character == "$" and index + 1 < len(text) and text[index + 1] == "$":
            current.append("$")
            index += 2
            continue

        if character.isspace():
            if current:
                words.append("".join(current))
                current = []
            index += 1
            continue

        current.append(character)
        index += 1

    if current:
        words.append("".join(current))

    return words


def _find_makefile_rule_separator(text: str) -> int | None:
    """
    Find the colon that separates a makefile target from its dependencies.

    Looking for the first colon is wrong on Windows when the target is an
    absolute path such as ``C:/project/build/file.o``. GCC writes the rule
    separator as a colon followed by whitespace, while a drive-letter colon is
    followed by a slash or backslash.
    """
    escaped = False

    for index, character in enumerate(text):
        if escaped:
            escaped = False
            continue

        if character == "\\":
            escaped = True
            continue

        if character != ":":
            continue

        next_index = index + 1
        if next_index >= len(text) or text[next_index].isspace():
            return index

    return None


def _read_gcc_dependencies(
    dependency_file: Path,
    working_directory: Path,
) -> list[Path] | None:
    try:
        text = dependency_file.read_text(encoding="utf-8")
    except OSError:
        return None

    # GCC wraps long dependency rules using backslash-newline continuations.
    text = text.replace("\\\r\n", " ").replace("\\\n", " ")

    # -MP adds extra phony rules after the main object dependency rule.
    # We only need the first logical rule.
    lines = text.splitlines()
    first_line = lines[0] if lines else ""
    separator = _find_makefile_rule_separator(first_line)
    if separator is None:
        return None

    dependency_text = first_line[separator + 1:]
    dependency_names = _split_makefile_words(dependency_text)

    if not dependency_names:
        return None

    dependencies: list[Path] = []
    for dependency_name in dependency_names:
        dependency = Path(dependency_name)
        if not dependency.is_absolute():
            dependency = working_directory / dependency
        dependencies.append(dependency)

    return dependencies


def _compiler_output_is_up_to_date(
    output_file: Path,
    dependency_file: Path,
    working_directory: Path,
    command: list[str],
    tool: str,
) -> bool:
    if not output_file.is_file():
        return False

    if not dependency_file.is_file():
        return False

    if not _build_information_matches(
        output_file,
        "compile",
        command,
        tool,
        [dependency_file],
    ):
        return False

    dependencies = _read_gcc_dependencies(dependency_file, working_directory)
    if dependencies is None:
        return False

    for dependency in dependencies:
        if not dependency.is_file():
            return False

        if _is_newer(dependency, output_file):
            return False

    return True


def _output_is_up_to_date(
    output_file: Path,
    input_files: list[Path],
    kind: str,
    command: list[str],
    tool: str,
) -> bool:
    if not output_file.is_file():
        return False

    if not _build_information_matches(output_file, kind, command, tool):
        return False

    for input_file in input_files:
        if not input_file.is_file():
            return False

        if _is_newer(input_file, output_file):
            return False

    return True


class Compiler:
    def __init__(self, working_directory: str | Path):
        self.working_directory = Path(working_directory).resolve()
        self.compiler = "g++"
        self.cpp_standard = "C++20"
        self.include_directories: list[Path] = []
        self.compilation_units: list[tuple[Path, Path]] = []

    def add_include_directory(self, directory: str | Path) -> None:
        self.include_directories.append(Path(directory))

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
            dependency_file = output.with_suffix(".d")

            source_argument = _path_for_command(source, self.working_directory)
            output_argument = _path_for_command(output, self.working_directory)
            dependency_argument = _path_for_command(
                dependency_file,
                self.working_directory,
            )

            command = [
                compiler,
                standard,
                "-Wall",
                "-Wextra",
            ]

            for include_directory in self.include_directories:
                include_path = self.working_directory / include_directory
                command.append(
                    "-I" + _path_for_command(
                        include_path,
                        self.working_directory,
                    )
                )

            # Ask GCC to write the exact non-system header dependencies used by
            # this translation unit while it compiles. The next build can then
            # safely skip this object unless the source/header graph changed.
            command.extend([
                "-MMD",
                "-MP",
                "-MF",
                dependency_argument,
                "-MT",
                output_argument,
                "-c",
                source_argument,
                "-o",
                output_argument,
            ])

            if _compiler_output_is_up_to_date(
                output,
                dependency_file,
                self.working_directory,
                command,
                compiler,
            ):
                print(f"UP TO DATE  {object_file}", flush=True)
                continue

            print(f"COMPILE     {source_file}", flush=True)

            # Invalidate the previous success record *before* invoking GCC.
            # If GCC fails or the process is interrupted, the next build must
            # retry rather than trusting a possibly stale/partial object file.
            _invalidate_build_information(output)
            try:
                dependency_file.unlink()
            except FileNotFoundError:
                pass

            _run(command, self.working_directory)

            if not output.is_file():
                raise BuildError(
                    f"Compiler reported success but did not create: {object_file}"
                )
            if not dependency_file.is_file():
                raise BuildError(
                    "Compiler reported success but did not create dependency "
                    f"file: {dependency_file.name}"
                )

            _write_build_information(
                output,
                "compile",
                command,
                compiler,
                [dependency_file],
            )


class StaticLibrary:
    def __init__(self, working_directory: str | Path):
        self.working_directory = Path(working_directory).resolve()
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

        object_paths: list[Path] = []
        object_arguments: list[str] = []

        for object_file in self.object_files:
            path = self.working_directory / object_file

            if not path.is_file():
                raise BuildError(f"Object file does not exist: {object_file}")

            object_paths.append(path)
            object_arguments.append(
                _path_for_command(path, self.working_directory)
            )

        output_argument = _path_for_command(output, self.working_directory)
        logical_command = [
            archiver,
            "rcs",
            output_argument,
            *object_arguments,
        ]

        if _output_is_up_to_date(
            output,
            object_paths,
            "static_library",
            logical_command,
            archiver,
        ):
            print(f"UP TO DATE  {self.output_file}", flush=True)
            return

        print(f"ARCHIVE     {self.output_file}", flush=True)

        # Build a fresh archive rather than updating an old one in-place. If an
        # object is ever removed from add_object_file(), this guarantees a stale
        # member cannot survive inside the .a file.
        temporary_output = output.with_name(output.name + ".tmp")
        if temporary_output.exists():
            temporary_output.unlink()

        temporary_command = [
            archiver,
            "rcs",
            _path_for_command(temporary_output, self.working_directory),
            *object_arguments,
        ]

        _invalidate_build_information(output)

        try:
            _run(temporary_command, self.working_directory)
            if not temporary_output.is_file():
                raise BuildError(
                    "Archiver reported success but did not create: "
                    f"{temporary_output.name}"
                )
            temporary_output.replace(output)
        finally:
            if temporary_output.exists():
                temporary_output.unlink()

        _write_build_information(output, "static_library", logical_command, archiver)


class Linker:
    def __init__(self, working_directory: str | Path):
        self.working_directory = Path(working_directory).resolve()
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

        input_paths: list[Path] = []
        input_arguments: list[str] = []

        for object_file in self.object_files:
            path = self.working_directory / object_file

            if not path.is_file():
                raise BuildError(f"Object file does not exist: {object_file}")

            input_paths.append(path)
            input_arguments.append(
                _path_for_command(path, self.working_directory)
            )

        for library_file in self.static_libraries:
            path = self.working_directory / library_file

            if not path.is_file():
                raise BuildError(
                    f"Static library does not exist: {library_file}"
                )

            # This is the exact library file path.
            # No -lNAME search and no hidden .lib/.a lookup is performed.
            input_paths.append(path)
            input_arguments.append(
                _path_for_command(path, self.working_directory)
            )

        output_argument = _path_for_command(output, self.working_directory)
        command = [
            linker,
            *input_arguments,
            "-o",
            output_argument,
        ]

        if _output_is_up_to_date(
            output,
            input_paths,
            "link",
            command,
            linker,
        ):
            print(f"UP TO DATE  {self.output_file}", flush=True)
            return

        print(f"LINK        {self.output_file}", flush=True)

        # As with compilation, remove old success metadata first. A failed
        # linker can truncate or replace an existing executable.
        _invalidate_build_information(output)
        _run(command, self.working_directory)

        if not output.is_file():
            raise BuildError(
                f"Linker reported success but did not create: {self.output_file}"
            )

        _write_build_information(output, "link", command, linker)


def run_program(
    working_directory: str | Path,
    executable_file: str | Path,
) -> None:
    working_directory = Path(working_directory).resolve()
    executable = working_directory / executable_file

    if not executable.is_file():
        raise BuildError(f"Executable does not exist: {executable_file}")

    _run([str(executable)], working_directory)


def get_directory_containing_file(file: str | Path) -> Path:
    return Path(file).resolve().parent
