#!/usr/bin/env python3
"""
HisiNve CLI - Command Line Tool for Huawei Kirin NVME Partition Images.
"""
import sys
import os
import argparse
import json
import csv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hisi_nve import HisiNveImage, SocProfile, SOC_PROFILES

def print_banner():
    print("=" * 65)
    print("  HisiNve-Py v3.0 - Huawei Kirin NVME Partition Manager")
    print("  100% Pure Python | Offline Safe | Hardware-Accurate CRC32C")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(
        description="HisiNve-Py: Read, modify, and repair Huawei Kirin NVME partition images offline."
    )
    parser.add_argument(
        "image",
        help="Path to the nvme.img partition image file"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Command: info
    p_info = subparsers.add_parser("info", help="Show image header and detected SoC information")

    # Command: read
    p_read = subparsers.add_parser("read", aliases=["r"], help="Read an NV item value by key")
    p_read.add_argument("key", help="Key name (e.g. SN, USRKEY, FBLOCK, IMEI, BOARDID)")
    p_read.add_argument("-b", "--block", type=int, default=None, help="Specific block index (default: all active)")

    # Command: write
    p_write = subparsers.add_parser("write", aliases=["w"], help="Write a value to an NV item")
    p_write.add_argument("key", help="Key name (e.g. SN, USRKEY, FBLOCK, MACADDR)")
    p_write.add_argument("value", help="New value (ASCII string or hex with 0x prefix)")
    p_write.add_argument("--no-backup", action="store_true", help="Disable automatic .bak creation")
    p_write.add_argument("-o", "--output", help="Save to new file instead of overwriting")

    # Command: unlock-bl
    p_ubl = subparsers.add_parser("unlock-bl", help="Set bootloader unlock key (USRKEY)")
    p_ubl.add_argument("code", help="16-character unlock key or 64-char SHA256 hex string")
    p_ubl.add_argument("--plain", action="store_true", help="Force plain-text write without SHA-256")
    p_ubl.add_argument("--no-backup", action="store_true", help="Disable automatic .bak creation")
    p_ubl.add_argument("-o", "--output", help="Save to new file instead of overwriting")

    # Command: unlock-frp
    p_frp = subparsers.add_parser("unlock-frp", help="Set FBLOCK state to unlocked (0)")
    p_frp.add_argument("--lock", action="store_true", help="Set to locked (1) instead of unlocked (0)")
    p_frp.add_argument("--no-backup", action="store_true", help="Disable automatic .bak creation")
    p_frp.add_argument("-o", "--output", help="Save to new file instead of overwriting")

    # Command: list
    p_list = subparsers.add_parser("list", aliases=["ls"], help="List all valid NV items in the image")
    p_list.add_argument("-f", "--filter", help="Filter by key name substring")

    # Command: dump
    p_dump = subparsers.add_parser("dump", help="Export all NV items to JSON or CSV file")
    p_dump.add_argument("output", help="Output file path (.json or .csv)")

    # Command: verify
    p_verify = subparsers.add_parser("verify", help="Verify CRC32C checksums and block integrity")

    # Command: fix-crc
    p_fix = subparsers.add_parser("fix-crc", help="Recalculate and repair all broken CRC32C checksums")
    p_fix.add_argument("--no-backup", action="store_true", help="Disable automatic .bak creation")
    p_fix.add_argument("-o", "--output", help="Save to new file instead of overwriting")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        nve = HisiNveImage(args.image)
    except Exception as e:
        print(f"[!] Error loading image '{args.image}': {e}", file=sys.stderr)
        sys.exit(1)

    cmd = args.command

    if cmd == "info":
        print_banner()
        print(f"File Path:       {nve.filepath}")
        print(f"File Size:       {len(nve.raw_data):,} bytes ({len(nve.raw_data) // 1024} KB)")
        print(f"Total Blocks:    {len(nve.blocks)} (128 KB each)")
        print(f"Active Blocks:   {len(nve.active_blocks)}")
        if nve.detected_soc:
            print(f"Detected SoC:    {nve.detected_soc.display_name} ({nve.detected_soc.soc_name})")
            print(f"Hashed USRKEY:   {'Yes (SHA-256)' if nve.is_hashed_soc else 'No (Plain)'}")
        else:
            print("Detected SoC:    Unknown")
        
        if nve.active_blocks:
            ref = nve.active_blocks[0]
            print(f"Valid NV Items:  {ref.valid_items_count}")
            if ref.header:
                print(f"Partition Name:  {ref.header.partition_name}")
                print(f"NVE Version:     {ref.header.nve_version}")
                print(f"NVE Age:         {ref.header.nve_age}")

    elif cmd in ("read", "r"):
        key = args.key.strip().upper()
        if args.block is not None:
            item = nve.get_entry(key, block_index=args.block)
            if item:
                status = "OK" if item.verify_crc() else "CRC_MISMATCH"
                print(f"[+] Block {args.block} | {item.nv_name} (Slot #{item.index:03d}, Size: {item.valid_size}B, CRC: 0x{item.crc:08x} [{status}]):")
                if key == "FBLOCK":
                    f_val = item.value_bytes[0] if item.value_bytes else 255
                    desc = "Unlocked (0)" if f_val == 0 else ("Locked (1)" if f_val == 1 else f"Unknown ({f_val})")
                    print(f"    State: {desc}")
                else:
                    print(f"    Text:  {item.value_text}")
                    print(f"    Hex:   {item.value_bytes.hex()}")
            else:
                print(f"[-] Key '{key}' not found in Block {args.block}.")
        else:
            found_any = False
            for blk_idx, item in nve.read_all_blocks_for_key(key):
                if item:
                    found_any = True
                    status = "OK" if item.verify_crc() else "CRC_ERR"
                    if key == "FBLOCK":
                        f_val = item.value_bytes[0] if item.value_bytes else 255
                        val_str = "Unlocked (0)" if f_val == 0 else ("Locked (1)" if f_val == 1 else f"Unknown ({f_val})")
                    else:
                        val_str = item.value_text
                    print(f"[+] Block {blk_idx} | {item.nv_name}: {val_str} (CRC: 0x{item.crc:08x} [{status}])")
            if not found_any:
                print(f"[-] Key '{key}' not found in any active block.")

    elif cmd in ("write", "w"):
        key = args.key.strip().upper()
        raw_val = args.value
        if raw_val.startswith("0x") or raw_val.startswith("0X"):
            val_bytes = bytes.fromhex(raw_val[2:])
        else:
            val_bytes = raw_val.encode("utf-8")
        
        auto_bak = not args.no_backup
        success = nve.write_entry(key, val_bytes, auto_backup=auto_bak)
        if success:
            nve.save(args.output)
            out_file = args.output or nve.filepath
            print(f"[+] Successfully updated '{key}' across all active blocks!")
            print(f"[+] CRC32C recalculated and synchronized.")
            print(f"[+] Saved to: {out_file}")
        else:
            print(f"[-] Key '{key}' not found in image. Write failed.", file=sys.stderr)
            sys.exit(1)

    elif cmd == "unlock-bl":
        auto_bak = not args.no_backup
        auto_hash = not args.plain
        res = nve.set_bootloader_unlock_key(args.code, auto_hash=auto_hash, auto_backup=auto_bak)
        if res["success"]:
            nve.save(args.output)
            out_file = args.output or nve.filepath
            print("[+] Bootloader Unlock Key successfully configured!")
            print(f"    Mode:     {res['mode']}")
            print(f"    Code:     {res['code']}")
            print(f"    Hex:      {res['raw_hex']}")
            print(f"    Saved to: {out_file}")
            print("\n[i] Now flash this nvme.img in fastboot factory mode, then run:")
            print(f"    fastboot oem unlock {args.code}")
        else:
            print("[-] Failed to find USRKEY entry in image!", file=sys.stderr)
            sys.exit(1)

    elif cmd == "unlock-frp":
        auto_bak = not args.no_backup
        unlock_state = not args.lock
        success = nve.set_frp_fblock(unlock=unlock_state, auto_backup=auto_bak)
        if success:
            nve.save(args.output)
            out_file = args.output or nve.filepath
            state_str = "UNLOCKED (0)" if unlock_state else "LOCKED (1)"
            print(f"[+] Successfully set FBLOCK (FRP/Factory Lock) to: {state_str}")
            print(f"[+] Saved to: {out_file}")
        else:
            print("[-] Failed to find FBLOCK entry in image!", file=sys.stderr)
            sys.exit(1)

    elif cmd in ("list", "ls"):
        if not nve.active_blocks:
            print("[-] No active blocks found.")
            return
        ref = nve.active_blocks[0]
        flt = (args.filter or "").upper()
        print(f"Slot  | Name     | Size | CRC32C     | Status | Value Preview")
        print("-" * 65)
        for item in ref.items:
            if not item.is_valid:
                continue
            if flt and flt not in item.nv_name:
                continue
            crc_ok = "OK " if item.verify_crc() else "ERR"
            val_prev = item.value_text[:30].replace("\n", " ")
            print(f"#{item.index:03d}  | {item.nv_name:<8} | {item.valid_size:<4} | 0x{item.crc:08x} | {crc_ok}    | {val_prev}")

    elif cmd == "dump":
        summary = nve.export_summary()
        out_path = os.path.abspath(args.output)
        if out_path.lower().endswith(".csv"):
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Slot", "Name", "Property", "ValidSize", "CRC32C", "CRCValid", "HexData", "TextValue"])
                for item_dict in summary["items_list"]:
                    writer.writerow([item_dict["index"], item_dict["name"], item_dict["property"], item_dict["valid_size"], item_dict["crc"], item_dict["crc_valid"], item_dict["hex"], item_dict["text"]])
            print(f"[+] Successfully exported {len(summary['items_list'])} items to CSV: {out_path}")
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"[+] Successfully exported {len(summary['items_list'])} items to JSON: {out_path}")

    elif cmd == "verify":
        print_banner()
        print(f"Checking integrity of: {nve.filepath}...\n")
        res = nve.verify_integrity()
        for b_sum in res["block_summaries"]:
            status_str = "PASSED" if b_sum["crc_errors"] == 0 else f"FAILED ({b_sum['crc_errors']} errors)"
            print(f"  Block {b_sum['block']}: Header='{b_sum['header_name']}', Items={b_sum['valid_items']}, Age={b_sum['age']} -> {status_str}")
        
        print("-" * 65)
        print(f"Total Items Checked: {res['total_items_checked']}")
        print(f"Valid CRCs:          {res['valid_crc_count']}")
        print(f"Invalid CRCs:        {res['invalid_crc_count']}")
        if res["invalid_crc_count"] == 0:
            print("\n[+] INTEGRITY VERIFICATION PASSED: All partition blocks and item CRCs are 100% valid!")
        else:
            print(f"\n[!] WARNING: Found {res['invalid_crc_count']} CRC errors. You can run 'fix-crc' to repair them.")

    elif cmd == "fix-crc":
        auto_bak = not args.no_backup
        fixed = nve.fix_all_crcs(auto_backup=auto_bak)
        if fixed > 0:
            nve.save(args.output)
            out_file = args.output or nve.filepath
            print(f"[+] Repaired {fixed} broken CRC32C checksums across all blocks!")
            print(f"[+] Saved repaired image to: {out_file}")
        else:
            print("[+] All CRC checksums are already valid. No repair needed.")

if __name__ == "__main__":
    main()
