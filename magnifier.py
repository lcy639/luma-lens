"""Luma Lens — a portable Windows screen magnifier."""
import ctypes
import ctypes.wintypes
import datetime as dt
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageDraw, ImageEnhance, ImageGrab, ImageOps, ImageTk


ctypes.windll.shcore.SetProcessDpiAwareness(2)
USER32 = ctypes.windll.user32
BG = "#10141d"
PANEL = "#1b2230"
PANEL2 = "#252e3d"
FG = "#f5f7fc"
MUTED = "#98a5b9"
ACCENT = "#79e4c7"
CHROMA = "#010203"
FONT = "Segoe UI"


def button(parent, text, command, color=PANEL2, fg=FG, width=None):
    b = tk.Button(parent, text=text, command=command, bg=color, fg=fg,
                  activebackground="#354254", activeforeground=FG,
                  relief="flat", bd=0, padx=13, pady=9, cursor="hand2",
                  font=(FONT, 10, "bold"), width=width)
    return b


class Magnifier:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Luma Lens · 屏幕放大镜")
        self.root.configure(bg=BG)
        self.root.geometry("760x590")
        self.root.minsize(520, 400)
        self.zoom = tk.DoubleVar(value=3.0)
        self.size = tk.IntVar(value=280)
        self.opacity = tk.DoubleVar(value=100)
        self.mode = tk.StringVar(value="原色")
        self.shape = tk.StringVar(value="圆形")
        self.show_cross = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=False)
        self.follow = tk.BooleanVar(value=True)
        self.frozen = False
        self.visible = True
        self.image = None
        self.tk_preview = None
        self.tk_lens = None
        self.last_mouse = (-1, -1)
        self.hotkeys = []
        self.build_ui()
        self.make_lens()
        self.register_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda _event: self.close())
        self.root.after(60, self.tick)

    def build_ui(self):
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True)
        self.scroll = tk.Canvas(shell, bg=BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(shell, orient="vertical", command=self.scroll.yview)
        self.scroll.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.scroll.pack(side="left", fill="both", expand=True)
        content = tk.Frame(self.scroll, bg=BG)
        content_id = self.scroll.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda _e: self.scroll.configure(scrollregion=self.scroll.bbox("all")))
        self.scroll.bind("<Configure>", lambda e: self.on_width(e.width, content_id))
        self.root.bind_all("<MouseWheel>", self.on_wheel)

        top = tk.Frame(content, bg=BG)
        top.pack(fill="x", padx=22, pady=(18, 11))
        tk.Label(top, text="◉", fg=ACCENT, bg=BG, font=(FONT, 29)).pack(side="left")
        title = tk.Frame(top, bg=BG)
        title.pack(side="left", padx=12)
        tk.Label(title, text="LUMA LENS", fg=FG, bg=BG, font=(FONT, 21, "bold")).pack(anchor="w")
        tk.Label(title, text="清晰看见屏幕上的每个细节", fg=MUTED, bg=BG, font=(FONT, 10)).pack(anchor="w")
        self.status = tk.Label(top, text="●  实时放大中", fg=ACCENT, bg=PANEL,
                               padx=12, pady=8, font=(FONT, 9, "bold"))
        self.status.pack(side="right")

        preview_card = tk.Frame(content, bg=PANEL)
        preview_card.pack(fill="x", padx=22, pady=(0, 11))
        head = tk.Frame(preview_card, bg=PANEL)
        head.pack(fill="x", padx=17, pady=(13, 8))
        tk.Label(head, text="实时预览", bg=PANEL, fg=FG, font=(FONT, 11, "bold")).pack(side="left")
        self.coords = tk.Label(head, text="等待捕获", bg=PANEL, fg=MUTED, font=(FONT, 9))
        self.coords.pack(side="right")
        self.preview = tk.Canvas(preview_card, bg="#0c1018", highlightthickness=0, height=185)
        self.preview.pack(fill="x", padx=17, pady=(0, 15))

        controls = tk.Frame(content, bg=BG)
        controls.pack(fill="x", padx=22)
        self.controls = controls
        left = tk.Frame(controls, bg=PANEL, padx=18, pady=14)
        left.pack(side="left", fill="both", expand=True, padx=(0, 7))
        right = tk.Frame(controls, bg=PANEL, padx=18, pady=14)
        right.pack(side="left", fill="both", expand=True, padx=(7, 0))
        self.control_left, self.control_right = left, right
        self.stacked = False
        self.slider(left, "放大倍率", self.zoom, 1.5, 12, "×")
        self.slider(left, "镜片尺寸", self.size, 160, 480, " px")
        self.slider(left, "镜片透明度", self.opacity, 35, 100, "%")
        self.choice(right, "显示效果", self.mode, ["原色", "黑白", "反色", "高对比度"])
        self.choice(right, "镜片形状", self.shape, ["圆形", "方形"])
        toggles = tk.Frame(right, bg=PANEL)
        toggles.pack(fill="x", pady=(10, 0))
        for label, var in [("十字准线", self.show_cross), ("像素网格", self.show_grid), ("跟随鼠标", self.follow)]:
            tk.Checkbutton(toggles, text=label, variable=var, bg=PANEL, fg=FG,
                           selectcolor=PANEL2, activebackground=PANEL, activeforeground=FG,
                           font=(FONT, 9), cursor="hand2").pack(side="left")

        actions = tk.Frame(content, bg=BG)
        actions.pack(fill="x", padx=22, pady=(12, 8))
        self.freeze_button = button(actions, "❚❚  冻结画面", self.toggle_freeze, ACCENT, BG)
        self.freeze_button.pack(side="left", padx=(0, 8))
        self.lens_button = button(actions, "◉  隐藏镜片", self.toggle_lens)
        self.lens_button.pack(side="left", padx=(0, 8))
        button(actions, "↓  保存截图", self.save).pack(side="left")
        self.hint = tk.Label(content, text="快捷键  Ctrl + Alt + ↑ / ↓ 调整倍率    F8 冻结    F9 显示/隐藏    Esc 退出",
                             bg=BG, fg=MUTED, font=(FONT, 9), justify="center")
        self.hint.pack(padx=20, pady=(0, 14))

    def on_width(self, width, content_id):
        self.scroll.itemconfigure(content_id, width=width)
        self.hint.configure(wraplength=max(300, width-40))
        should_stack = width < 690
        if should_stack != self.stacked:
            self.control_left.pack_forget()
            self.control_right.pack_forget()
            if should_stack:
                self.control_left.pack(side="top", fill="x", pady=(0, 8))
                self.control_right.pack(side="top", fill="x")
            else:
                self.control_left.pack(side="left", fill="both", expand=True, padx=(0, 7))
                self.control_right.pack(side="left", fill="both", expand=True, padx=(7, 0))
            self.stacked = should_stack

    def on_wheel(self, event):
        if event.widget.winfo_toplevel() == self.root:
            self.scroll.yview_scroll(-int(event.delta / 120), "units")

    def slider(self, parent, title, variable, low, high, suffix):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x")
        tk.Label(row, text=title, bg=PANEL, fg=FG, font=(FONT, 9, "bold")).pack(side="left")
        value = tk.Label(row, bg=PANEL, fg=ACCENT, font=(FONT, 9, "bold"))
        value.pack(side="right")
        def update(*_):
            n = variable.get()
            value.config(text=(f"{n:.1f}" if suffix == "×" else str(round(n))) + suffix)
            if hasattr(self, "lens"):
                self.resize_lens()
        variable.trace_add("write", update)
        update()
        tk.Scale(parent, from_=low, to=high, resolution=.1 if suffix == "×" else 1,
                 variable=variable, orient="horizontal", showvalue=False, bg=PANEL,
                 fg=ACCENT, troughcolor=PANEL2, activebackground=ACCENT,
                 highlightthickness=0, bd=0, sliderrelief="flat").pack(fill="x", pady=(0, 3))

    def choice(self, parent, title, variable, values):
        tk.Label(parent, text=title, bg=PANEL, fg=FG, font=(FONT, 9, "bold")).pack(anchor="w")
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=(6, 10))
        buttons = []
        def select(v):
            variable.set(v)
            for b, name in buttons:
                b.config(bg=ACCENT if name == v else PANEL2, fg=BG if name == v else FG)
            if variable is self.shape and hasattr(self, "lens"):
                self.resize_lens()
        for v in values:
            b = button(row, v, lambda x=v: select(x))
            b.config(font=(FONT, 8), padx=7, pady=6)
            b.pack(side="left", padx=(0, 5))
            buttons.append((b, v))
        select(variable.get())

    def make_lens(self):
        self.lens = tk.Toplevel(self.root)
        self.lens.overrideredirect(True)
        self.lens.attributes("-topmost", True)
        self.lens.configure(bg=CHROMA)
        self.lens.attributes("-transparentcolor", CHROMA)
        self.lens_canvas = tk.Canvas(self.lens, bg=CHROMA, highlightthickness=0)
        self.lens_canvas.pack(fill="both", expand=True)
        self.lens_canvas.bind("<ButtonPress-1>", self.drag_start)
        self.lens_canvas.bind("<B1-Motion>", self.drag)
        self.resize_lens()

    def resize_lens(self):
        n = self.size.get()
        self.lens.geometry(f"{n}x{n}")
        self.lens.attributes("-alpha", self.opacity.get() / 100)

    def drag_start(self, event):
        self.follow.set(False)
        self.drag_offset = (event.x_root - self.lens.winfo_x(), event.y_root - self.lens.winfo_y())

    def drag(self, event):
        x, y = self.drag_offset
        self.lens.geometry(f"+{event.x_root-x}+{event.y_root-y}")

    def capture(self, x, y):
        n = self.size.get()
        radius = max(8, round(n / self.zoom.get() / 2))
        box = (x-radius, y-radius, x+radius, y+radius)
        shot = ImageGrab.grab(bbox=box, all_screens=True).convert("RGB")
        shot = shot.resize((n, n), Image.Resampling.NEAREST if self.zoom.get() >= 6 else Image.Resampling.LANCZOS)
        effect = self.mode.get()
        if effect == "黑白":
            shot = ImageOps.grayscale(shot).convert("RGB")
        elif effect == "反色":
            shot = ImageOps.invert(shot)
        elif effect == "高对比度":
            shot = ImageEnhance.Contrast(shot).enhance(2.2)
            shot = ImageEnhance.Sharpness(shot).enhance(1.5)
        return shot

    def render(self):
        if self.image is None:
            return
        n = self.size.get()
        lens_image = self.image
        if self.shape.get() == "圆形":
            mask = Image.new("L", (n, n), 0)
            ImageDraw.Draw(mask).ellipse((2, 2, n-3, n-3), fill=255)
            lens_image = Image.new("RGB", (n, n), CHROMA)
            lens_image.paste(self.image, (0, 0), mask)
        self.tk_lens = ImageTk.PhotoImage(lens_image)
        c = self.lens_canvas
        c.delete("all")
        c.create_image(0, 0, image=self.tk_lens, anchor="nw")
        if self.shape.get() == "圆形":
            c.create_oval(2, 2, n-2, n-2, outline=ACCENT, width=3)
        else:
            c.create_rectangle(2, 2, n-2, n-2, outline=ACCENT, width=3)
        if self.show_grid.get() and self.zoom.get() >= 5:
            step = max(8, int(self.zoom.get()))
            for p in range(n//2 % step, n, step):
                c.create_line(p, 0, p, n, fill="#ffffff", stipple="gray12")
                c.create_line(0, p, n, p, fill="#ffffff", stipple="gray12")
        if self.show_cross.get():
            mid = n//2
            c.create_line(mid-17, mid, mid+17, mid, fill=ACCENT, width=2)
            c.create_line(mid, mid-17, mid, mid+17, fill=ACCENT, width=2)
        w = max(1, self.preview.winfo_width())
        h = max(1, self.preview.winfo_height())
        scale = min(w/n, h/n)
        pw, ph = max(1, int(n*scale)), max(1, int(n*scale))
        self.tk_preview = ImageTk.PhotoImage(self.image.resize((pw, ph), Image.Resampling.LANCZOS))
        self.preview.delete("all")
        self.preview.create_image(w//2, h//2, image=self.tk_preview)
        if self.show_cross.get():
            self.preview.create_line(w//2-15, h//2, w//2+15, h//2, fill=ACCENT, width=2)
            self.preview.create_line(w//2, h//2-15, w//2, h//2+15, fill=ACCENT, width=2)

    def tick(self):
        try:
            self.process_hotkeys()
            point = ctypes.wintypes.POINT()
            USER32.GetCursorPos(ctypes.byref(point))
            x, y = point.x, point.y
            if not self.frozen:
                self.image = self.capture(x, y)
                self.coords.config(text=f"X {x}   Y {y}   ·   {self.zoom.get():.1f}×")
            if self.follow.get() and self.visible:
                n = self.size.get()
                sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
                lx = x+32 if x+n+42 < sw else x-n-32
                ly = y+32 if y+n+42 < sh else y-n-32
                self.lens.geometry(f"+{lx}+{ly}")
            self.lens.attributes("-alpha", self.opacity.get()/100)
            self.render()
        except Exception as exc:
            self.status.config(text=f"●  捕获失败: {str(exc)[:35]}", fg="#ff9e9e")
        self.root.after(80, self.tick)

    def toggle_freeze(self):
        self.frozen = not self.frozen
        self.freeze_button.config(text="▶  继续放大" if self.frozen else "❚❚  冻结画面")
        self.status.config(text="●  画面已冻结" if self.frozen else "●  实时放大中")

    def toggle_lens(self):
        self.visible = not self.visible
        if self.visible:
            self.lens.deiconify()
        else:
            self.lens.withdraw()
        self.lens_button.config(text="◉  隐藏镜片" if self.visible else "◉  显示镜片")

    def save(self):
        if self.image is None:
            return
        name = "LumaLens_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        path = filedialog.asksaveasfilename(parent=self.root, initialfile=name,
                                            defaultextension=".png", filetypes=[("PNG 图片", "*.png")])
        if path:
            self.image.save(path)
            self.status.config(text="●  截图已保存")

    def register_hotkeys(self):
        for ident, modifiers, key in [(1, 0x0003, 0x26), (2, 0x0003, 0x28),
                                      (3, 0, 0x77), (4, 0, 0x78)]:
            if USER32.RegisterHotKey(None, ident, modifiers, key):
                self.hotkeys.append(ident)

    def process_hotkeys(self):
        msg = ctypes.wintypes.MSG()
        while USER32.PeekMessageW(ctypes.byref(msg), None, 0x0312, 0x0312, 1):
            if msg.wParam == 1:
                self.zoom.set(min(12, round(self.zoom.get()+.5, 1)))
            elif msg.wParam == 2:
                self.zoom.set(max(1.5, round(self.zoom.get()-.5, 1)))
            elif msg.wParam == 3:
                self.toggle_freeze()
            elif msg.wParam == 4:
                self.toggle_lens()

    def close(self):
        for ident in self.hotkeys:
            USER32.UnregisterHotKey(None, ident)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Magnifier().run()
