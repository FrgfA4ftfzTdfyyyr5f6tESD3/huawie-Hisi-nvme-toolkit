# HisiNve-Py

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-green.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![Pure Python](https://img.shields.io/badge/dependencies-Zero%20(Standard%20Library)-brightgreen.svg)]()

> **A 100% Pure Python offline reader, writer, bootloader unlocker, and partition manager for Huawei HiSilicon Kirin NVME (`nvme.img`) images.**

---

## 📖 Overview

In Huawei devices powered by HiSilicon Kirin SoCs, the **NVE** (Non-Volatile Environment / `nvme` partition) stores mission-critical hardware identifiers and security configuration data—including:
* **`USRKEY`**: Bootloader unlock key (plain 16-char ASCII or SHA-256 binary digest)
* **`FBLOCK`**: Factory & FRP lock state (`0` = Unlocked, `1` = Locked)
* **`SN` / `BOARDID` / `IMEI` / `MACADDR`**: Serial numbers and hardware identifiers
* **`WVLOCK` / `BATTCAL`**: DRM keys and factory calibration tables

### 💡 Why HisiNve-Py?
Previous tools (such as C-based PoCs) required a **rooted Android device** and shell access to run on-device binaries. Furthermore, older tools lacked hardware **CRC32C recalculation**, causing partition write operations to fail or be rejected by bootloaders on newer chipsets (such as Kirin 710, 970, 980, 990).

**HisiNve-Py runs 100% offline on your PC**, takes an `nvme.img` partition backup, applies your desired changes with **hardware-accurate Castagnoli CRC32C recalculation**, synchronizes all 7 redundant partition blocks, and prepares the image ready to be flashed back via **Factory Fastboot / Testpoint mode—with zero root or ADB requirements.**

---

## 🚀 Key Features

* **Zero Device Root Required:** Works directly on raw `nvme.img` partition backup files on Windows, Linux, and macOS.
* **Hardware-Accurate Castagnoli CRC32C:** Implements polynomial `0x1EDC6F41` (`0x82F63B78` reflected) across all 128-byte item slots, resolving the write limitation on Kirin 710 and newer chipsets.
* **Multi-Block Redundant Synchronization:** Automatically synchronizes and signs all 7 active reliable blocks (Blocks 1–7) in `nvme.img`.
* **Automatic Safe Backups:** Generates timestamped `.bak` files before any write or modification.
* **Bootloader Unlock Helper (`unlock-bl`):** Configures any 16-character unlock code with automated SHA-256 binary hashing.
* **FRP / Factory Unlock Helper (`unlock-frp`):** Toggles `FBLOCK` between `0` (Unlocked) and `1` (Locked).
* **Dual Interface:** Includes both an interactive CLI wizard (`main.py`) and a scriptable command-line interface (`hisi_nve_cli.py`).
* **Integrity Auditing & Repair:** `verify` scans all blocks for corrupt CRCs, and `fix-crc` automatically repairs broken checksums.
* **Zero External Dependencies:** Built entirely with Python's standard library.

---

## 📱 Kirin SoC Compatibility Matrix

| Chipset Family | SoC Code Name | NVE Item Count | USRKEY Format | Read Support | Write Support |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Kirin 620** | `hi6210sft` | ~330 | Plain ASCII (16-char) | ✅ | ✅ |
| **Kirin 650 / 655 / 658 / 659** | `hi6250` | ~379 | SHA-256 Hashed | ✅ | ✅ |
| **Kirin 950 / 955** | `hi3650` | ~352 | SHA-256 Hashed | ✅ | ✅ |
| **Kirin 960** | `hi3660` | ~376 | SHA-256 Hashed | ✅ | ✅ |
| **Kirin 710 / 710F / 710A** | `kirin710` | ~416 | SHA-256 Hashed | ✅ | ✅ |
| **Kirin 970** | `kirin970` | ~393 | SHA-256 Hashed | ✅ | ✅ |
| **Kirin 980** | `kirin980` | ~415 | SHA-256 Hashed | ✅ | ✅ |
| **Kirin 990 4G / 5G / 990E** | `kirin990` | ~701 | SHA-256 Hashed | ✅ | ✅ |
| **Kirin 810 / 820 / 9000** | `kirin810` / `kirin9000` | ~450–800 | SHA-256 Hashed | ✅ | ✅ |

---

## 📦 Installation

Clone the repository and run directly:
```bash
git clone https://github.com/your-username/hisi-nve-py.git
cd hisi-nve-py
```

Optional: Install as a system command:
```bash
pip install -e .
```

---

## 💻 Usage

### 1. Interactive Wizard (Recommended)
Launch the interactive menu:
```bash
python main.py
```

### 2. Command Line Interface (CLI)

#### View Image Information & Detected SoC:
```bash
python hisi_nve_cli.py nvme.img info
```

#### Read an NV Item (e.g. SN, FBLOCK, USRKEY, IMEI):
```bash
python hisi_nve_cli.py nvme.img read SN
python hisi_nve_cli.py nvme.img read FBLOCK
python hisi_nve_cli.py nvme.img read USRKEY
```

#### Set Bootloader Unlock Key (USRKEY):
```bash
python hisi_nve_cli.py nvme.img unlock-bl 0123456789ABCDEF
```

#### Unlock FRP / Factory Lock:
```bash
python hisi_nve_cli.py nvme.img unlock-frp
```

#### Modify a Custom Key:
```bash
python hisi_nve_cli.py nvme.img write SN "8JN4C17A12345678"
```

#### Verify Image Integrity & CRC32C Checksums:
```bash
python hisi_nve_cli.py nvme.img verify
```

#### Repair Broken Checksums:
```bash
python hisi_nve_cli.py nvme.img fix-crc
```

#### Export Full Partition Dump (JSON / CSV):
```bash
python hisi_nve_cli.py nvme.img dump output.json
python hisi_nve_cli.py nvme.img dump output.csv
```

#### List All Valid Items:
```bash
python hisi_nve_cli.py nvme.img list
```

---

## ⚡ Factory Fastboot Flashing Guide

After customizing your `nvme.img`:
1. Connect your device in **Factory Fastboot mode** (or via Testpoint / USB COM 1.0 download mode).
2. Flash the updated partition:
   ```bash
   fastboot flash nvme nvme.img
   ```
3. If you configured a bootloader unlock key:
   ```bash
   fastboot oem unlock 0123456789ABCDEF
   ```
4. Verify lock state:
   ```bash
   fastboot oem lock-state info
   ```

---

## 🔬 Technical Details: Partition & CRC Layout

Each Huawei Kirin NVE partition is structured as follows:
* **Block 0 (0x00000 - 0x20000):** Raw padding / junk block (128 KB).
* **Blocks 1–7 (0x20000 - 0x100000):** Seven redundant 128 KB active blocks.
* **Per-Block Layout (128 KB = 131,072 bytes):**
  * **1023 Item Slots:** 128 bytes each (`1023 * 128 = 130,944 bytes` = `0x1FF80`).
  * **1 Partition Header:** 128 bytes at `0x1FF80` (`Hisi-NV-Partition`, age counter, item count).
* **Per-Item Struct Layout (128 bytes):**
  * `0x00..0x03` (4B): `nv_number` (uint32)
  * `0x04..0x0B` (8B): `nv_name` (ASCII)
  * `0x0C..0x0F` (4B): `nv_property` (uint32)
  * `0x10..0x13` (4B): `valid_size` (uint32)
  * `0x14..0x17` (4B): `crc` (Castagnoli CRC32C computed over `[0x00..0x13] + [0x18..0x7F]`)
  * `0x18..0x7F` (104B): `nv_data` (payload padded with zeros)

---

## 🤝 Credits & Acknowledgements

* Based on reverse engineering and research from the original [hisi-nve](https://github.com/R0rt1z2/hisi-nve) project by **Roger Ortiz (R0rt1z2)** and contributors.
* Reference kernel driver specifications from Huawei / HiSilicon open-source Linux kernel releases (`drivers/huawei_platform/nve/`).

---

## ⚠️ Disclaimer

This tool is created for educational, device repair, and firmware recovery purposes only. Always maintain an original, unmodified backup of your `nvme.img` before making changes. The authors are not responsible for any misuse or device bricks.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**. See [LICENSE](LICENSE) for details.
