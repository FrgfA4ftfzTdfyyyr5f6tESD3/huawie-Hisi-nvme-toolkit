#!/usr/bin/env python3
"""
HisiNve Interactive - Interactive CLI Wizard for Huawei Kirin NVME partitions.
100% Pure Python | Offline Safe | Hardware-Accurate Castagnoli CRC32C
"""
import sys
import os
import shutil
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hisi_nve import HisiNveImage, SocProfile, SOC_PROFILES

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_header(title=""):
    print("=" * 72)
    print("  ★ HisiNve-Py v3.0 - Huawei Kirin NVME Partition Manager ★")
    print("  ★ 100% Pure Python | Offline Safe | Hardware-Accurate CRC32C ★")
    print("=" * 72)
    if title:
        print(f"  >>> {title}")
        print("-" * 72)

def prompt_image_path() -> str:
    print_header("Select NVME Partition Image (nvme.img)")
    default_name = "nvme.img"
    
    if os.path.exists(default_name):
        print(f"[1] Use '{default_name}' in current working directory")
        print("[2] Enter custom path to nvme.img")
        choice = input("\nEnter choice (1/2, default: 1): ").strip()
        if choice == "2":
            path = input("Enter path to nvme.img: ").strip().strip('"')
        else:
            path = default_name
    else:
        path = input("Enter path to nvme.img: ").strip().strip('"')
        
    return path

