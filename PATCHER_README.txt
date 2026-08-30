========================================================================
 Brave Tamer Shop Patcher
 Brave Tamer 商店修改工具
 -- adds "Chaos Flare" to the in-game card shop
 -- 讓卡片店販售「カオスフレア」
 (Digimon Tamers: Brave Tamer / WonderSwan Color, Japanese)
========================================================================

  Author : William Lin      作者：淋浴
  Version 版本 : 1.1  (2026-08-30)

  The program asks for a language (繁體中文 / English) when it starts.
  程式啟動時會先讓你選擇語言（繁體中文 / English）。

========================================================================
 中文
========================================================================

■ 這是什麼

  這個工具會修改你自己的 Brave Tamer ROM，讓遊戲中 Nanimon 的卡片店
  開始販售「カオスフレア」這張卡。

  カオスフレア 是 ベルゼブモン ブラストモード（Beelzebumon Blast Mode）
  的必殺技卡，屬性：病毒、Rank 6、效果：攻擊敵方全體造成傷害。

  這張卡在原版遊戲裡資料完整（有卡名、說明、售價、效果），但沒有任何
  取得途徑 —— 不會出現在商店，沒有合成組合能做出來，而且
  ブラストベルゼブモン 在遊戲資料中沒有戰鬥數值、不會作為敵人登場，
  所以也無法用 D-Ark 掃描後轉換成卡。本工具為它開啟唯一的入手管道。

■ 怎麼用

  1. 執行 BraveTamer_ShopPatcher.exe
  2. 選擇顯示語言（之後也可以在主視窗右上角隨時切換）
  3. 按「瀏覽…」選擇你自己的 Brave Tamer ROM（.wsc，4 MB）
  4. 確認檢查結果全部通過
  5. 按「產生修改版 ROM…」，選一個輸出檔名

  原始 ROM 不會被改動，工具會另外輸出一個新檔案。

■ 買到之後怎麼用這張卡

  カオスフレア 是「プラグインカード」（技能卡），不是戰鬥中直接打出去的卡：

  1. 在 Nanimon 卡片店買下這張卡（3200 BIT）
  2. 到 Nanomon 的 D-Ark 商店 → カード組み込み → プラグイン
     → 選一隻數碼寶貝裝上（每隻最多 5 張，且不能處於「受傷」狀態）
  3. 戰鬥中：Command → Waza（技）→ カオスフレア

  想確認有沒有裝上：Joutai（狀態）→ Plug-in

■ 這個工具會改什麼

  * 卡片店有 6 份庫存清單（隨劇情進度切換），六份都會加入這張卡。
  * 只新增，不移除任何原有商品。
  * 售價 3200 BIT 是遊戲資料中原本就設定好的，工具沒有自己指定價格。
  * 修改後會自動重算 WonderSwan 檔頭檢查碼，ROM 依然有效。
  * 實際改動約 636 bytes。

■ 重要說明

  * 本程式「不含任何 ROM 資料」，所有修改都是即時計算出來的。
    請使用你自己合法取得的 ROM。
  * 工具會先驗證檔案（大小、檔頭、檢查碼、卡片資料、商店表結構），
    不是目標遊戲或已經改過的檔案會直接拒絕，不會破壞你的檔案。
  * 建議先備份原始 ROM 和存檔。
  * 修改後的 ROM 與原版存檔相容。
  * 這個 exe 沒有數位簽章，Windows SmartScreen 可能會跳出藍色警告，
    需要點「其他資訊」→「仍要執行」；部分防毒軟體也可能對
    PyInstaller 打包的程式誤報。這在自製小工具很常見。

■ 沒有 exe、只有 .pyw 的話

  需要安裝 Python 3（python.org，安裝時勾選 tcl/tk），
  然後雙擊 BraveTamerShopPatcher.pyw 即可。
  想自己打包成 exe：執行 build_exe.bat（需要網路）。

■ 作者

  淋浴（William Lin）

  本工具與其依據的逆向研究（商店庫存表、卡片主表、卡片合成表、
  存檔格式與檢查碼演算法）皆由本人整理製作。
  遊戲本體《デジモンテイマーズ ブレイブテイマー》著作權屬於
  Bandai / 本鄉あきよし / 東映動畫，本工具與之無關聯。


========================================================================
 English
========================================================================

■ What this is

  This tool patches your own copy of the Brave Tamer ROM so that Nanimon's
  card shop sells the "Chaos Flare" (カオスフレア) card.

  Chaos Flare is BlastBeelzebumon's signature attack, available as a plug-in
  card: Virus attribute, Rank 6, damages all enemies.

  The card is fully defined in the original game (name, description, price,
  effect) but has no way of being obtained: it is not sold anywhere, no card
  jogress combination produces it, and BlastBeelzebumon has no battle stats
  at all, so it never appears as an enemy and cannot be scanned and converted
  into a card. This tool creates the only way to get it.

■ How to use

  1. Run BraveTamer_ShopPatcher.exe
  2. Pick a language (you can also switch it any time from the top right)
  3. Click "Browse..." and select your own Brave Tamer ROM (.wsc, 4 MB)
  4. Check that every verification row passes
  5. Click "Create patched ROM..." and choose an output filename

  Your original ROM is never modified - a new file is written instead.

■ Using the card once you have bought it

  Chaos Flare is a plug-in card (a technique), not something you play directly
  in battle:

  1. Buy it at Nanimon's card shop (3200 BIT)
  2. Go to Nanomon's D-Ark shop -> Card Insert -> Plug-in
     -> install it on a Digimon (max 5 per Digimon; it cannot be injured)
  3. In battle: Command -> Waza -> Chaos Flare

  To check what is installed: Joutai (status) -> Plug-in

■ What the tool changes

  * The shop has 6 stock lists (one per story stage); the card is added to all six.
  * It only adds - no existing item is ever removed.
  * The 3200 BIT price already exists in the game data; the tool does not set it.
  * The WonderSwan header checksum is recomputed, so the ROM stays valid.
  * About 636 bytes are changed in total.

■ Important

  * This program contains NO ROM data - everything is computed at run time.
    Please use your own legally obtained ROM.
  * The file is verified first (size, header, checksum, card data, shop table
    structure). A wrong game or an already-patched file is refused, so your
    files cannot be damaged.
  * Back up your ROM and save file first.
  * The patched ROM stays compatible with existing save files.
  * The exe is unsigned, so Windows SmartScreen may show a blue warning -
    click "More info" -> "Run anyway". Some antivirus products also give
    false positives on PyInstaller executables. This is common for small
    homemade tools.

■ If you only have the .pyw file

  Install Python 3 (python.org, with the tcl/tk option enabled) and
  double-click BraveTamerShopPatcher.pyw.
  To build the exe yourself: run build_exe.bat (needs an internet connection).

■ Author

  William Lin (淋浴)

  This tool, and the reverse engineering it is based on (the shop stock tables,
  the card master table, the card-jogress table, the save format and its
  checksum algorithm), were researched and written by me.
  Digimon Tamers: Brave Tamer is copyright Bandai / Akiyoshi Hongo /
  Toei Animation. This tool is unofficial and unaffiliated.

========================================================================
