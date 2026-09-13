from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence


# The project build script should set this explicitly through Project(...) or
# set_project_root(...). The fallback keeps older build scripts working.
ROOT = Path(sys.argv[0]).resolve().parent
_LOG_INITIALIZED = False


def set_project_root(path: str | Path) -> Path:
    global ROOT, _LOG_INITIALIZED
    ROOT = Path(path).resolve()
    _LOG_INITIALIZED = False
    return ROOT


def project_root() -> Path:
    return ROOT


class Optimization(Enum):
    NONE = "-O0"
    DEBUG = "-Og"
    SPEED = "-O2"
    MAXIMUM = "-O3"
    SIZE = "-Os"


class CppStandard(Enum):
    CPP17 = "c++17"
    CPP20 = "c++20"
    CPP23 = "c++23"


class BuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class StandardBuildOptions:
    clean: bool
    debug: bool
    show_warnings: bool
    run_after_build: bool
    build_tests: bool


def read_standard_build_options(
    project_name: str,
    arguments: Sequence[str] | None = None,
) -> StandardBuildOptions:
    parser = argparse.ArgumentParser(
        description=f"Build {project_name}.",
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
        help="Print compiler/linker warnings. They are always written to build/build.log.",
    )
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="Build only; do not launch the application or tests.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Build the project's test executables instead of its normal application.",
    )

    parsed = parser.parse_args(sys.argv[1:] if arguments is None else arguments)
    return StandardBuildOptions(
        clean=parsed.clean,
        debug=parsed.debug,
        show_warnings=parsed.show_warnings,
        run_after_build=not parsed.no_run,
        build_tests=parsed.test,
    )


def print_build_heading(
    project_name: str,
    options: StandardBuildOptions,
    *,
    application_name: str = "Application",
    tests_name: str = "Tests",
) -> None:
    configuration = "Debug" if options.debug else "Release"
    target = tests_name if options.build_tests else application_name
    print("=" * 60)
    print(f" {project_name} - {configuration} {target} Build")
    print("=" * 60)
    print()


def _fail(message: str, exit_code: int = 1) -> None:
    print(f"\nBUILD ERROR: {message}", flush=True)
    raise SystemExit(exit_code)


def _resolve(path: str | Path) -> Path:
    path = Path(path)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def _display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _find_tool(requested: str, candidates: Sequence[str]) -> str:
    if requested:
        explicit = Path(requested)
        if explicit.is_file():
            return str(explicit.resolve())

        found = shutil.which(requested)
        if found:
            return found

        _fail(f"Tool was not found: {requested}")

    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found

    _fail("Could not find any of these tools: " + ", ".join(candidates))
    raise AssertionError("unreachable")


def _quote_command(command: Sequence[str]) -> str:
    return subprocess.list2cmdline([str(value) for value in command])


def _initialize_log() -> Path:
    global _LOG_INITIALIZED

    log_path = ROOT / "build" / "build.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if not _LOG_INITIALIZED:
        log_path.write_text("P1 build log\n============\n\n", encoding="utf-8")
        _LOG_INITIALIZED = True

    return log_path


def _append_log(title: str, command: Sequence[str], output: str) -> None:
    log_path = _initialize_log()
    with log_path.open("a", encoding="utf-8", errors="replace") as file:
        file.write(f"[{title}]\n")
        file.write(_quote_command(command))
        file.write("\n")
        if output:
            file.write(output.rstrip())
            file.write("\n")
        file.write("\n")


