#!/usr/bin/env python3
"""
Digimon Tamers: Brave Tamer (WonderSwan Color, JP) — save file (.sav, 2048 bytes) parser / CRC tool.

Author: William Lin (淋浴).  Unofficial and unaffiliated; contains no ROM data.

Usage:
    python bt_save.py dump   "Brave Tamer.sav" [--rom "Brave Tamer.wsc"]
    python bt_save.py verify "Brave Tamer.sav"
    python bt_save.py fixcrc "Brave Tamer.sav" [-o out.sav]

`dump` prints everything the save contains.  Pass --rom to resolve species / card IDs to
Japanese names (the ROM is only used to read its name tables).  Without --rom, IDs are printed raw.

`fixcrc` recomputes the CRC-16 after you have edited bytes in the payload (0x003..0x6AE).
The CRC table is reconstructed from 8 embedded basis values (the ROM table is XOR-linear), so no
ROM is required.

Layout summary (see BraveTamer_SaveFormat.md for the full write-up):
    0x000  02                    magic
    0x001  LE16 0x06AC           payload length
    0x003  "BRAVETAMER_V001\\0"   signature (16 bytes)
    0x013  LE32                  BIT (money)
    0x017  50 x LE16             card holder (sorted, 0x120 = empty)
    0x07B  FF FF                 ?
    0x07D  LE32                  ? (play-time counter?)
    0x081  00                    ?
    0x082  22 x LE16             scan data (species IDs, 0 = empty)
    0x0AE  6 bytes               tamer name (FF-terminated)
    0x0B4  00 00                 ?
    0x0B6  35 bytes              flags (mostly FF)
    0x0D9  1 byte                ?
    0x0DA  4 x 0x6D              party records (slot 0 unused in the reference save)
    0x28E  1 byte                party member count
    0x28F  15 x 0x41             cloak (storage) records
    0x65E  81 bytes              ? (misc)
    0x6AF  03                    magic 2
    0x6B0  BE16                  CRC-16 over 0x001..0x6AF
    0x6B2  zeros                 padding to 2048
"""
import argparse
import struct
import sys

# --------------------------------------------------------------------------- CRC
# The ROM's CRC lookup table (hi bytes @ROM 0x3B1F68, lo bytes @ROM 0x3B2068) is XOR-linear,
# so the whole 256-entry table follows from the entries at the 8 powers of two.
_CRC_BASIS = {1: 0x8911, 2: 0x1223, 4: 0x2446, 8: 0x488C,
              16: 0x8110, 32: 0x0221, 64: 0x0442, 128: 0x0884}


def build_crc_table():
    tbl = []
    for i in range(256):
        v = 0
        for bit, val in _CRC_BASIS.items():
            if i & bit:
                v ^= val
        tbl.append(v)
    return tbl


CRC_TABLE = build_crc_table()


def crc16(data, init=0):
    c = init
    for b in data:
        c = ((c << 8) ^ CRC_TABLE[((c >> 8) ^ b) & 0xFF]) & 0xFFFF
    return c


def crc_span(sav):
    """Return (body_bytes, crc_offset) for the single save block at offset 0."""
    length = sav[1] | (sav[2] << 8)
    body = bytes(sav[1:1 + length + 3])          # length(2) + payload + magic2, CRC excluded
    return body, 4 + length


def verify_crc(sav):
    body, off = crc_span(sav)
    stored = (sav[off] << 8) | sav[off + 1]
    return stored, crc16(body)


def fix_crc(sav):
    sav = bytearray(sav)
    body, off = crc_span(sav)
    c = crc16(body)
    sav[off] = (c >> 8) & 0xFF
    sav[off + 1] = c & 0xFF
    return bytes(sav)


# --------------------------------------------------------------------------- text encoding
_HIRA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
_HDAK = "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ"
_HSML = "ぁぃぅぇぉゃゅょっ"
_KATA = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
_KDAK = "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ"
_KSML = "ァィゥェォャュョッ"

CHARSET = {}
for _i, _c in enumerate("0123456789"):
    CHARSET[_i] = _c
for _base, _s in ((0x0A, _HIRA), (0x38, _HDAK), (0x51, _HSML),
                  (0x5A, _KATA), (0x88, _KDAK), (0xA1, _KSML)):
    for _i, _c in enumerate(_s):
        CHARSET[_base + _i] = _c
CHARSET[0xAA] = 'ヴ'
CHARSET[0xAB] = 'ー'
CHARSET[0xED] = '='                      # e.g. ムーン=ミレニアモン
for _i, _c in enumerate('①②③④'):        # tier glyphs used in card names (PFーHPプラス①..④); exact tile unknown
    CHARSET[0xF0 + _i] = _c
