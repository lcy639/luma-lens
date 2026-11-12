# Luma Lens 屏幕放大镜

Windows 屏幕放大镜。悬浮镜片可以跟随鼠标，也可以拖动到固定位置。支持调节倍率、镜片大小、透明度、显示效果、十字准线和像素网格。

## 安装和运行

需要带 Tkinter 的 Windows Python 3.10 或更新版本。

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\magnifier.py
```

安装后也可双击 `launch.bat`。若系统只有 `python` 命令，可用 `python -m venv .venv` 完成第一步。

- `F8` 冻结或恢复画面。
- `F9` 显示或隐藏悬浮镜片。
- `Ctrl+Alt+↑/↓` 调整倍率。
- 点「保存截图」可把放大画面保存为 PNG。

某些受保护窗口和独占全屏应用可能无法被 Windows 捕获。

## 许可证

[MIT](LICENSE)
