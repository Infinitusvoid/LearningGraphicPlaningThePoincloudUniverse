# Lesson: Executable Location vs Working Directory

While testing the program, I noticed something interesting:

- When the application was started through `build.py`, the generated `test.png` appeared in the **project directory**.
- When I opened `build/application.exe` directly from Windows Explorer, the generated `test.png` appeared in the **build directory beside the executable**.

At first this can look inconsistent, but the important idea is:

> A relative file path is resolved from the program's **current working directory**, not necessarily from the directory containing the executable.

---

## Example

The application contains something conceptually like:

```cpp
save(image, "test.png");
```

`"test.png"` is a **relative path**.

It does not say:

```text
C:/SomeProject/test.png
```

or:

```text
C:/SomeProject/build/test.png
```

It only says:

> Create `test.png` relative to wherever the program is currently working.

---

## When the build script launches the application

Suppose the project looks like this:

```text
MyProject/
    application/
    build/
        application.exe
    build.py
    build_api.py
```

The build system can launch:

```text
build/application.exe
```

while explicitly setting the working directory to:

```text
MyProject/
```

Then:

```cpp
save(image, "test.png");
```

becomes:

```text
MyProject/test.png
```

Even though the executable itself is physically located at:

```text
MyProject/build/application.exe
```

The executable location and the working directory are two different things.

---

## When I launch the executable from Explorer

If I open:

```text
MyProject/build/application.exe
```

directly from Windows Explorer, the working directory is typically the directory containing the executable:

```text
MyProject/build/
```

Now the same code:

```cpp
save(image, "test.png");
```

creates:

```text
MyProject/build/test.png
```

The C++ code did not change.

What changed was the **working directory from which the program was launched**.

---

## The mental model

Think of these as two independent paths:

```text
Executable location
    MyProject/build/application.exe

Current working directory
    MyProject/
```

or:

```text
Executable location
    MyProject/build/application.exe

Current working directory
    MyProject/build/
```

A relative path such as:

```text
test.png
```

uses the second one: the **current working directory**.

---

## This affects more than image saving

The same rule applies to things such as:

```cpp
std::ifstream("settings.json");
stbi_load("texture.png", ...);
fopen("data.txt", "rb");
save(image, "output.png");
```

All of these paths are relative to the current working directory unless an absolute path is used.

So this can affect:

- loading textures,
- loading configuration files,
- saving screenshots,
- writing logs,
- loading shaders,
- reading game data,
- saving user-created files.

---

## Why this matters

A program may behave differently depending on how it is launched:

```text
build.py
Visual Studio
Command Prompt
Windows Explorer
another launcher
```

Each launcher can choose a different working directory.

Therefore:

> Do not assume that the executable's directory and the current working directory are always the same.

For small experiments, using relative paths is perfectly fine.

For larger applications, it is often better to deliberately decide where different kinds of files belong, for example:

```text
MyProject/
    build/
        application.exe

    output/
        screenshots/
        generated_images/

    data/
        textures/
        shaders/
```

Then the application can construct those paths deliberately instead of depending accidentally on how it happened to be launched.

---

## The lesson I noticed

The useful discovery was not simply that the image appeared in two different folders.

It revealed an important runtime concept:

```text
Where the executable lives
            !=
Where the program is currently working
```

And:

```text
relative path
    +
current working directory
    =
actual file location
```

That is the rule to remember.