for _i in range(26):
    CHARSET[0xB4 + _i] = chr(ord('A') + _i)
    CHARSET[0xCE + _i] = chr(ord('a') + _i)
CHARSET_REV = {v: k for k, v in CHARSET.items()}


def decode_text(raw):
    out = []
    for c in raw:
        if c == 0xFF:
            break
        out.append(CHARSET.get(c, f'[{c:02X}]'))
    return ''.join(out)


def encode_name(text, length=6):
    """Encode a nickname into the 6-byte field (max 5 chars + 0xFF terminator)."""
    if len(text) > length - 1:
        raise ValueError(f'name too long (max {length - 1} chars): {text!r}')
    out = bytearray()
    for ch in text:
        if ch not in CHARSET_REV:
            raise ValueError(f'unsupported character: {ch!r}')
        out.append(CHARSET_REV[ch])
    out.append(0xFF)
    while len(out) < length:
        out.append(0xFF)
    return bytes(out)


# --------------------------------------------------------------------------- ROM name tables
ROM_SPECIES_PTR_TABLES = (0x370974, 0x370F6C)   # far-pointer tables -> 238 + 72 = 310 names
ROM_ITEM_PTR_TABLE = 0x373ACA                    # 33  アイテムカード descriptions
ROM_PF_PTR_TABLE = 0x375AEE                      # 101 Pいんしカード (PF) descriptions
ROM_PLUGIN_PTR_TABLE = 0x3780AA                  # 131 プラグインカード descriptions (album order, NOT card-ID order)
ROM_TECH_PTR_TABLE = 0x3718D6                    # 238 technique names (tech IDs 0..237)
ROM_TECH_EXT_PTR_TABLE = 0x371EFA                # 72 extra technique names (tech IDs 238..309, boss moves)
ROM_CRC_HI, ROM_CRC_LO = 0x3B1F68, 0x3B2068
# Card master data: four contiguous tables of 4-byte entries (LE16 price, LE16 X).  X is 1-based
# (ROM 0x3C00E8 returns X-1); its meaning depends on the category (ROM 0x3C018D):
#   item / PF  : X-1 = species drawn on the card (illustration)
#   summon     : X-1 = species that gets summoned (name = species name)
#   plug-in    : X-1 = technique ID (<238 -> ROM_TECH_PTR_TABLE, else ROM_TECH_EXT_PTR_TABLE[id-238])
# Card ID -> (category, index) is decided by the ROM routine at 0x3C003F: <33 / <57 / <158 / <289.
ROM_CARD_TABLES = (  # (category name, file offset, count, first holder ID)
    ("アイテム", 0x39829C, 33, 0),
    ("しょうかん", 0x398320, 24, 33),
    ("Pいんし", 0x398380, 101, 57),
    ("プラグイン", 0x398514, 131, 158),
)
CARD_COUNT = 289            # valid holder IDs 0..288 (288 also doubles as the "empty slot" value)
HOLDER_EMPTY = 0x120


def _far2file(off, seg):
    # ROM bank window: linear 0x40000..0xFFFFF <-> file 0x340000..0x3FFFFF
    return (seg << 4) + off - 0x70000 + 0x370000


def _read_ptr_table(rom, table):
    out = []
    p = table
    while True:
        off, seg = struct.unpack_from('<HH', rom, p)
        if off == 0 and seg == 0:
            break
        a = _far2file(off, seg)
        if not (0x370000 <= a < 0x380000):
            break
        e = rom.find(b'\xff', a)
        out.append(decode_text(rom[a:e]))
        p += 4
    return out


def _card_name(desc):
    # description strings look like "<type>[EE][FE][FC]1<name>[FC]0<text>..."
    i = desc.find('[FC]1')
    j = desc.find('[FC]0', i + 5)
    if i != -1 and j != -1:
        return desc[i + 5:j]
    return desc[:24]


def card_category(cid):
    """Holder card ID -> (category index 0..3, index within category), mirroring ROM 0x3C003F."""
    for ci, (_, _, cnt, base) in enumerate(ROM_CARD_TABLES):
        if cid < base + cnt:
            return ci, cid - base
    return None, None


