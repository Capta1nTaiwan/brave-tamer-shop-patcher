# Brave Tamer Shop Patcher

**Unlocks "Chaos Flare" (カオスフレア) — a card that exists in *Digimon Tamers: Brave Tamer* but can never be obtained.**

A small Windows tool that patches **your own** copy of the WonderSwan Color game so Nanimon's card shop finally sells it. Bilingual UI (繁體中文 / English). **Contains no ROM data.**

[English](#english) · [中文](#中文)

---

## English

### The finding

`カオスフレア` (Chaos Flare) is BlastBeelzebumon's signature attack, available as a plug-in card. It is **fully defined** in the retail ROM — name, description text, price (3200 BIT), Rank 6, Virus attribute, "damages all enemies", even its own card-fusion results.

And it is **impossible to obtain**. Three independent checks, all confirmed against the ROM:

| Route | Result |
|---|---|
| **Card shop** | Not present in any of the 6 shop stock lists |
| **Card Jogress** (fusion) | No combination in the 310-entry fusion table produces it |
| **Scan → Convert** | BlastBeelzebumon is **1 of only 2 species (out of 310) with all-zero battle stats** — it never appears as an enemy, so it can never be scanned |

Every real enemy and boss in the game (including the VR- clones, Armagemon, Diablomon, Mephistomon, Pharaohmon) has non-zero stats. This card is leftover content with no path to the player.

This tool creates that path.

### What it does

Adds the card to **all six** shop stock lists — one per story stage — **without removing anything**. It sells at the 3200 BIT price already present in the game data.

- Your original ROM is never modified; a patched copy is written alongside it.
- The input file is verified first (size, header, checksum, card data, shop table structure). A wrong game or an already-patched file is refused.
- The WonderSwan header checksum is recomputed, so the ROM stays valid.
- About **636 bytes** change in total.
- Patched ROMs remain compatible with existing save files.

### Usage

1. Download `BraveTamer_ShopPatcher.exe` from [Releases](../../releases)
2. Run it and pick a language
3. **Browse…** → select your own ROM (`.wsc`, 4 MB)
4. Check that every verification row passes
5. **Create patched ROM…** → choose an output filename

> The `.exe` is unsigned, so Windows SmartScreen may warn you — *More info → Run anyway*. Some antivirus products also false-positive on PyInstaller builds.

### Using the card in game

Chaos Flare is a **plug-in card** (a technique), not something you play directly in battle:

1. Buy it at Nanimon's card shop (3200 BIT)
2. Nanomon's D-Ark shop → **Card Insert → Plug-in** → install it on a Digimon
   *(max 5 per Digimon; the Digimon must not be injured)*
3. In battle: **Command → Waza → カオスフレア**

To check what's installed: **Joutai → Plug-in**

### How it works

The shop is driven by tables that had to be located and decoded first:

| ROM offset | Contents |
|---|---|
| `0x3A7BFE` | Shop stock **pointer table** — 6 far pointers, one per story stage |
| *(pointed-to lists)* | 4-byte entries `{LE16 category, LE16 index}`, `FFFF`-terminated |
| `0x398720` | **Species master table**, 14 bytes × 310 — which card each species has, its price, rank, card-fusion results, and the minutes it buys at the final portal |
| `0x39829C` … `0x398514` | Card master tables ×4 (item / summon / P-factor / plug-in) |
| `0x390300` | Species battle data, 27 bytes each |
| `0x3C003F`, `0x3C018D` | Routines that map a card ID to its category and to its name |

The six stock lists sit back-to-back with no slack, so the patcher **relocates** each list into unused ROM space at `0x39994C`, appends the card, and rewrites the pointer table. That is why nothing has to be removed.

The price is *not* stored in the stock list — the shop looks it up from the species master table — so the card is automatically sold at its own designed price.

Full write-up: [`docs/BraveTamer_SaveFormat.md`](docs/BraveTamer_SaveFormat.md) (in Chinese) — save format, CRC-16 algorithm, Japanese text encoding, the card system, the fusion table, and complete ID tables.

### Repository contents

| Path | What |
|---|---|
| `BraveTamerShopPatcher.pyw` | The GUI patcher (Python + tkinter, single file, no dependencies) |
| `build_exe.bat` | Builds the standalone `.exe` with PyInstaller |
| `PATCHER_README.txt` | Bilingual end-user documentation shipped with releases |
| `docs/BraveTamer_SaveFormat.md` | Full reverse-engineering write-up of the save & ROM data |
| `tools/bt_save.py` | Save file (`.sav`, 2 KB) parser / CRC tool |
| `tools/bt_rompatch.py` | Command-line version of the ROM patcher |

### Running from source / building

```bat
:: run directly (needs Python 3 with tcl/tk)
BraveTamerShopPatcher.pyw

:: or build the standalone exe
build_exe.bat
```

### A note on ROMs

**No ROM is included, and none will be.** Every change is computed at run time from the ROM you supply. Please use your own legally obtained copy.

### Credits

Tool and reverse engineering by **William Lin (淋浴)** — [@Capta1nTaiwan](https://github.com/Capta1nTaiwan)

Licensed under the [MIT License](LICENSE).

*Digimon Tamers: Brave Tamer* © 2001 Bandai / Akiyoshi Hongo / Toei Animation. This project is unofficial and unaffiliated.

---

## 中文

### 這個專案發現了什麼

「カオスフレア」是 ベルゼブモン ブラストモード 的必殺技，以プラグインカード（技能卡）的形式存在。它在原版 ROM 中**資料完整** —— 卡名、說明文、售價 3200 BIT、Rank 6、病毒屬性、全體攻擊，連自己的卡片合成結果都寫好了。

但它**完全無法取得**。三條管道全部驗證過：

| 管道 | 結果 |
|---|---|
| **卡片店** | 六份商店庫存清單都沒有它 |
| **卡片合成**（Card Jogress） | 310 筆合成表中沒有任何組合能產生 |
| **掃描 → 轉換** | ブラストベルゼブモン 是全 310 個物種中**僅有的 2 個「戰鬥數值全為 0」的物種之一**，不會作為敵人登場，因此無法掃描 |

遊戲中所有真實敵人與 BOSS（包含 VR 系列、アーマゲモン、ディアボロモン、メフィスモン、ファラオモン）都有完整數值。這張卡是**沒有任何入手途徑的殘留內容**。

本工具為它開啟唯一的管道。

### 這個工具做什麼

把這張卡加進**全部六份**商店庫存清單（每個劇情階段各一份），**不移除任何原有商品**。售價 3200 BIT 是遊戲資料中原本就設定好的。

- 原始 ROM 不會被改動，會另外輸出一個新檔案。
- 會先驗證輸入檔（大小、檔頭、檢查碼、卡片資料、商店表結構），不是目標遊戲或已改過的檔案會直接拒絕。
- 自動重算 WonderSwan 檔頭檢查碼，ROM 依然有效。
- 實際改動約 **636 bytes**。
- 修改後的 ROM 與原版存檔相容。

### 使用方式

1. 到 [Releases](../../releases) 下載 `BraveTamer_ShopPatcher.exe`
2. 執行後選擇語言
3. **瀏覽…** → 選擇你自己的 ROM（`.wsc`，4 MB）
4. 確認檢查結果全部通過
5. **產生修改版 ROM…** → 選一個輸出檔名

> exe 未經數位簽章，Windows SmartScreen 可能會跳警告 ——「其他資訊 → 仍要執行」。部分防毒軟體也可能對 PyInstaller 打包的程式誤報。

### 買到之後怎麼用

カオスフレア 是**プラグインカード（技能卡）**，不是戰鬥中直接打出去的卡：

1. 在 Nanimon 卡片店買下（3200 BIT）
2. Nanomon 的 D-Ark 商店 → **カード組み込み → プラグイン** → 裝到數碼寶貝身上
   *（每隻最多 5 張，且不能處於「受傷」狀態）*
3. 戰鬥中：**Command → Waza → カオスフレア**

確認有沒有裝上：**Joutai → Plug-in**

### 運作原理

商店由幾張必須先解出來的資料表驅動：

| ROM 位移 | 內容 |
|---|---|
| `0x3A7BFE` | 商店庫存**指標表** —— 6 個 far pointer，每個劇情階段一份 |
| *(各清單本體)* | 4 bytes/筆的 `{LE16 類別, LE16 類別內索引}`，以 `FFFF` 結尾 |
| `0x398720` | **物種主表**，14 bytes × 310 —— 每個物種對應哪張卡、售價、Rank、卡片合成結果、最終關傳送門可換的分鐘數 |
| `0x39829C` … `0x398514` | 卡片主表 ×4（道具／召喚／P因子／外掛） |
| `0x390300` | 物種戰鬥資料，27 bytes/筆 |
| `0x3C003F`、`0x3C018D` | 卡片 ID ↔ 類別、卡片 ID → 卡名 的轉換函式 |

六份清單在 ROM 內緊鄰排列、沒有任何空隙，所以本工具把每份清單**搬移**到 `0x39994C` 起的空白區、在結尾加上這張卡，再改寫指標表 —— 這就是為什麼不需要移除任何東西。

售價**不在**庫存清單裡，商店會用卡片 ID 去查物種主表，所以這張卡會自動以它原本設計的價格販售。

完整技術文件：[`docs/BraveTamer_SaveFormat.md`](docs/BraveTamer_SaveFormat.md) —— 存檔格式、CRC-16 演算法、日文文字編碼、卡片系統、合成表與完整 ID 對照表。

### 專案內容

| 路徑 | 說明 |
|---|---|
| `BraveTamerShopPatcher.pyw` | GUI 修改工具（Python + tkinter，單一檔案、無外部相依） |
| `build_exe.bat` | 用 PyInstaller 打包成獨立 exe |
| `PATCHER_README.txt` | 隨 Release 附上的中英雙語使用說明 |
| `docs/BraveTamer_SaveFormat.md` | 存檔與 ROM 資料的完整逆向研究文件 |
| `tools/bt_save.py` | 存檔（`.sav`，2 KB）解析／CRC 工具 |
| `tools/bt_rompatch.py` | 命令列版的 ROM 修改工具 |

### 從原始碼執行／自行打包

```bat
:: 直接執行（需 Python 3，安裝時勾選 tcl/tk）
BraveTamerShopPatcher.pyw

:: 或打包成獨立 exe
build_exe.bat
```

### 關於 ROM

**本專案不含 ROM，也不會提供。** 所有修改都是在執行時，根據你提供的 ROM 即時計算出來的。請使用你自己合法取得的副本。

### 作者

工具與逆向研究：**淋浴（William Lin）** —— [@Capta1nTaiwan](https://github.com/Capta1nTaiwan)

採用 [MIT License](LICENSE)。

《デジモンテイマーズ ブレイブテイマー》© 2001 Bandai / 本鄉あきよし / 東映動畫。本專案為非官方作品，與其無任何關聯。