def _run_command(
    title: str,
    command: Sequence[str],
    *,
    verbose: bool,
    show_output: bool,
) -> subprocess.CompletedProcess[str]:
    if verbose:
        print("CMD ", _quote_command(command), flush=True)

    try:
        result = subprocess.run(
            [str(value) for value in command],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except OSError as error:
        _fail(f"Could not start {command[0]}: {error}")

    output = result.stdout or ""
    _append_log(title, command, output)

    if result.returncode != 0:
        if output:
            print(output.rstrip(), flush=True)
        _fail(f"{title} failed.", result.returncode)

    if show_output and output:
        print(output.rstrip(), flush=True)

    return result


def _sidecar(output: Path, suffix: str) -> Path:
    return Path(str(output) + suffix)


def _command_signature(command: Sequence[str]) -> str:
    text = "\0".join(str(value) for value in command)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _command_changed(sidecar: Path, command: Sequence[str]) -> bool:
    if not sidecar.is_file():
        return True
    try:
        old_signature = sidecar.read_text(encoding="utf-8").strip()
    except OSError:
        return True
    return old_signature != _command_signature(command)


def _write_command_signature(sidecar: Path, command: Sequence[str]) -> None:
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(_command_signature(command), encoding="utf-8")


def _is_newer(input_path: Path, output_path: Path) -> bool:
    try:
        return input_path.stat().st_mtime_ns > output_path.stat().st_mtime_ns
    except OSError:
        return True


def _read_dependencies(depfile: Path) -> list[Path]:
    if not depfile.is_file():
        return []

    try:
        text = depfile.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    text = text.replace("\\\n", " ")
    marker = text.find(":")
    if marker < 0:
        return []

    try:
        tokens = shlex.split(text[marker + 1 :], posix=True)
    except ValueError:
        return []

    dependencies: list[Path] = []
    for token in tokens:
        dependency = Path(token)
        if not dependency.is_absolute():
            dependency = ROOT / dependency
        dependencies.append(dependency.resolve())
    return dependencies


def _inputs_require_output(inputs: Iterable[Path], output: Path) -> bool:
    if not output.is_file():
        return True
    return any(not path.is_file() or _is_newer(path, output) for path in inputs)


def _normalize_cpp_standard(value: CppStandard | str) -> CppStandard:
    if isinstance(value, CppStandard):
        return value

    normalized = str(value).strip().lower().replace(" ", "").replace("_", "")
    aliases = {
        "c++17": CppStandard.CPP17,
        "cpp17": CppStandard.CPP17,
        "17": CppStandard.CPP17,
        "c++20": CppStandard.CPP20,
        "cpp20": CppStandard.CPP20,
        "20": CppStandard.CPP20,
        "c++23": CppStandard.CPP23,
        "cpp23": CppStandard.CPP23,
        "23": CppStandard.CPP23,
    }
    if normalized in aliases:
        return aliases[normalized]
    _fail(f"Unknown C++ standard: {value}")
    raise AssertionError("unreachable")


def _normalize_optimization(value: Optimization | str) -> Optimization:
    if isinstance(value, Optimization):
        return value

    normalized = str(value).strip().lower().replace("_", "-")
    aliases = {
        "none": Optimization.NONE,
        "off": Optimization.NONE,
        "debug": Optimization.DEBUG,
        "speed": Optimization.SPEED,
        "fast": Optimization.SPEED,
        "maximum": Optimization.MAXIMUM,
        "max": Optimization.MAXIMUM,
        "size": Optimization.SIZE,
        "small": Optimization.SIZE,
        "-o0": Optimization.NONE,
        "-og": Optimization.DEBUG,
        "-o2": Optimization.SPEED,
        "-o3": Optimization.MAXIMUM,
        "-os": Optimization.SIZE,
    }
    if normalized in aliases:
        return aliases[normalized]
    _fail(f"Unknown optimization mode: {value}")
    raise AssertionError("unreachable")


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return value or "target"


def _automatic_object_name(source: str | Path, index: int) -> str:
    source_text = Path(source).as_posix()
    digest = hashlib.sha1(source_text.encode("utf-8")).hexdigest()[:8]
    stem = _safe_name(Path(source).stem)
    return f"{index:03d}_{stem}_{digest}.o"


class Compiler:
    """Incremental C++ compiler with a small, declarative public API."""

    def __init__(self) -> None:
        self.filepath = ""
        self.cpp_standard: CppStandard | str = CppStandard.CPP20
        self.optimization: Optimization | str = Optimization.NONE
        self.debug_information = False
        self.link_time_optimization = False
        self.warnings = True
        self.show_warnings = False
        self.verbose = False
        self.force_recompile = False
        self.object_directory: str | Path = "build/obj"

        self.include_directories: list[str | Path] = []
        self.definitions: list[str] = []
        self.flags: list[str] = []
        self.compilation_units: list[tuple[str | Path, str | Path | None]] = []

    def init(self, filepath: str = "") -> "Compiler":
        self.filepath = _find_tool(filepath or self.filepath, ("g++.exe", "g++"))
        return self

    def add_compilation_unit(
        self,
        source_file: str | Path,
        output_file: str | Path | None = None,
    ) -> "Compiler":
        self.compilation_units.append((source_file, output_file))
        return self

    def add_include_directory(self, path: str | Path) -> "Compiler":
        self.include_directories.append(path)
        return self

    def add_definition(self, definition: str) -> "Compiler":
        self.definitions.append(definition)
        return self

    def add_flag(self, flag: str) -> "Compiler":
        self.flags.append(flag)
        return self

    def run(self) -> list[Path]:
        objects: list[Path] = []
        for index, (source, explicit_output) in enumerate(self.compilation_units):
            output = explicit_output
            if output is None:
                output = Path(self.object_directory) / _automatic_object_name(source, index)
            objects.append(self.compile(source, output))
        return objects

    def compile(self, input_file: str | Path, output_file: str | Path) -> Path:
        if not self.filepath:
            self.init()

        source = _resolve(input_file)
        output = _resolve(output_file)

        if not source.is_file():
            _fail(f"Source file does not exist: {_display(source)}")

        output.parent.mkdir(parents=True, exist_ok=True)
        depfile = _sidecar(output, ".d")
        command_file = _sidecar(output, ".command")

        standard = _normalize_cpp_standard(self.cpp_standard)
        optimization = _normalize_optimization(self.optimization)

        command: list[str] = [
            self.filepath,
            f"-std={standard.value}",
            optimization.value,
        ]

        if self.debug_information:
            command.append("-g3")
        if self.link_time_optimization:
            command.append("-flto")
        if self.warnings:
            command.extend(("-Wall", "-Wextra"))

        command.extend(f"-I{_resolve(path)}" for path in self.include_directories)
        command.extend(f"-D{definition}" for definition in self.definitions)
        command.extend(self.flags)
        command.extend(
            (
                "-MMD",
                "-MF",
                str(depfile),
                "-MT",
                "p1_object",
                "-c",
                str(source),
                "-o",
                str(output),
            )
        )

        needs_compile = self.force_recompile or not output.is_file()
        needs_compile = needs_compile or _command_changed(command_file, command)
        needs_compile = needs_compile or _is_newer(source, output)

        if not needs_compile:
            dependencies = _read_dependencies(depfile)
            needs_compile = not dependencies or any(
                not dependency.is_file() or _is_newer(dependency, output)
                for dependency in dependencies
            )

        if not needs_compile:
            return output

        print(f"CXX  {_display(source)}", flush=True)
        output.unlink(missing_ok=True)

        _run_command(
            f"Compile {_display(source)}",
            command,
            verbose=self.verbose,
            show_output=self.show_warnings,
        )

        _write_command_signature(command_file, command)
        return output


class CCompiler:
    """Incremental C compiler companion for vendored C sources."""

    def __init__(self) -> None:
        self.filepath = ""
        self.optimization: Optimization | str = Optimization.NONE
        self.debug_information = False
        self.link_time_optimization = False
        self.warnings = True
        self.show_warnings = False
        self.verbose = False
        self.force_recompile = False
        self.object_directory: str | Path = "build/obj_c"
        self.include_directories: list[str | Path] = []
        self.definitions: list[str] = []
        self.flags: list[str] = []
        self.compilation_units: list[tuple[str | Path, str | Path | None]] = []

    def init(self, filepath: str = "") -> "CCompiler":
        self.filepath = _find_tool(filepath or self.filepath, ("gcc.exe", "gcc"))
        return self

    def add_compilation_unit(
        self,
        source_file: str | Path,
        output_file: str | Path | None = None,
    ) -> "CCompiler":
        self.compilation_units.append((source_file, output_file))
        return self

    def add_include_directory(self, path: str | Path) -> "CCompiler":
        self.include_directories.append(path)
        return self

    def add_definition(self, definition: str) -> "CCompiler":
        self.definitions.append(definition)
        return self

    def add_flag(self, flag: str) -> "CCompiler":
        self.flags.append(flag)
        return self

    def run(self) -> list[Path]:
        objects: list[Path] = []
        for index, (source, explicit_output) in enumerate(self.compilation_units):
            output = explicit_output
            if output is None:
                output = Path(self.object_directory) / _automatic_object_name(source, index)
            objects.append(self.compile(source, output))
        return objects

    def compile(self, input_file: str | Path, output_file: str | Path) -> Path:
        if not self.filepath:
            self.init()

        source = _resolve(input_file)
        output = _resolve(output_file)
        if not source.is_file():
            _fail(f"Source file does not exist: {_display(source)}")

        output.parent.mkdir(parents=True, exist_ok=True)
        depfile = _sidecar(output, ".d")
        command_file = _sidecar(output, ".command")
        optimization = _normalize_optimization(self.optimization)
        command: list[str] = [self.filepath, "-std=c11", optimization.value]

        if self.debug_information:
            command.append("-g3")
        if self.link_time_optimization:
            command.append("-flto")
        if self.warnings:
            command.extend(("-Wall", "-Wextra"))

        command.extend(f"-I{_resolve(path)}" for path in self.include_directories)
        command.extend(f"-D{definition}" for definition in self.definitions)
        command.extend(self.flags)
        command.extend(
            (
                "-MMD",
                "-MF",
                str(depfile),
                "-MT",
                "p1_c_object",
                "-c",
                str(source),
                "-o",
                str(output),
            )
        )

        needs_compile = self.force_recompile or not output.is_file()
        needs_compile = needs_compile or _command_changed(command_file, command)
        needs_compile = needs_compile or _is_newer(source, output)

        if not needs_compile:
            dependencies = _read_dependencies(depfile)
            needs_compile = not dependencies or any(
                not dependency.is_file() or _is_newer(dependency, output)
                for dependency in dependencies
            )

        if not needs_compile:
            return output

        print(f"CC   {_display(source)}", flush=True)
        output.unlink(missing_ok=True)

        _run_command(
            f"Compile {_display(source)}",
            command,
            verbose=self.verbose,
            show_output=self.show_warnings,
        )
        _write_command_signature(command_file, command)
        return output


class Linker:
    """Low-level incremental linker. Most projects can use Executable/StaticLibrary."""

    def __init__(self) -> None:
        self.filepath = ""
        self.archiver_filepath = ""
        self.link_time_optimization = False
        self.static_runtime = False
        self.console_application = True
        self.verbose = False
        self.show_warnings = False
        self.force_relink = False
        self.library_directories: list[str | Path] = []
        self.libraries: list[str] = []
        self.flags: list[str] = []

    def init(self, filepath: str = "") -> "Linker":
        self.filepath = _find_tool(filepath or self.filepath, ("g++.exe", "g++"))
        return self

    def _common_command(self) -> list[str]:
        if not self.filepath:
            self.init()

        command = [self.filepath]
        if self.link_time_optimization:
            command.append("-flto")
        if self.static_runtime:
            command.extend(("-static", "-static-libgcc", "-static-libstdc++"))
        command.extend(f"-L{_resolve(path)}" for path in self.library_directories)
        return command

    def _link(
        self,
        kind: str,
        input_files: Iterable[str | Path],
        output_file: str | Path,
        libraries: Iterable[str],
        extra_flags: Iterable[str] = (),
    ) -> Path:
        inputs = [_resolve(path) for path in input_files]
        output = _resolve(output_file)

        for input_path in inputs:
            if not input_path.is_file():
                _fail(f"Link input does not exist: {_display(input_path)}")

        output.parent.mkdir(parents=True, exist_ok=True)
        command_file = _sidecar(output, ".command")

        command = self._common_command()
        command.extend(extra_flags)
        command.extend(str(path) for path in inputs)
        command.extend(f"-l{library}" for library in [*self.libraries, *libraries])
        command.extend(self.flags)
        command.extend(("-o", str(output)))

        needs_link = self.force_relink or _inputs_require_output(inputs, output)
        needs_link = needs_link or _command_changed(command_file, command)

        if not needs_link:
            return output

        print(f"{kind:<4} {_display(output)}", flush=True)
        output.unlink(missing_ok=True)

        _run_command(
            f"Link {_display(output)}",
            command,
            verbose=self.verbose,
            show_output=self.show_warnings,
        )

        _write_command_signature(command_file, command)
        return output

    def link_executable(
        self,
        input_files: Iterable[str | Path],
        output_file: str | Path,
        libraries: Iterable[str] = (),
    ) -> Path:
        flags: tuple[str, ...] = ()
        if os.name == "nt":
            flags = ("-mconsole" if self.console_application else "-mwindows",)
        return self._link("EXE", input_files, output_file, libraries, flags)

    def link_static_library(
        self,
        input_files: Iterable[str | Path],
        output_file: str | Path,
    ) -> Path:
        inputs = [_resolve(path) for path in input_files]
        output = _resolve(output_file)

        for input_path in inputs:
            if not input_path.is_file():
                _fail(f"Library input does not exist: {_display(input_path)}")

        if not self.archiver_filepath:
            self.archiver_filepath = _find_tool("", ("gcc-ar.exe", "gcc-ar", "ar.exe", "ar"))

        output.parent.mkdir(parents=True, exist_ok=True)
        command_file = _sidecar(output, ".command")
        command = [self.archiver_filepath, "rcs", str(output), *map(str, inputs)]

        needs_link = self.force_relink or _inputs_require_output(inputs, output)
        needs_link = needs_link or _command_changed(command_file, command)

        if not needs_link:
            return output

        print(f"LIB  {_display(output)}", flush=True)
        output.unlink(missing_ok=True)

        _run_command(
            f"Create static library {_display(output)}",
            command,
            verbose=self.verbose,
            show_output=self.show_warnings,
        )

        _write_command_signature(command_file, command)
        return output

    def link_shared_library(
        self,
        input_files: Iterable[str | Path],
        output_file: str | Path,
        libraries: Iterable[str] = (),
        import_library_file: str | Path | None = None,
    ) -> Path:
        flags = ["-shared"]
        if import_library_file is not None:
            import_library = _resolve(import_library_file)
            import_library.parent.mkdir(parents=True, exist_ok=True)
            flags.append(f"-Wl,--out-implib,{import_library}")

        return self._link("DLL", input_files, output_file, libraries, flags)


class Project:
    """Project-wide defaults and validation shared by build targets."""

    def __init__(self, name: str, root: str | Path) -> None:
        self.name = name
        self.root = set_project_root(root)
        self.cpp_standard: CppStandard | str = CppStandard.CPP20
        self.optimization: Optimization | str = Optimization.MAXIMUM
        self.debug = False
        self.show_warnings = False
        self.warnings = True
        self.include_directories: list[str | Path] = []
        self.required_files: list[str | Path] = []
        self.python_validations: list[tuple[str | Path, str]] = []

    def apply_options(self, options: StandardBuildOptions) -> "Project":
        self.debug = options.debug
        self.show_warnings = options.show_warnings
        return self

    def add_include_directory(self, path: str | Path) -> "Project":
        self.include_directories.append(path)
        return self

    def require_file(self, path: str | Path) -> "Project":
        self.required_files.append(path)
        return self

    def add_python_validation(
        self,
        script_file: str | Path,
        description: str = "Python validation",
    ) -> "Project":
        self.python_validations.append((script_file, description))
        return self

    def clean(self) -> None:
        clean_directory("build")

    def validate(self) -> None:
        missing = [path for path in self.required_files if not _resolve(path).is_file()]
        if missing:
            print("BUILD ERROR: required project files are missing:")
            for path in missing:
                print(f"  - {path}")
            raise SystemExit(1)

        for script_file, description in self.python_validations:
            script = _resolve(script_file)
            if not script.is_file():
                _fail(f"Validation script does not exist: {_display(script)}")
            print(f"VALIDATE {description}", flush=True)
            _run_command(
                description,
                [sys.executable, str(script)],
                verbose=False,
                show_output=True,
            )

    def executable(
        self,
        name: str,
        *,
        output_directory: str | Path = "build",
        output_file: str | Path | None = None,
    ) -> "Executable":
        return Executable(self, name, output_directory=output_directory, output_file=output_file)

    def static_library(
        self,
        name: str,
        *,
        output_directory: str | Path = "build/lib",
        output_file: str | Path | None = None,
    ) -> "StaticLibrary":
        return StaticLibrary(self, name, output_directory=output_directory, output_file=output_file)


class _CppTarget:
    def __init__(
        self,
        project: Project,
        name: str,
        *,
        output_directory: str | Path,
        output_file: str | Path | None,
    ) -> None:
        self.project = project
        self.name = name
        self.output_directory = Path(output_directory)
        self.explicit_output_file = Path(output_file) if output_file is not None else None
        self.cpp_standard: CppStandard | str | None = None
        self.optimization: Optimization | str | None = None
        self.link_time_optimization = False
        self.windows_only = False
        self.compilation_units: list[str | Path] = []
        self.include_directories: list[str | Path] = []
        self.definitions: list[str] = []
        self.compiler_flags: list[str] = []
        self._built_output: Path | None = None

    def add_compilation_unit(self, source_file: str | Path) -> "_CppTarget":
        self.compilation_units.append(source_file)
        return self

    def add_include_directory(self, path: str | Path) -> "_CppTarget":
        self.include_directories.append(path)
        return self

    def add_definition(self, definition: str) -> "_CppTarget":
        self.definitions.append(definition)
        return self

    def add_compiler_flag(self, flag: str) -> "_CppTarget":
        self.compiler_flags.append(flag)
        return self

    def _check_platform(self) -> None:
        if self.windows_only and os.name != "nt":
            _fail(f"{self.name} uses a Windows-only backend and must be built on Windows.")

    def _effective_standard(self) -> CppStandard | str:
        return self.cpp_standard if self.cpp_standard is not None else self.project.cpp_standard

    def _effective_optimization(self) -> Optimization | str:
        if self.project.debug:
            return Optimization.DEBUG
        return self.optimization if self.optimization is not None else self.project.optimization

    def _create_compiler(self) -> Compiler:
        compiler = Compiler()
        compiler.cpp_standard = self._effective_standard()
        compiler.optimization = self._effective_optimization()
        compiler.debug_information = self.project.debug
        compiler.link_time_optimization = self.link_time_optimization and not self.project.debug
        compiler.warnings = self.project.warnings
        compiler.show_warnings = self.project.show_warnings
        compiler.object_directory = Path("build/obj") / _safe_name(self.name)

        for path in self.project.include_directories:
            compiler.add_include_directory(path)
        for path in self.include_directories:
            compiler.add_include_directory(path)
        for definition in self.definitions:
            compiler.add_definition(definition)
        for flag in self.compiler_flags:
            compiler.add_flag(flag)
        for source_file in self.compilation_units:
            compiler.add_compilation_unit(source_file)

        return compiler

    def _compile(self) -> list[Path]:
        self._check_platform()
        return self._create_compiler().run()


class StaticLibrary(_CppTarget):
    def __init__(
        self,
        project: Project,
        name: str,
        *,
        output_directory: str | Path = "build/lib",
        output_file: str | Path | None = None,
    ) -> None:
        super().__init__(
            project,
            name,
            output_directory=output_directory,
            output_file=output_file,
        )

    @property
    def output_file(self) -> Path:
        if self.explicit_output_file is not None:
            return self.explicit_output_file
        return self.output_directory / f"lib{self.name}.a"

    def build(self) -> Path:
        print(f"BUILD {self.name} static library", flush=True)
        objects = self._compile()
        linker = Linker()
        linker.link_time_optimization = self.link_time_optimization and not self.project.debug
        linker.show_warnings = self.project.show_warnings
        self._built_output = linker.link_static_library(objects, self.output_file)
        return self._built_output


class Executable(_CppTarget):
    def __init__(
        self,
        project: Project,
        name: str,
        *,
        output_directory: str | Path = "build",
        output_file: str | Path | None = None,
    ) -> None:
        super().__init__(
            project,
            name,
            output_directory=output_directory,
            output_file=output_file,
        )
        self.static_runtime = False
        self.console_application = True
        self.system_libraries: list[str] = []
        self.library_directories: list[str | Path] = []
        self.linker_flags: list[str] = []
        self.static_libraries: list[StaticLibrary] = []

    @property
    def output_file(self) -> Path:
        if self.explicit_output_file is not None:
            return self.explicit_output_file
        suffix = ".exe" if os.name == "nt" else ""
        return self.output_directory / f"{self.name}{suffix}"

    def add_static_library(self, library: StaticLibrary) -> "Executable":
        self.static_libraries.append(library)
        return self

    def add_library(self, library_name: str) -> "Executable":
        self.system_libraries.append(library_name)
        return self

    def add_library_directory(self, path: str | Path) -> "Executable":
        self.library_directories.append(path)
        return self

    def add_linker_flag(self, flag: str) -> "Executable":
        self.linker_flags.append(flag)
        return self

    def build(self) -> Path:
        print(f"BUILD {self.name} executable", flush=True)
        objects = self._compile()

        inputs: list[Path] = list(objects)
        for library in self.static_libraries:
            inputs.append(library.build())

        linker = Linker()
        linker.link_time_optimization = self.link_time_optimization and not self.project.debug
        linker.static_runtime = self.static_runtime
        linker.console_application = self.console_application
        linker.show_warnings = self.project.show_warnings
        linker.library_directories.extend(self.library_directories)
        linker.flags.extend(self.linker_flags)

        self._built_output = linker.link_executable(
            inputs,
            self.output_file,
            self.system_libraries,
        )
        return self._built_output

    def run(
        self,
        *,
        wait: bool = True,
        timeout_seconds: float | None = None,
    ):
        executable = self._built_output or _resolve(self.output_file)
        if not executable.is_file():
            executable = self.build()
        return run_program(
            executable,
            wait=wait,
            timeout_seconds=timeout_seconds,
        )


def run_program(
    executable_file: str | Path,
    arguments: Iterable[str] = (),
    *,
    working_directory: str | Path | None = None,
    wait: bool = True,
    timeout_seconds: float | None = None,
):
    executable = _resolve(executable_file)
    if not executable.is_file():
        _fail(f"Executable does not exist: {_display(executable)}")

    cwd = _resolve(working_directory) if working_directory is not None else ROOT
    command = [str(executable), *map(str, arguments)]

    print(f"RUN  {_display(executable)}", flush=True)

    try:
        if wait:
            try:
                return_code = subprocess.call(command, cwd=cwd, shell=False, timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _fail(f"Program exceeded the bounded {timeout_seconds:g}s run limit.")
            if return_code != 0:
                unsigned_code = return_code & 0xFFFFFFFF
                detail = ""
                if unsigned_code == 0xC0000005:
                    detail = " (Windows access violation / invalid memory access, 0xC0000005)"
                elif unsigned_code == 0xC0000409:
                    detail = " (Windows stack buffer overrun / fast-fail, 0xC0000409)"
                _fail(f"Program exited with code {return_code}{detail}.", return_code)
            return return_code

        return subprocess.Popen(command, cwd=cwd, shell=False)
    except OSError as error:
        _fail(f"Could not start {_display(executable)}: {error}")


def run(
    executable_file: str | Path,
    arguments: Iterable[str] = (),
    *,
    working_directory: str | Path | None = None,
    wait: bool = True,
    timeout_seconds: float | None = None,
):
    """Backwards-compatible alias for run_program()."""
    return run_program(
        executable_file,
        arguments,
        working_directory=working_directory,
        wait=wait,
        timeout_seconds=timeout_seconds,
    )


def clean_directory(path: str | Path) -> None:
    directory = _resolve(path)
    if directory.exists():
        shutil.rmtree(directory)
    print(f"CLEAN {_display(directory)}", flush=True)
