# Paint Puzzle

**方块染色解谜** · A strategy color-painting puzzle game built with **Python + pygame**.

> **[English](README.md)** · **[中文](README.zh-CN.md)**

## ⬇️ Downloads

| Platform | File | Release |
|---|---|---|
| **Windows** (Python + pygame) | `PaintPuzzle-Setup.exe` | [v2.3](https://github.com/Fatallove101/paint-puzzle/releases/tag/v2.3) |
| **Android** (Godot 4 port) | `PaintPuzzle-Android-v2.4.0.apk` | [v2.4.0-android](https://github.com/Fatallove101/paint-puzzle/releases/tag/v2.4.0-android) |

Two editions share the same puzzle rules: the original **Python + pygame** desktop game (`paint_puzzle/`) and a **Godot 4 touch port for Android** (`paint_puzzle_godot/`).

Paint one whole row or column at a time. Later strokes overwrite earlier ones, so you have to think backwards to reproduce the target pattern within a limited number of moves.

![icon](paint_puzzle/icon.png)

## Features

- **Start menu** with *Continue* (auto-saved progress), *Settings* (sound on/off) and *Exit*
- **Two difficulties**
  - Easy: choose colors from a palette before painting
  - Hard: brushes carry random colors (with a limited number of manual "recolor" uses)
- **Level selection** for the 10 built-in levels; levels 11+ are procedurally generated & guaranteed solvable
- **Hint system** built on a reverse solver — following the hints always solves the level; dead-ends auto-reset
- **Undo** (`Ctrl+Z`), **Retry**
- **Resizable window** (drag edges) and **fullscreen** (`F11`), with smooth scaling
- **GUI installer** (Inno Setup): per-user install, desktop/shortcut, uninstall entry in *Settings → Apps*
- Custom 2×2 color-block icon and synthesized sound effects

## Requirements

- Windows 10 / 11
- To run from source: **Python 3.14** + **pygame-ce** (`pip install pygame-ce`)
- Or install via the built installer / prebuilt exe (no Python needed)

## Run from source

```bash
python src/main.py
```

## Controls

| Action | Input |
|---|---|
| Paint row / column | Left-click a brush |
| Pick color (Easy) | Click a palette chip |
| Hint | Click the `提示` button |
| Undo | `Ctrl+Z` or the `撤销` button |
| Back to menu | `ESC` |
| Fullscreen / Window | `F11` |
| Resize window | Drag the window edges |

## Packaging

Build the standalone game (PyInstaller, onedir):

```bash
python -m PyInstaller --noconfirm --clean --noupx --noconsole \
  --name "方块染色解谜" --icon icon.ico \
  --add-data "snd;snd" --add-data "icon.ico;." --add-data "icon.png;." src\main.py
```

Build the installer (needs Inno Setup 6 + `installer\ChineseSimplified.isl`):

```bash
ISCC.exe installer\方块染色解谜.iss
# -> installer_out\方块染色解谜-Setup.exe
```

## Build the Android APK

Requires [Godot 4.x](https://godotengine.org/) (with Android export templates), JDK 17 and the Android SDK (command-line tools are enough). Then:

1. copy `paint_puzzle_godot/export_presets.cfg.example` to `export_presets.cfg` and fill in your keystore paths/passwords;
2. set the Android SDK / JDK paths in Godot's editor settings;
3. run the logic self-test: `godot --headless --path paint_puzzle_godot --script res://tests/logic_test.gd`
4. export: `godot --headless --path paint_puzzle_godot --export-release "Android" build/PaintPuzzle-release.apk`

> Tip: in Godot's editor settings, existing (empty or wrong) `export/android/*` keys are **not** overwritten by simply appending — replace those lines when configuring a new machine.

## License

[MIT](LICENSE)
