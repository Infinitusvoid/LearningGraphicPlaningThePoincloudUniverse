from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence


# Default to the directory of the entry-point script for backwards compatibility.
# Project build scripts should call set_project_root(...) explicitly so the build
# API never has to guess which repository it is operating on.
ROOT = Path(sys.argv[0]).resolve().parent
_LOG_INITIALIZED = False


def set_project_root(path: str | Path) -> Path:
    """Set and return the root directory used for all relative build paths."""
    global ROOT, _LOG_INITIALIZED

    ROOT = Path(path).resolve()
    _LOG_INITIALIZED = False
    return ROOT


def project_root() -> Path:
    """Return the currently configured project root."""
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
    show_warnings: bool,
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

    if show_warnings and output:
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


class Compiler:
    def __init__(self) -> None:
        self.filepath = ""
        self.cpp_standard = CppStandard.CPP20
        self.optimization = Optimization.NONE
        self.debug_information = False
        self.link_time_optimization = False
        self.warnings = True
        self.show_warnings = False
        self.verbose = False
        self.force_recompile = False

        self.include_directories: list[str | Path] = []
        self.definitions: list[str] = []
        self.flags: list[str] = []

    def init(self, filepath: str = "") -> "Compiler":
        self.filepath = _find_tool(filepath or self.filepath, ("g++.exe", "g++"))
        return self

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

        command: list[str] = [
            self.filepath,
            f"-std={self.cpp_standard.value}",
            self.optimization.value,
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
            show_warnings=self.show_warnings,
        )

        _write_command_signature(command_file, command)
        return output


class CCompiler:
    """Small explicit C compiler companion for vendored C sources."""
    def __init__(self) -> None:
        self.filepath = ""
        self.optimization = Optimization.NONE
        self.debug_information = False
        self.link_time_optimization = False
        self.warnings = True
        self.show_warnings = False
        self.verbose = False
        self.force_recompile = False
        self.include_directories: list[str | Path] = []
        self.definitions: list[str] = []
        self.flags: list[str] = []

    def init(self, filepath: str = "") -> "CCompiler":
        self.filepath = _find_tool(filepath or self.filepath, ("gcc.exe", "gcc"))
        return self

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
        command: list[str] = [self.filepath, "-std=c11", self.optimization.value]
        if self.debug_information:
            command.append("-g3")
        if self.link_time_optimization:
            command.append("-flto")
        if self.warnings:
            command.extend(("-Wall", "-Wextra"))
        command.extend(f"-I{_resolve(path)}" for path in self.include_directories)
        command.extend(f"-D{definition}" for definition in self.definitions)
        command.extend(self.flags)
        command.extend(("-MMD", "-MF", str(depfile), "-MT", "p1_c_object", "-c", str(source), "-o", str(output)))
        needs_compile = self.force_recompile or not output.is_file()
        needs_compile = needs_compile or _command_changed(command_file, command) or _is_newer(source, output)
        if not needs_compile:
            dependencies = _read_dependencies(depfile)
            needs_compile = not dependencies or any(not dependency.is_file() or _is_newer(dependency, output) for dependency in dependencies)
        if not needs_compile:
            return output
        print(f"CC   {_display(source)}", flush=True)
        output.unlink(missing_ok=True)
        _run_command(f"Compile {_display(source)}", command, verbose=self.verbose, show_warnings=self.show_warnings)
        _write_command_signature(command_file, command)
        return output


class Linker:
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
            show_warnings=self.show_warnings,
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
            show_warnings=self.show_warnings,
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