class Names:
    def __init__(self, rom_path=None):
        self.species, self.items, self.pf, self.tech_names, self.tech_ext_names = [], [], [], [], []
        self.cards = []          # index = holder card ID -> (category, idx, price, X)
        self.rom_ok = False
        if not rom_path:
            return
        rom = open(rom_path, 'rb').read()
        if len(rom) != 4 * 1024 * 1024 or rom[0x370974:0x370978] != b'\x06\x00\x2b\x70':
            print('WARNING: --rom does not look like the Brave Tamer ROM; names disabled', file=sys.stderr)
            return
        for t in ROM_SPECIES_PTR_TABLES:
            self.species += _read_ptr_table(rom, t)
        self.items = [_card_name(x) for x in _read_ptr_table(rom, ROM_ITEM_PTR_TABLE)]
        self.pf = [_card_name(x) for x in _read_ptr_table(rom, ROM_PF_PTR_TABLE)]
        self.tech_names = _read_ptr_table(rom, ROM_TECH_PTR_TABLE)          # tech IDs 0..237
        self.tech_ext_names = _read_ptr_table(rom, ROM_TECH_EXT_PTR_TABLE)  # tech IDs 238..309
        for cat, (cname, addr, cnt, base) in enumerate(ROM_CARD_TABLES):
            for k in range(cnt):
                price, x = struct.unpack_from('<HH', rom, addr + 4 * k)
                self.cards.append((cat, k, price, x))
        rom_tbl = [(rom[ROM_CRC_HI + i] << 8) | rom[ROM_CRC_LO + i] for i in range(256)]
        if rom_tbl != CRC_TABLE:
            print('WARNING: embedded CRC table differs from ROM table!', file=sys.stderr)
        self.rom_ok = True

    def tech_name(self, t):
        if t < len(self.tech_names):
            return self.tech_names[t]
        if t - len(self.tech_names) < len(self.tech_ext_names):
            return self.tech_ext_names[t - len(self.tech_names)]
        return f'?{t}'

    def tech(self, t):
        """'id:name (owner species)' for a technique ID (0xFFFF = empty)."""
        if t == 0xFFFF:
            return '(empty)'
        if not self.tech_names:
            return str(t)
        owner = self.species[t] if t < len(self.species) else '?'
        return f'{t}:{self.tech_name(t)}({owner})'

    def plugin_card_for_tech(self, t):
        """Holder card ID of the plug-in card that installs technique `t` (None if no such card)."""
        for cid, (cat, k, price, x) in enumerate(self.cards):
            if cat == 3 and x - 1 == t:
                return cid
        return None

    def sp(self, i):
        if i is None:
            return '-'
        if i == 0xFFFF:
            return '(empty)'
        return f'{i}:{self.species[i]}' if i < len(self.species) else f'{i}:?'

    def pfname(self, i):
        if i == 0xFF:
            return '--'
        return f'{i}:{self.pf[i]}' if i < len(self.pf) else f'{i}:?'

    def card_name(self, cid):
        """Name of holder card `cid`, following ROM 0x3C018D (item/PF: description tables in
        index order; summon: species name of X-1; plug-in: technique name of X-1)."""
        cat, k = card_category(cid)
        if cat is None:
            return '??'
        x = self.cards[cid][3] if self.cards else None
        if cat == 0:
            return self.items[k] if k < len(self.items) else f'#{k}'
        if cat == 1:
            return self.sp(x - 1).split(':', 1)[1] if x else f'#{k}'
        if cat == 2:
            return self.pf[k] if k < len(self.pf) else f'#{k}'
        return self.tech_name(x - 1) if x else f'#{k}'

    def card(self, cid):
        """Decode a card-holder ID (0..288; 0x120 = empty slot)."""
        if cid == HOLDER_EMPTY:
            return '(empty)'
        cat, k = card_category(cid)
        if cat is None:
            return f'{cid}:?? (out of range)'
        cname = ROM_CARD_TABLES[cat][0]
        if not self.cards:
            return f'{cid}:{cname}#{k}'
        _, _, price, x = self.cards[cid]
        extra = ''
        if cat in (0, 2):
            extra = f', 絵柄 {self.sp(x - 1)}'
        elif cat == 3:
            extra = f', 技ID {x - 1}'
        return f'{cid}:{cname}カード「{self.card_name(cid)}」[{price}BIT{extra}]'

    def find_cards(self, text):
        """Holder card IDs whose name contains `text`."""
        return [cid for cid in range(len(self.cards)) if text in self.card_name(cid)]


# --------------------------------------------------------------------------- record parsing
STAT_NAMES = ["HP", "DP(技力)", "AP(攻撃)", "PP(防御)", "SP(速さ)", "LP(注意深さ)",
              "PA(単体技回避)", "TA(全体技回避)", "SC(状態変化耐性)", "PC(パラ変化耐性)",
              "EX(賢さ)", "YP(YP抑制)"]