def main():
    clear_screen()
    img_path = prompt_image_path()

    try:
        nve = HisiNveImage(img_path)
    except Exception as e:
        print(f"\n[!] Error loading image file: {e}")
        input("\nPress Enter to exit...")
        return

    while True:
        clear_screen()
        print_header(f"Loaded: {os.path.basename(nve.filepath)}")
        soc_display = nve.detected_soc.display_name if nve.detected_soc else "Unknown Kirin SoC"
        print(f"  • File Size:          {len(nve.raw_data):,} bytes ({len(nve.raw_data) // 1024} KB)")
        print(f"  • Detected SoC:       {soc_display}")
        print(f"  • Active Sync Blocks: {len(nve.active_blocks)} blocks (Blocks 1..{len(nve.active_blocks)})")
        print(f"  • USRKEY Mode:        {'SHA-256 Hashed (32-byte)' if nve.is_hashed_soc else 'Plain String'}")
        print("-" * 72)
        print("  [1] Read NV Item Value (SN, IMEI, MACADDR, USRKEY, FBLOCK, ...)")
        print("  [2] Set Bootloader Unlock Key (USRKEY Helper)")
        print("  [3] Unlock FRP / Factory Lock (FBLOCK = 0)")
        print("  [4] Write / Modify Custom NV Item (SN, BOARDID, MACADDR, ...)")
        print("  [5] Verify Integrity & CRC32C Checksums on All Blocks")
        print("  [6] Auto-Repair & Recalculate Broken CRC32C Checksums")
        print("  [7] Export Full Partition Dump (JSON / CSV)")
        print("  [8] List All Valid NV Items in Partition")
        print("  [9] Create Manual Backup (.bak)")
        print("  [0] Exit")
        print("=" * 72)
        
        opt = input("Please select an option (0-9): ").strip()
        
        if opt == "0":
            print("\nExiting HisiNve-Py. Goodbye!")
            break
            
        elif opt == "1":
            clear_screen()
            print_header("Read NV Item Entry")
            key = input("Enter item key name (e.g. SN, USRKEY, FBLOCK, BOARDID, MACADDR, IMEI): ").strip().upper()
            if key:
                print("\nSearch results across partition blocks:")
                found = False
                for blk_idx, item in nve.read_all_blocks_for_key(key):
                    if item:
                        found = True
                        status = "CRC OK" if item.verify_crc() else "CRC ERROR"
                        if key == "FBLOCK":
                            f_val = item.value_bytes[0] if item.value_bytes else 255
                            val_str = "Unlocked (0)" if f_val == 0 else ("Locked (1)" if f_val == 1 else f"Unknown ({f_val})")
                        else:
                            val_str = item.value_text
                        print(f"  • Block {blk_idx} | {item.nv_name}: {val_str} | Size: {item.valid_size} bytes | CRC: 0x{item.crc:08x} [{status}]")
                        print(f"    Raw Hex: {item.value_bytes.hex()}")
                if not found:
                    print(f"  [-] Item '{key}' not found in any active block.")
            input("\nPress Enter to return to menu...")

        elif opt == "2":
            clear_screen()
            print_header("Set Bootloader Unlock Key (USRKEY)")
            print("Info: You can set any desired 16-character unlock code (e.g., 0123456789ABCDEF).")
            print("The tool automatically computes the exact SHA-256 hash and hardware CRC32C,")
            print("synchronizing it across all 7 redundant partition blocks.")
            print("-" * 72)
            code = input("Enter 16-character unlock code (e.g. 0123456789ABCDEF): ").strip()
            if len(code) == 16:
                confirm = input(f"Are you sure you want to write unlock code '{code}'? (y/n): ").strip().lower()
                if confirm == "y":
                    res = nve.set_bootloader_unlock_key(code, auto_hash=True, auto_backup=True)
                    if res["success"]:
                        nve.save()
                        print("\n[+] Unlock key successfully configured and synced across all blocks!")
                        print(f"    • Storage Mode: {res['mode']}")
                        print(f"    • Binary Digest: {res['raw_hex']}")
                        print(f"    • Backup created automatically.")
                        print("\n[i] Next steps in Factory Fastboot mode:")
                        print("    1. Flash partition:  fastboot flash nvme nvme.img")
                        print(f"    2. Unlock phone:     fastboot oem unlock {code}")
                    else:
                        print("\n[!] Failed to find USRKEY entry in image.")
            else:
                print("\n[!] Unlock code must be exactly 16 characters long.")
            input("\nPress Enter to return to menu...")

        elif opt == "3":
            clear_screen()
            print_header("Unlock FRP / Factory Block (FBLOCK)")
            print("In Huawei devices, FBLOCK = 0 indicates Unlocked state, while 1 is Locked.")
            print("-" * 72)
            print("[1] Unlock FRP (Set FBLOCK = 0)")
            print("[2] Lock FRP (Set FBLOCK = 1)")
            f_opt = input("Your choice (1/2): ").strip()
            if f_opt in ("1", "2"):
                unlock_st = (f_opt == "1")
                nve.set_frp_fblock(unlock=unlock_st, auto_backup=True)
                nve.save()
                st_text = "UNLOCKED (0)" if unlock_st else "LOCKED (1)"
                print(f"\n[+] Successfully updated FBLOCK to {st_text} with recalculated CRC32C.")
            input("\nPress Enter to return to menu...")

        elif opt == "4":
            clear_screen()
            print_header("Write / Modify Custom NV Item")
            key = input("Enter item key name (e.g. SN, BOARDID, MACADDR, ...): ").strip().upper()
            if key:
                cur = nve.get_entry(key)
                if cur:
                    print(f"  • Current Value: {cur.value_text} (Length: {cur.valid_size} bytes)")
                    new_val = input("Enter new value: ").strip()
                    if new_val:
                        confirm = input("Synchronize and save across all blocks? (y/n): ").strip().lower()
                        if confirm == "y":
                            nve.write_entry(key, new_val, auto_backup=True)
                            nve.save()
                            print(f"\n[+] Item '{key}' updated successfully across all active blocks.")
                else:
                    print(f"[-] Item '{key}' not found in image.")
            input("\nPress Enter to return to menu...")

        elif opt == "5":
            clear_screen()
            print_header("Verify Integrity & CRC32C Checksums")
            res = nve.verify_integrity()
            for b_sum in res["block_summaries"]:
                status_str = "PASSED (100% Valid)" if b_sum["crc_errors"] == 0 else f"FAILED ({b_sum['crc_errors']} CRC errors)"
                print(f"  • Block {b_sum['block']}: Header='{b_sum['header_name']}', Items={b_sum['valid_items']}, Age={b_sum['age']} -> {status_str}")
            print("-" * 72)
            print(f"  Total Items Checked: {res['total_items_checked']}")
            print(f"  Valid CRC32C Count:  {res['valid_crc_count']}")
            print(f"  Invalid CRC Count:   {res['invalid_crc_count']}")
            if res["invalid_crc_count"] == 0:
                print("\n[+] SUCCESS: Partition structure and all CRC32C checksums are 100% valid and ready for flashing!")
            else:
                print(f"\n[!] WARNING: Found {res['invalid_crc_count']} invalid CRCs. You can repair them with option 6.")
            input("\nPress Enter to return to menu...")

        elif opt == "6":
            clear_screen()
            print_header("Auto-Repair All CRC32C Checksums")
            confirm = input("Recalculate and repair all CRC32C checksums in the image? (y/n): ").strip().lower()
            if confirm == "y":
                fixed = nve.fix_all_crcs(auto_backup=True)
                if fixed > 0:
                    nve.save()
                    print(f"\n[+] Repaired {fixed} CRC32C checksums across all blocks!")
                else:
                    print("\n[+] All CRC checksums are already 100% valid. No repair needed.")
            input("\nPress Enter to return to menu...")

        elif opt == "7":
            clear_screen()
            print_header("Export Full Dump (JSON / CSV)")
            dump_name = input("Enter output filename (default: nve_dump.json): ").strip() or "nve_dump.json"
            summary = nve.export_summary()
            if dump_name.lower().endswith(".csv"):
                import csv
                with open(dump_name, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Slot", "Name", "Property", "ValidSize", "CRC32C", "CRCValid", "HexData", "TextValue"])
                    for item_dict in summary["items_list"]:
                        writer.writerow([item_dict["index"], item_dict["name"], item_dict["property"], item_dict["valid_size"], item_dict["crc"], item_dict["crc_valid"], item_dict["hex"], item_dict["text"]])
                print(f"\n[+] Exported {len(summary['items_list'])} items to CSV: '{dump_name}'")
            else:
                with open(dump_name, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                print(f"\n[+] Exported {len(summary['items_list'])} items to JSON: '{dump_name}'")
            input("\nPress Enter to return to menu...")

        elif opt == "8":
            clear_screen()
            print_header("List All NV Items")
            ref = nve.active_blocks[0] if nve.active_blocks else None
            if ref:
                print(f"Slot  | Name     | Size  | CRC32C     | Status | Value Preview")
                print("-" * 72)
                for item in ref.items:
                    if item.is_valid:
                        st = "OK " if item.verify_crc() else "ERR"
                        val_str = item.value_text[:28].replace("\n", " ")
                        print(f"#{item.index:03d}  | {item.nv_name:<8} | {item.valid_size:<4}B | 0x{item.crc:08x} | {st}    | {val_str}")
            input("\nPress Enter to return to menu...")

        elif opt == "9":
            clear_screen()
            print_header("Create Manual Backup")
            bak_path = nve.create_backup()
            print(f"\n[+] Backup created successfully:\n    {bak_path}")
            input("\nPress Enter to return to menu...")

if __name__ == "__main__":
    main()
