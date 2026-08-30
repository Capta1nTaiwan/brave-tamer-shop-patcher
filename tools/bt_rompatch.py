#!/usr/bin/env python3
"""
Digimon Tamers: Brave Tamer (WSC, JP) — ROM patcher: add cards to the card shop.

Author: William Lin (淋浴).  Unofficial and unaffiliated; contains no ROM data.

    python bt_rompatch.py add-to-shop "Brave Tamer.wsc" -o out.wsc --card 263
    python bt_rompatch.py show-shop   "Brave Tamer.wsc"
    python bt_rompatch.py checksum    "Brave Tamer.wsc"

How the shop works (reverse engineered from the ROM):

  RAM 0x3720   50-slot array of card IDs = the shop's current stock (0xFFFF = empty)
  RAM 0x3108   story-progress index; the shop stock list is chosen by it
  RAM 0x371C   0 = buy menu, 1 = sell menu      RAM 0x371E = cursor

  ROM 0x3A7BFE   pointer table, 6 far pointers {LE16 offset, LE16 segment}
                 (code at 0x3F43C6 does: les bx, es:[bx+0x0E] with es=0xA7BF,
                  bx = progress*4 - 0x118, so entry n is at 0x3A7BFE + 4*n)
  each list      array of 4-byte entries {LE16 category, LE16 index-in-category},
                 terminated by category == 0xFFFF.  Category/base:
                 0 アイテム(+0)  1 しょうかん(+33)  2 Pいんし(+57)  3 プラグイン(+158)
                 The loop at 0x3F43C6 converts each (category,index) to a card ID
                 via the routine at 0x3C0000 and stores it into RAM 0x3720.

  Prices are NOT in the shop list.  They come from the species-indexed master
  table at ROM 0x398720 (14 bytes/species); the shop calls 0x3C0170 which maps
  card ID -> species -> price.  So a card added to a shop list is automatically
  sold at its real price (カオスフレア = 3200 BIT).

Because the six lists sit back-to-back with no slack, adding an entry means
relocating the list.  This tool copies every list into free ROM space, appends
the new card, and rewrites the pointer table — no existing item is removed.

The WonderSwan header checksum (last 2 bytes of the ROM, little-endian) is the
sum of every other byte mod 0x10000; it is recomputed automatically.
"""
import argparse
import struct
import sys

SHOP_PTR_TABLE = 0x3A7BFE
SHOP_LIST_COUNT = 6
LIST_TERMINATOR = 0xFFFF
CARD_CATEGORIES = (  # (name, first card ID, count)
    ("アイテム", 0, 33),
    ("しょうかん", 33, 24),
    ("Pいんし", 57, 101),
    ("プラグイン", 158, 131),
)
FREE_SPACE = 0x39994C          # 26 KB of 0xFF following the species master table
ROM_LINEAR_BIAS = 0x300000     # file offset = CPU linear address + this


def card_to_cat_idx(card_id):
    for cat, (_, base, count) in enumerate(CARD_CATEGORIES):
        if base <= card_id < base + count:
            return cat, card_id - base
    raise ValueError(f'card ID {card_id} out of range (0..288)')


def cat_idx_to_card(cat, idx):
    return CARD_CATEGORIES[cat][1] + idx


def far_ptr_to_file(off, seg):
    return ((seg << 4) + off) + ROM_LINEAR_BIAS


def file_to_far_ptr(file_off):
    linear = file_off - ROM_LINEAR_BIAS
    if not (0x40000 <= linear < 0x100000):
        raise ValueError(f'0x{file_off:06X} is not reachable by a plain far pointer')
    return linear & 0xF, linear >> 4


def read_shop_lists(rom):
    """Return [(file_offset, [card_id, ...]), ...] for the six shop stock lists."""
    out = []
    for n in range(SHOP_LIST_COUNT):
        off, seg = struct.unpack_from('<HH', rom, SHOP_PTR_TABLE + 4 * n)
        base = far_ptr_to_file(off, seg)
        cards = []
        k = 0
        while True:
            cat, idx = struct.unpack_from('<HH', rom, base + 4 * k)
            if cat == LIST_TERMINATOR:
                break
            if cat > 3 or k > 60:
                raise ValueError(f'list {n} at 0x{base:06X} is malformed')
            cards.append(cat_idx_to_card(cat, idx))
            k += 1
        out.append((base, cards))
    return out