PARTY_REC = 0x6D
BOX_REC = 0x41
PARTY_BASE, PARTY_SLOTS = 0x0DA, 4
PARTY_COUNT_OFF = 0x28E
BOX_BASE, BOX_SLOTS = 0x28F, 15


def _u16(s, o):
    return s[o] | (s[o + 1] << 8)


def parse_record(s, o, party):
    """Parse one Digimon record starting at offset o.  Returns dict."""
    r = {'offset': o, 'party': party}
    r['flag'] = s[o]
    r['tech0'] = _u16(s, o + 1)
    if party:
        r['species'] = _u16(s, o + 3)
        r['partner'] = s[o + 5]
        r['name_raw'] = bytes(s[o + 6:o + 12])
        p = o + 12
        bb = s[p:p + 30]
        r['battle'] = {
            'HP': (_u16(bb, 0), _u16(bb, 2)), 'DP': (_u16(bb, 4), _u16(bb, 6)),
            'AP': (_u16(bb, 8), _u16(bb, 10)), 'PP': (_u16(bb, 12), _u16(bb, 14)),
            'SP': (bb[16], bb[17]), 'LP': bb[18], 'PA': (bb[19], bb[20]), 'TA': (bb[21], bb[22]),
            'SC': (bb[23], bb[24]), 'PC': (bb[25], bb[26]), 'EX': (bb[27], bb[28]), 'byte29': bb[29]}
        p += 30
    else:
        r['species'] = None
        r['partner'] = s[o + 3]
        r['name_raw'] = bytes(s[o + 4:o + 10])
        p = o + 10
    r['name'] = decode_text(r['name_raw'])
    # installed plug-in (technique) cards: up to 5 technique IDs, used in battle via "Waza".
    # Technique-table index == species ID of the technique's owner, so the values look like
    # species IDs (e.g. 146 = ガイアフォース, WarGreymon's move).  The first entry is duplicated
    # at +0x01 ('tech0'; probably the default / last used Waza).
    r['plugin_count'] = s[p]
    r['plugins'] = [_u16(s, p + 1 + 2 * i) for i in range(5)]
    p += 11
    r['pf'] = list(s[p:p + 4])
    r['pf_count'] = s[p + 4]
    p += 5
    r['stats'] = [_u16(s, p + 2 * i) for i in range(12)]
    p += 24
    if party:
        r['extra12'] = list(s[p:p + 12])
        r['byte5E'] = s[p + 12]
        p += 13
    tr = bytes(s[p:p + 14])
    r['trailer_raw'] = tr
    r['level'] = tr[3]
    r['yp'] = struct.unpack_from('<I', tr, 5)[0]
    r['tr_u16'] = tr[10] | (tr[11] << 8)
    p += 14
    if not party:
        r['pad'] = s[p]
        p += 1
    r['end'] = p
    return r


