#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brave Tamer Shop Patcher - adds the "Chaos Flare" card to the in-game card shop.
Brave Tamer 商店修改工具 - 讓卡片店販售「カオスフレア」

Author: William Lin   作者：淋浴

Digimon Tamers: Brave Tamer is copyright Bandai / Akiyoshi Hongo / Toei
Animation.  This tool is unofficial and unaffiliated, and contains no ROM data.

Double-click to run.  Pick your own ROM, get a patched copy out.
This program contains NO ROM data; every change is computed at run time.

What it changes (all verifiable from the ROM itself):
  * ROM 0x3A7BFE is the card shop's stock pointer table: 6 far pointers,
    one per story-progress stage.
  * Each stock list is an array of 4-byte {LE16 category, LE16 index} entries
    terminated by FFFF.
  * The six lists sit back-to-back with no slack, so this tool copies each list
    into the blank region at 0x39994C, appends Chaos Flare, and rewrites the
    pointer table -> nothing existing is ever removed.
  * The price is not stored in the stock list: the shop looks it up from the
    species master table at 0x398720, so the card is sold at its own 3200 BIT.
  * Finally the WonderSwan header checksum (last 2 bytes = sum of all others)
    is recomputed.
"""

import os
import struct
import sys
import traceback

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    sys.exit("tkinter not found. Install the standard python.org build with tcl/tk enabled.")

APP_VERSION = "1.2"
APP_AUTHOR = "William Lin"        # used in English UI / bilingual splash
APP_AUTHOR_ZH = "淋浴"             # used in the Chinese UI

# ---------------------------------------------------------------- ROM layout
ROM_SIZE = 4 * 1024 * 1024
ROM_LINEAR_BIAS = 0x300000        # file offset = CPU linear address + this
SHOP_PTR_TABLE = 0x3A7BFE         # 6 far pointers {LE16 offset, LE16 segment}
SHOP_LIST_COUNT = 6
LIST_TERMINATOR = 0xFFFF
FREE_SPACE = 0x39994C             # ~26 KB of 0xFF after the species master table
PLUGIN_MASTER = 0x398514          # plug-in card master table (4 bytes each)
SPECIES_MASTER = 0x398720         # species master table (14 bytes each)

CARD_CATEGORIES = (               # (name, first card ID, count)
    ("item", 0, 33),
    ("summon", 33, 24),
    ("pfactor", 57, 101),
    ("plugin", 158, 131),
)

TARGET_CARD = 263                 # Chaos Flare = plug-in #105
TARGET_NAME = "カオスフレア"
TARGET_TECH = 290                 # technique / species ID = BlastBeelzebumon
KNOWN_CHECKSUM = 0x279D           # unmodified Japanese ROM

# ---------------------------------------------------------------- i18n
STRINGS = {
    "zh": {
        "lang_name": "繁體中文",
        "app_title": "Brave Tamer 商店修改工具",
        "lang_title": "選擇語言 / Language",
        "lang_prompt": "請選擇顯示語言",
        "heading": "讓卡片店販售「カオスフレア」",
        "intro": ("這張卡（ベルゼブモン ブラストモード 的必殺技）在原版遊戲中沒有任何取得途徑。"
                  "本工具會讓 Nanimon 卡片店的六個階段都販售它，售價為資料中原本的 3200 BIT，"
                  "且不會移除任何原有商品。\n"
                  "本程式不含 ROM 資料，請使用你自己的 ROM。"),
        "step1": " 步驟 1：選擇你的 ROM ",
        "step2": " 步驟 2：檢查結果 ",
        "step3_btn": "步驟 3：產生修改版 ROM…",
        "log_frame": " 記錄 ",
        "no_file": "（尚未選擇檔案）",
        "browse": "瀏覽…",
        "col_item": "項目",
        "col_result": "結果",
        "status_choose": "請先選擇 ROM 檔案。",
        "status_ok": "檢查通過，可以產生修改版。",
        "status_bad": "無法修改這個檔案。",
        "status_done": "完成！",
        "lang_switch": "語言 / Language：",
        "by": "作者：{a}",
        "author_name": "淋浴",
        # verification labels
        "v_size": "檔案大小",
        "v_header": "ROM 檔頭",
        "v_checksum": "檢查碼",
        "v_card": "{card} 卡片資料",
        "v_shop": "商店庫存表",
        "v_state": "目前狀態",
        # verification results
        "r_size_bad": "{n:,} bytes（應為 4,194,304）",
        "r_size_ok": "4 MB",
        "r_header_ok": "Bandai / WonderSwan Color / Game ID 0x1D",
        "r_header_bad": "publisher {p:02X} color {c:02X} id {g:02X}（與預期不符）",
        "r_sum_bad": "{stored:04X}（實際 {calc:04X}）不一致 — 可能是漢化版 ROM，修改時會自動修正",
        "r_sum_known": "{s:04X} — 未修改的原版 ROM",
        "r_sum_other": "{s:04X} — 檢查碼正確，但不是已知的原版（可能已被改過）",
        "r_card_missing": "未找到（X={x}）",
        "r_card_ok": "卡片 ID {id}、售價 {price} BIT、Rank {rank}",
        "r_shop_ok": "6 份清單：{sizes} 張",
        "r_state_patched": "{where}商店清單已經有這張卡 — 這份 ROM 已經改過了，不需要再改",
        "r_state_all": "全部 6 份",
        "r_state_some": "第 {list} 份",
        "r_state_ok": "尚未販售，可以修改",
        # errors
        "e_ptr": "第 {n} 份商店清單指標無效（0x{a:06X}）",
        "e_fmt": "第 {n} 份商店清單格式不符",
        "e_free": "0x{a:06X} 起的空白區已被占用，無法安全寫入",
        "e_outverify": "輸出檔驗證失敗，請回報這個狀況",
        "e_read": "無法讀取檔案：\n{e}",
        "e_same": "請不要覆蓋原始 ROM，換一個檔名吧。",
        "e_patch": "修改失敗：\n{e}",
        "e_unknown": "未知原因",
        # log
        "l_loaded": "已載入：{name}（{n:,} bytes）",
        "l_pass": "檢查通過。",
        "l_fail": "檢查未通過：{msg}",
        "l_start": "開始修改…",
        "l_list": "  第 {n} 份商店清單：{a} → {b} 張（搬移至 0x{off:06X}）",
        "l_sum": "  重算檔頭檢查碼：{s:04X}",
        "l_verified": "驗證：6 份清單都含有{card}，檢查碼 {s:04X} 正確。",
        "l_written": "已輸出：{path}\n",
        "l_failed": "失敗：{e}",
        # dialogs
        "dlg_open": "選擇 Brave Tamer ROM",
        "dlg_save": "儲存修改版 ROM",
        "ft_rom": "WonderSwan Color ROM",
        "ft_all": "所有檔案",
        "done_msg": ("完成！\n\n已輸出：\n{path}\n\n"
                     "卡片店（六個階段）都會販售「{card}」，售價 3200 BIT。\n\n"
                     "提示：買到後要到 Nanomon 的 D-Ark 商店，用「カード組み込み → プラグイン」"
                     "裝到數碼寶貝身上，戰鬥中才能用 Waza 施放。"),
    },
    "en": {
        "lang_name": "English",
        "app_title": "Brave Tamer Shop Patcher",
        "lang_title": "選擇語言 / Language",
        "lang_prompt": "Please choose a language",
        "heading": "Add “Chaos Flare” to the card shop",
        "intro": ("This card (BlastBeelzebumon's signature attack) has no way of being obtained "
                  "in the original game. This tool makes Nanimon's card shop sell it in all six "
                  "story stages, at the 3200 BIT price already defined in the game data, "
                  "without removing any existing item.\n"
                  "This program contains no ROM data - please use your own ROM."),
        "step1": " Step 1: Choose your ROM ",
        "step2": " Step 2: Verification ",
        "step3_btn": "Step 3: Create patched ROM…",
        "log_frame": " Log ",
        "no_file": "(no file selected)",
        "browse": "Browse…",
        "col_item": "Check",
        "col_result": "Result",
        "status_choose": "Select a ROM file to begin.",
        "status_ok": "Verified - ready to patch.",
        "status_bad": "This file cannot be patched.",
        "status_done": "Done!",
        "lang_switch": "語言 / Language: ",
        "by": "by {a}",
        "author_name": "William Lin",
        "v_size": "File size",
        "v_header": "ROM header",
        "v_checksum": "Checksum",
        "v_card": "{card} card data",
        "v_shop": "Shop stock tables",
        "v_state": "Current state",
        "r_size_bad": "{n:,} bytes (expected 4,194,304)",
        "r_size_ok": "4 MB",
        "r_header_ok": "Bandai / WonderSwan Color / Game ID 0x1D",
        "r_header_bad": "publisher {p:02X} color {c:02X} id {g:02X} (does not match)",
        "r_sum_bad": ("{stored:04X} (actual {calc:04X}) mismatch - likely a translated ROM; "
                      "it will be fixed when patching"),
        "r_sum_known": "{s:04X} - unmodified original ROM",
        "r_sum_other": "{s:04X} - valid, but not the known original (may already be modified)",
        "r_card_missing": "not found (X={x})",
        "r_card_ok": "card ID {id}, price {price} BIT, rank {rank}",
        "r_shop_ok": "6 lists: {sizes} cards",
        "r_state_patched": "{where} already contain this card - this ROM has already been patched",
        "r_state_all": "All 6 shop lists",
        "r_state_some": "Shop list(s) {list}",
        "r_state_ok": "Not sold yet - ready to patch",
        "e_ptr": "shop list {n} has an invalid pointer (0x{a:06X})",
        "e_fmt": "shop list {n} is malformed",
        "e_free": "the blank region at 0x{a:06X} is already in use - cannot write safely",
        "e_outverify": "output file failed verification - please report this",
        "e_read": "Cannot read the file:\n{e}",
        "e_same": "Please don't overwrite the original ROM - choose a different name.",
        "e_patch": "Patching failed:\n{e}",
        "e_unknown": "unknown reason",
        "l_loaded": "Loaded: {name} ({n:,} bytes)",
        "l_pass": "Verification passed.",
        "l_fail": "Verification failed: {msg}",
        "l_start": "Patching…",
        "l_list": "  Shop list {n}: {a} -> {b} cards (relocated to 0x{off:06X})",
        "l_sum": "  Recalculated header checksum: {s:04X}",
        "l_verified": "Verified: all 6 lists contain {card}, checksum {s:04X} is correct.",
        "l_written": "Written: {path}\n",
        "l_failed": "Failed: {e}",
        "dlg_open": "Choose your Brave Tamer ROM",
        "dlg_save": "Save patched ROM",
        "ft_rom": "WonderSwan Color ROM",
        "ft_all": "All files",
        "done_msg": ("Done!\n\nWritten to:\n{path}\n\n"
                     "The card shop now sells “{card}” in all six stages for 3200 BIT.\n\n"
                     "Tip: after buying it, go to Nanomon's D-Ark shop and use "
                     "“Card Insert -> Plug-in” to install it on a Digimon. "
                     "You can then use it in battle via Waza."),
    },
}


# ---------------------------------------------------------------- core logic
class PatchError(Exception):
    """Carries an already-localised message."""


def card_to_cat_idx(card_id):
    for cat, (_, base, count) in enumerate(CARD_CATEGORIES):
        if base <= card_id < base + count:
            return cat, card_id - base
    raise ValueError(f"card ID {card_id} out of range")


def cat_idx_to_card(cat, idx):
    return CARD_CATEGORIES[cat][1] + idx


def far_to_file(off, seg):
    return ((seg << 4) + off) + ROM_LINEAR_BIAS


def file_to_far(file_off):
    linear = file_off - ROM_LINEAR_BIAS
    if not (0x40000 <= linear < 0x100000):
        raise ValueError(f"0x{file_off:06X} is not reachable by a far pointer")
    return linear & 0xF, linear >> 4


def read_shop_lists(rom, S):
    """Return [(list file offset, [card ID, ...]), ...] - six entries."""
    lists = []
    for n in range(SHOP_LIST_COUNT):
        off, seg = struct.unpack_from("<HH", rom, SHOP_PTR_TABLE + 4 * n)
        base = far_to_file(off, seg)
        if not (0x340000 <= base < ROM_SIZE):
            raise PatchError(S["e_ptr"].format(n=n + 1, a=base))
        cards, k = [], 0
        while True:
            cat, idx = struct.unpack_from("<HH", rom, base + 4 * k)
            if cat == LIST_TERMINATOR:
                break
            if cat > 3 or idx >= CARD_CATEGORIES[cat][2] or k > 60:
                raise PatchError(S["e_fmt"].format(n=n + 1))
            cards.append(cat_idx_to_card(cat, idx))
            k += 1
        lists.append((base, cards))
    return lists


def verify_rom(rom, S):
    """Return (patchable, [(label, result, status)]).  status: ok / warn / bad"""
    rows = []
    if len(rom) != ROM_SIZE:
        rows.append((S["v_size"], S["r_size_bad"].format(n=len(rom)), "bad"))
        return False, rows
    rows.append((S["v_size"], S["r_size_ok"], "ok"))

    f = rom[-16:]
    publisher, color, game_id = f[6], f[7], f[8]
    if (publisher, color, game_id) != (0x01, 0x01, 0x1D):
        rows.append((S["v_header"],
                     S["r_header_bad"].format(p=publisher, c=color, g=game_id), "bad"))
        return False, rows
    rows.append((S["v_header"], S["r_header_ok"], "ok"))

    calc = sum(rom[:-2]) & 0xFFFF
    stored = struct.unpack_from("<H", rom, len(rom) - 2)[0]
    if calc != stored:
        # Fan translations often leave the header checksum stale.  The console
        # never checks it and patch_rom() recomputes it, so this is only a
        # warning; the structural checks below decide whether it is patchable.
        rows.append((S["v_checksum"], S["r_sum_bad"].format(stored=stored, calc=calc), "warn"))
    elif stored == KNOWN_CHECKSUM:
        rows.append((S["v_checksum"], S["r_sum_known"].format(s=stored), "ok"))
    else:
        rows.append((S["v_checksum"], S["r_sum_other"].format(s=stored), "warn"))

    card_label = S["v_card"].format(card=TARGET_NAME)
    x = struct.unpack_from("<H", rom, PLUGIN_MASTER + 105 * 4 + 2)[0]
    if x - 1 != TARGET_TECH:
        rows.append((card_label, S["r_card_missing"].format(x=x), "bad"))
        return False, rows
    price = struct.unpack_from("<H", rom, SPECIES_MASTER + TARGET_TECH * 14 + 2)[0]
    rank = rom[SPECIES_MASTER + TARGET_TECH * 14 + 4]
    rows.append((card_label,
                 S["r_card_ok"].format(id=TARGET_CARD, price=price, rank=rank), "ok"))

    try:
        lists = read_shop_lists(rom, S)
    except PatchError as e:
        rows.append((S["v_shop"], str(e), "bad"))
        return False, rows
    sizes = "、".join(str(len(c)) for _, c in lists) if S is STRINGS["zh"] \
        else ", ".join(str(len(c)) for _, c in lists)
    rows.append((S["v_shop"], S["r_shop_ok"].format(sizes=sizes), "ok"))

    already = [n + 1 for n, (_, c) in enumerate(lists) if TARGET_CARD in c]
    if already:
        where = (S["r_state_all"] if len(already) == SHOP_LIST_COUNT
                 else S["r_state_some"].format(list=", ".join(map(str, already))))
        rows.append((S["v_state"], S["r_state_patched"].format(where=where), "bad"))
        return False, rows
    rows.append((S["v_state"], S["r_state_ok"], "ok"))
    return True, rows


def patch_rom(rom, log, S):
    """Append TARGET_CARD to all six shop lists.  Returns the new ROM bytes."""
    rom = bytearray(rom)
    lists = read_shop_lists(rom, S)
    cursor = FREE_SPACE
    total = sum(len(c) + 1 for _, c in lists) * 4 + SHOP_LIST_COUNT * 4
    if any(b != 0xFF for b in rom[FREE_SPACE:FREE_SPACE + total]):
        raise PatchError(S["e_free"].format(a=FREE_SPACE))

    for n, (_, cards) in enumerate(lists):
        new_cards = cards + [TARGET_CARD]
        for i, c in enumerate(new_cards):
            struct.pack_into("<HH", rom, cursor + 4 * i, *card_to_cat_idx(c))
        struct.pack_into("<HH", rom, cursor + 4 * len(new_cards),
                         LIST_TERMINATOR, LIST_TERMINATOR)
        off, seg = file_to_far(cursor)
        struct.pack_into("<HH", rom, SHOP_PTR_TABLE + 4 * n, off, seg)
        log(S["l_list"].format(n=n + 1, a=len(cards), b=len(new_cards), off=cursor))
        cursor += len(new_cards) * 4 + 4

    checksum = sum(rom[:-2]) & 0xFFFF
    struct.pack_into("<H", rom, len(rom) - 2, checksum)
    log(S["l_sum"].format(s=checksum))
    return bytes(rom)


# ---------------------------------------------------------------- language picker
def center(win, w, h):
    win.update_idletasks()
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 3
    win.geometry(f"{w}x{h}+{x}+{y}")


def choose_language(root):
    """Startup language picker, drawn in the root window itself.

    Deliberately NOT a Toplevel: a transient dialog whose master is withdrawn
    is not shown by the Windows window manager, which would make the program
    look like it never started.
    """
    picked = {"lang": None}
    root.title(STRINGS["zh"]["lang_title"])
    root.resizable(False, False)
    center(root, 430, 210)

    body = ttk.Frame(root, padding=24)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="Brave Tamer Shop Patcher",
              font=("Segoe UI", 13, "bold")).pack()
    ttk.Label(body, text=f"v{APP_VERSION}  ·  by {APP_AUTHOR} / {APP_AUTHOR_ZH}",
              foreground="#777").pack(pady=(2, 0))
    ttk.Label(body, text="請選擇顯示語言  /  Please choose a language",
              foreground="#555").pack(pady=(10, 18))

    done = tk.BooleanVar(value=False)

    def pick(lang):
        picked["lang"] = lang
        done.set(True)

    btns = ttk.Frame(body)
    btns.pack()
    zh_btn = ttk.Button(btns, text="繁體中文", width=16, command=lambda: pick("zh"))
    en_btn = ttk.Button(btns, text="English", width=16, command=lambda: pick("en"))
    zh_btn.pack(side="left", padx=6)
    en_btn.pack(side="left", padx=6)
    zh_btn.focus_set()
    root.bind("<Return>", lambda e: pick("zh"))

    root.protocol("WM_DELETE_WINDOW", lambda: done.set(True))
    root.wait_variable(done)

    root.unbind("<Return>")
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    body.destroy()
    return picked["lang"]


# ---------------------------------------------------------------- main window
class PatcherApp:
    def __init__(self, root, lang):
        self.root = root
        self.lang = lang
        self.S = STRINGS[lang]
        self.rom_path = None
        self.rom_data = None
        self.can_patch = False
        self.build()

    # ---------------------------------------------------- layout
    def build(self):
        S = self.S
        for child in self.root.winfo_children():
            child.destroy()

        self.root.title(f"{S['app_title']} v{APP_VERSION}")
        self.root.resizable(True, True)
        self.root.minsize(640, 540)
        if not self.rom_data:                 # only re-centre on first build
            center(self.root, 700, 590)
        pad = {"padx": 12, "pady": 6}

        head = ttk.Frame(self.root)
        head.pack(fill="x", **pad)
        top = ttk.Frame(head)
        top.pack(fill="x")
        ttk.Label(top, text=S["heading"], font=("Segoe UI", 14, "bold")).pack(side="left")
        lang_box = ttk.Frame(top)
        lang_box.pack(side="right")
        ttk.Label(lang_box, text=S["lang_switch"], foreground="#555").pack(side="left")
        self.lang_var = tk.StringVar(value=STRINGS[self.lang]["lang_name"])
        combo = ttk.Combobox(lang_box, textvariable=self.lang_var, width=10,
                             state="readonly",
                             values=[STRINGS["zh"]["lang_name"], STRINGS["en"]["lang_name"]])
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", self.switch_language)
        ttk.Label(head, text=S["intro"], wraplength=660, justify="left",
                  foreground="#555").pack(anchor="w", pady=(6, 0))

        ttk.Separator(self.root).pack(fill="x", padx=12, pady=4)

        step1 = ttk.LabelFrame(self.root, text=S["step1"])
        step1.pack(fill="x", **pad)
        row = ttk.Frame(step1)
        row.pack(fill="x", padx=10, pady=10)
        self.path_var = tk.StringVar(value=self.rom_path or S["no_file"])
        ttk.Entry(row, textvariable=self.path_var, state="readonly").pack(
            side="left", fill="x", expand=True)
        ttk.Button(row, text=S["browse"], command=self.choose_rom).pack(side="left", padx=(8, 0))

        step2 = ttk.LabelFrame(self.root, text=S["step2"])
        step2.pack(fill="both", expand=True, **pad)
        self.tree = ttk.Treeview(step2, columns=("item", "result"), show="headings", height=7)
        self.tree.heading("item", text=S["col_item"])
        self.tree.heading("result", text=S["col_result"])
        self.tree.column("item", width=180, anchor="w", stretch=False)
        self.tree.column("result", width=460, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.tag_configure("ok", foreground="#0a7b34")
        self.tree.tag_configure("warn", foreground="#a86a00")
        self.tree.tag_configure("bad", foreground="#b00020")

        step3 = ttk.Frame(self.root)
        step3.pack(fill="x", **pad)
        self.patch_btn = ttk.Button(step3, text=S["step3_btn"], command=self.do_patch,
                                    state="normal" if self.can_patch else "disabled")
        self.patch_btn.pack(side="left")
        self.status = tk.StringVar(value=S["status_choose"])
        ttk.Label(step3, textvariable=self.status, foreground="#555").pack(side="left", padx=12)
        ttk.Label(step3, text=S["by"].format(a=S["author_name"]),
                  foreground="#888").pack(side="right")

        logf = ttk.LabelFrame(self.root, text=S["log_frame"])
        logf.pack(fill="both", expand=True, **pad)
        self.logbox = tk.Text(logf, height=7, wrap="word", state="disabled",
                              font=("Consolas", 9), background="#fafafa")
        self.logbox.pack(fill="both", expand=True, padx=10, pady=10)

        # re-run verification so the table matches the new language
        if self.rom_data is not None:
            self.run_verify()

    def switch_language(self, _event=None):
        chosen = self.lang_var.get()
        new = "zh" if chosen == STRINGS["zh"]["lang_name"] else "en"
        if new != self.lang:
            self.lang = new
            self.S = STRINGS[new]
            self.build()

    # ---------------------------------------------------- helpers
    def log(self, msg):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")
        self.root.update_idletasks()

    def set_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        for item, result, tag in rows:
            self.tree.insert("", "end", values=(item, result), tags=(tag,))

    def run_verify(self):
        try:
            ok, rows = verify_rom(self.rom_data, self.S)
        except Exception as e:
            ok, rows = False, [("Error", str(e), "bad")]
        self.set_rows(rows)
        self.can_patch = ok
        self.patch_btn.configure(state="normal" if ok else "disabled")
        self.status.set(self.S["status_ok"] if ok else self.S["status_bad"])
        return ok, rows

    # ---------------------------------------------------- actions
    def choose_rom(self):
        S = self.S
        path = filedialog.askopenfilename(
            title=S["dlg_open"],
            filetypes=[(S["ft_rom"], "*.wsc"), (S["ft_all"], "*.*")])
        if not path:
            return
        try:
            data = open(path, "rb").read()
        except OSError as e:
            messagebox.showerror(S["app_title"], S["e_read"].format(e=e))
            return

        self.rom_path, self.rom_data = path, data
        self.path_var.set(path)
        self.log(S["l_loaded"].format(name=os.path.basename(path), n=len(data)))

        ok, rows = self.run_verify()
        if ok:
            self.log(S["l_pass"])
        else:
            bad = next((r for r in rows if r[2] == "bad"), None)
            self.log(S["l_fail"].format(msg=bad[1] if bad else S["e_unknown"]))

    def do_patch(self):
        S = self.S
        if not self.can_patch or self.rom_data is None:
            return
        stem, ext = os.path.splitext(os.path.basename(self.rom_path))
        out = filedialog.asksaveasfilename(
            title=S["dlg_save"],
            initialfile=f"{stem} (ChaosFlare in shop){ext or '.wsc'}",
            initialdir=os.path.dirname(self.rom_path),
            defaultextension=ext or ".wsc",
            filetypes=[(S["ft_rom"], "*.wsc"), (S["ft_all"], "*.*")])
        if not out:
            return
        if os.path.abspath(out) == os.path.abspath(self.rom_path):
            messagebox.showerror(S["app_title"], S["e_same"])
            return
        try:
            self.log(S["l_start"])
            patched = patch_rom(self.rom_data, self.log, S)
            with open(out, "wb") as fh:
                fh.write(patched)
            check = open(out, "rb").read()
            lists = read_shop_lists(check, S)
            n_ok = sum(1 for _, c in lists if TARGET_CARD in c)
            calc = sum(check[:-2]) & 0xFFFF
            stored = struct.unpack_from("<H", check, len(check) - 2)[0]
            if n_ok != SHOP_LIST_COUNT or calc != stored:
                raise PatchError(S["e_outverify"])
            self.log(S["l_verified"].format(card=TARGET_NAME, s=stored))
            self.log(S["l_written"].format(path=out))
            self.status.set(S["status_done"])
            messagebox.showinfo(S["app_title"],
                                S["done_msg"].format(path=out, card=TARGET_NAME))
        except Exception as e:
            self.log(S["l_failed"].format(e=e))
            messagebox.showerror(S["app_title"], S["e_patch"].format(e=e))


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    lang = choose_language(root)
    if lang is None:                          # user closed the picker
        root.destroy()
        return
    PatcherApp(root, lang)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            messagebox.showerror("Brave Tamer Shop Patcher", traceback.format_exc())
        except Exception:
            traceback.print_exc()