def add_card_to_shop(rom, card_id, lists_to_patch=None, free_space=FREE_SPACE):
    """Append `card_id` to the chosen shop lists, relocating them into free space."""
    rom = bytearray(rom)
    lists = read_shop_lists(rom)
    targets = range(SHOP_LIST_COUNT) if lists_to_patch is None else lists_to_patch

    cursor = free_space
    for n, (_, cards) in enumerate(lists):
        if n not in targets:
            continue
        if card_id in cards:
            print(f'  list {n}: already sells card {card_id}, skipped')
            continue
        new_cards = cards + [card_id]
        need = len(new_cards) * 4 + 4
        if any(b != 0xFF for b in rom[cursor:cursor + need]):
            raise ValueError(f'free space at 0x{cursor:06X} is not blank')
        for i, c in enumerate(new_cards):
            struct.pack_into('<HH', rom, cursor + 4 * i, *card_to_cat_idx(c))
        struct.pack_into('<HH', rom, cursor + 4 * len(new_cards), LIST_TERMINATOR, LIST_TERMINATOR)
        off, seg = file_to_far_ptr(cursor)
        struct.pack_into('<HH', rom, SHOP_PTR_TABLE + 4 * n, off, seg)
        print(f'  list {n}: {len(cards)} -> {len(new_cards)} cards, relocated to 0x{cursor:06X} '
              f'(ptr {seg:04X}:{off:04X})')
        cursor += need
    return bytes(rom)


def fix_checksum(rom):
    rom = bytearray(rom)
    s = sum(rom[:-2]) & 0xFFFF
    struct.pack_into('<H', rom, len(rom) - 2, s)
    return bytes(rom)


def verify_checksum(rom):
    return sum(rom[:-2]) & 0xFFFF, struct.unpack_from('<H', rom, len(rom) - 2)[0]


def _names(rom_path):
    """Optional pretty names, via bt_save.py if it is next to this script."""
    try:
        import bt_save
        n = bt_save.Names(rom_path)
        return n if n.rom_ok else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('show-shop'); p.add_argument('rom')
    p = sub.add_parser('checksum');  p.add_argument('rom')
    p = sub.add_parser('add-to-shop')
    p.add_argument('rom'); p.add_argument('-o', '--out', required=True)
    p.add_argument('--card', type=int, default=263, help='card ID to add (default 263 = カオスフレア)')
    p.add_argument('--lists', help='comma-separated list indices 0-5 (default: all six)')
    a = ap.parse_args()

    rom = open(a.rom, 'rb').read()
    if len(rom) != 4 * 1024 * 1024:
        sys.exit(f'expected a 4 MB ROM, got {len(rom)} bytes')
    N = _names(a.rom)
    name = (lambda c: N.card_name(c)) if N else (lambda c: f'#{c}')

    if a.cmd == 'checksum':
        calc, stored = verify_checksum(rom)
        print(f'calculated {calc:04X}  stored {stored:04X}  {"OK" if calc == stored else "MISMATCH"}')
    elif a.cmd == 'show-shop':
        for n, (base, cards) in enumerate(read_shop_lists(rom)):
            print(f'list {n} @0x{base:06X}  {len(cards)} cards')
            print('   ' + '、'.join(name(c) for c in cards))
    else:
        targets = None
        if a.lists:
            targets = [int(x) for x in a.lists.split(',')]
        print(f'adding card {a.card} ({name(a.card)}) to the shop:')
        patched = fix_checksum(add_card_to_shop(rom, a.card, targets))
        open(a.out, 'wb').write(patched)
        calc, stored = verify_checksum(patched)
        print(f'wrote {a.out}: checksum {stored:04X} ({"OK" if calc == stored else "BAD"})')


if __name__ == '__main__':
    main()
