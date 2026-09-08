# Paint Puzzle

**方块染色解谜** · A strategy color-painting puzzle game built with **Python + pygame**.

> **[English](README.md)** · **[中文](README.zh-CN.md)**

> **⬇️ Download the Windows installer:** [paint-puzzle **v2.3**](https://github.com/Fatallove101/paint-puzzle/releases/latest) · `PaintPuzzle-Setup.exe`

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

## License

[MIT](LICENSE)