def parse_save(s):
    if len(s) != 2048:
        raise ValueError(f'expected 2048-byte save, got {len(s)}')
    if s[0] != 0x02:
        raise ValueError('bad magic byte at 0x000')
    d = {}
    d['length'] = _u16(s, 1)
    d['signature'] = bytes(s[3:0x13])
    d['bit'] = struct.unpack_from('<I', s, 0x13)[0]
    d['holder'] = [_u16(s, 0x17 + 2 * i) for i in range(50)]
    d['u7B'] = bytes(s[0x7B:0x7D])
    d['u7D'] = struct.unpack_from('<I', s, 0x7D)[0]
    d['u81'] = s[0x81]
    d['scan'] = [_u16(s, 0x82 + 2 * i) for i in range(22)]
    d['tamer_raw'] = bytes(s[0xAE:0xB4])
    d['tamer'] = decode_text(d['tamer_raw'])
    d['uB4'] = bytes(s[0xB4:0xB6])
    # card album: 288 bits (LSB-first), one per holder card ID 0..287 -> collected flag
    d['album_raw'] = bytes(s[0xB6:0xDA])
    d['album'] = [(s[0xB6 + i // 8] >> (i % 8)) & 1 for i in range(288)]
    d['party'] = []
    for k in range(PARTY_SLOTS):
        o = PARTY_BASE + k * PARTY_REC
        if all(b == 0 for b in s[o:o + PARTY_REC]):
            d['party'].append(None)
        else:
            d['party'].append(parse_record(s, o, True))
    d['party_count'] = s[PARTY_COUNT_OFF]
    d['box'] = [parse_record(s, BOX_BASE + k * BOX_REC, False) for k in range(BOX_SLOTS)]
    d['tail'] = bytes(s[BOX_BASE + BOX_SLOTS * BOX_REC:3 + d['length']])
    d['magic2'] = s[3 + d['length']]
    d['crc_stored'], d['crc_calc'] = verify_crc(s)
    return d


# --------------------------------------------------------------------------- dump
def dump(s, names):
    d = parse_save(s)
    N = names
    print(f"signature      : {d['signature']!r}")
    print(f"payload length : 0x{d['length']:X}   magic2=0x{d['magic2']:02X}   "
          f"CRC stored={d['crc_stored']:04X} calc={d['crc_calc']:04X} "
          f"{'OK' if d['crc_stored'] == d['crc_calc'] else 'MISMATCH'}")
    print(f"tamer name     : {d['tamer']!r}  [{d['tamer_raw'].hex(' ')}]")
    print(f"BIT (money)    : {d['bit']}")
    print(f"0x7B/0x7D/0x81 : {d['u7B'].hex(' ')} / {d['u7D']} / {d['u81']:02X}   (unknown)")
    print(f"0xB4           : {d['uB4'].hex(' ')}   (unknown)")
    missing = [i for i, b in enumerate(d['album']) if not b]
    print(f"card album     : {sum(d['album'])}/288 collected; missing: " +
          (', '.join(N.card(m) for m in missing) if missing else '(none)'))
    used = [c for c in d['holder'] if c != HOLDER_EMPTY]
    print(f"card holder    : {len(used)}/50 used")
    for c in used:
        print(f"    {N.card(c)}")
    scan = [x for x in d['scan'] if x]
    print(f"scan data      : {len(scan)}/22 used: " + ', '.join(N.sp(x) for x in scan))
    print(f"party count    : {d['party_count']}")
    for k, r in enumerate(d['party']):
        print(f"\n[party slot {k}] @0x{PARTY_BASE + k * PARTY_REC:03X}")
        if r is None:
            print("    (empty)")
        else:
            dump_record(r, N)
    for k, r in enumerate(d['box']):
        print(f"\n[cloak slot {k}] @0x{r['offset']:03X}" + ("" if r['flag'] else "   (flag=00: inactive / stale copy)"))
        dump_record(r, N)
    print(f"\ntail @0x{BOX_BASE + BOX_SLOTS * BOX_REC:03X} ({len(d['tail'])} bytes, unknown): {d['tail'].hex(' ')}")


def dump_record(r, N):
    print(f"    name={r['name']!r}  partner#{r['partner']}  flag={r['flag']:02X}  "
          f"level={r['level']}  YP={r['yp']}  u16@trailer={r['tr_u16']}")
    if r['party']:
        print(f"    current form : {N.sp(r['species'])}")
    print(f"    tech @+0x01  : {N.tech(r['tech0'])}")
    techs = [N.tech(t) for t in r['plugins'][:r['plugin_count']]]
    print(f"    plug-in techs: {r['plugin_count']}/5  {', '.join(techs) if techs else '(none)'}")
    pfs = [N.pfname(x) for x in r['pf'] if x != 0xFF]
    print(f"    PF cards     : {r['pf_count']}/4  {', '.join(pfs) if pfs else '(none)'}")
    print("    stats        : " + ', '.join(f"{n}={v}" for n, v in zip(STAT_NAMES, r['stats'])))
    if r['party']:
        b = r['battle']
        print(f"    battle cur/max: HP {b['HP']} DP {b['DP']} AP {b['AP']} PP {b['PP']} SP {b['SP']} "
              f"LP {b['LP']} PA {b['PA']} TA {b['TA']} SC {b['SC']} PC {b['PC']} EX {b['EX']} b29={b['byte29']}")
        print(f"    extra12={r['extra12']}  byte5E={r['byte5E']:02X}")
    print(f"    trailer raw  : {r['trailer_raw'].hex(' ')}")


# --------------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('dump');   p.add_argument('save'); p.add_argument('--rom')
    p = sub.add_parser('verify'); p.add_argument('save')
    p = sub.add_parser('fixcrc'); p.add_argument('save'); p.add_argument('-o', '--out')
    a = ap.parse_args()

    s = open(a.save, 'rb').read()
    if a.cmd == 'dump':
        dump(s, Names(a.rom))
    elif a.cmd == 'verify':
        st, ca = verify_crc(s)
        print(f"CRC stored={st:04X} calc={ca:04X} {'OK' if st == ca else 'MISMATCH'}")
        sys.exit(0 if st == ca else 1)
    elif a.cmd == 'fixcrc':
        fixed = fix_crc(s)
        out = a.out or a.save
        open(out, 'wb').write(fixed)
        st, ca = verify_crc(fixed)
        print(f"wrote {out}: CRC {st:04X} ({'OK' if st == ca else 'BAD'})")


if __name__ == '__main__':
    main()
