# 方块染色解谜 Paint Puzzle

基于 **Python + pygame** 的策略类颜色染色解谜游戏。

每次把**整行或整列**染成一种颜色,后染的会覆盖先染的,所以你得像"倒推"一样思考,在限定步数内把棋盘染成与目标图案完全一致。

![icon](paint_puzzle/icon.png)

> **[English](README.md)** · **中文**

## ⬇️ 下载

| 平台 | 文件 | 发布页 |
|---|---|---|
| **Windows**(Python + pygame) | `PaintPuzzle-Setup.exe` | [v2.3](https://github.com/Fatallove101/paint-puzzle/releases/tag/v2.3) |
| **Android**(Godot 4 移植版) | `PaintPuzzle-Android-v2.3.1.apk` | [v2.3.1-android](https://github.com/Fatallove101/paint-puzzle/releases/tag/v2.3.1-android) |

两个版本玩法规则一致:原版是 **Python + pygame** 桌面版(`paint_puzzle/`),手机版是 **Godot 4 触控移植版**(`paint_puzzle_godot/`)。

## 特性

- **主菜单**:**继续游戏**(自动保存进度)、**设置**(音效开关)、**退出游戏**
- **两种难度**
  - 简单:先从色板选一种颜色,再点行/列画刷染色
  - 困难:每支笔刷颜色随机(还有有限次数的"改色"可手动指定)
- **关卡选择**:前 10 关固定图案;第 11 关起**程序化无限生成**且保证可解
- **提示系统**(基于反推求解器):照着提示操作必能通关;死局自动重置
- **撤销**(`Ctrl+Z`)、**重试**
- **窗口可拖拽缩放**、**全屏**(`F11`),平滑缩放,文字清晰
- **GUI 安装包**(Inno Setup):按用户安装、创建快捷方式、可到 *设置→应用* 卸载
- 定制 2×2 色块图标、程序合成音效

## 环境要求

- Windows 10 / 11
- 源码运行:**Python 3.14** + **pygame-ce**(`pip install pygame-ce`)
- 或直接使用打包好的安装包(无需装 Python)

## 从源码运行

```bash
python src/main.py
```

## 操作说明

| 操作 | 按键/方式 |
|---|---|
| 染整行/列 | 左键点击对应画刷 |
| 选颜色(简单) | 点击色板色块 |
| 提示 | 点"提示"按钮 |
| 撤销 | `Ctrl+Z` 或点"撤销"按钮 |
| 返回主菜单 | `ESC` |
| 全屏/窗口 | `F11` |
| 调整窗口大小 | 拖动窗口边缘 |

## 打包

打包独立游戏(PyInstaller,目录版):

```bash
python -m PyInstaller --noconfirm --clean --noupx --noconsole \
  --name "方块染色解谜" --icon icon.ico \
  --add-data "snd;snd" --add-data "icon.ico;." --add-data "icon.png;." src\main.py
```

打包安装包(需要 Inno Setup 6 + `installer\ChineseSimplified.isl`):

```bash
ISCC.exe installer\方块染色解谜.iss
# 产物:installer_out\方块染色解谜-Setup.exe
```

## 截图

(运行后截图可放这里,README 会更直观。)

## 构建 Android APK

需要 [Godot 4.x](https://godotengine.org/)(含 Android 导出模板)、JDK 17、Android SDK(命令行工具即可)。步骤:

1. 把 `paint_puzzle_godot/export_presets.cfg.example` 复制为 `export_presets.cfg`,填入你的签名密钥路径与密码;
2. 在 Godot 编辑器设置里填好 Android SDK / JDK 路径;
3. 跑逻辑自测:`godot --headless --path paint_puzzle_godot --script res://tests/logic_test.gd`
4. 导出:`godot --headless --path paint_puzzle_godot --export-release "Android" build/PaintPuzzle-release.apk`

> 提示:Godot 编辑器设置里**已存在**的 `export/android/*`(可能是空值或错误路径)不会因为"追加"而生效,换机器配置时需要**替换**那几行。

## 许可协议

[MIT](LICENSE)
