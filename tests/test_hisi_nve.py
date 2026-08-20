import os
import shutil
import tempfile
import unittest
import hashlib
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from hisi_nve import (
    HisiNveImage,
    NVEPartitionHeader,
    NVItem,
    NVE_BLOCK_SIZE,
    NV_ITEM_SIZE,
    NV_ITEMS_PER_BLOCK,
    crc32c,
    compute_nv_item_crc
)

class TestHisiNve(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_img = os.path.join(self.tmp_dir, "synthetic_nvme.img")
        self._create_synthetic_nvme_image(self.tmp_img)
        self.nve = HisiNveImage(self.tmp_img)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_synthetic_nvme_image(self, path: str):
        """Creates a valid synthetic 1MB NVE image for self-contained unit testing."""
        img = bytearray(8 * NVE_BLOCK_SIZE)
        
        # Block 0: Empty padding
        # Blocks 1..7: Active NVE partitions with generic dummy data
        test_items_def = [
            (0, "SWVERSI", 0, 5, b"T8300"),
            (1, "BOARDID", 1, 16, b"BOARD_GENERIC_01"),
            (2, "SN", 1, 16, b"SN_DUMMY_123456"),
            (3, "MACADDR", 1, 12, b"001122334455"),
            (4, "WVLOCK", 1, 32, b"UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU"),
            (5, "FBLOCK", 1, 1, b"\x01"),
            (6, "USRKEY", 1, 32, b"UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU"),
        ]

        for b_idx in range(1, 8):
            b_offset = b_idx * NVE_BLOCK_SIZE
            # Populate items
            for idx, name, prop, sz, data in test_items_def:
                it = NVItem(
                    index=idx,
                    nv_number=idx,
                    nv_name=name,
                    nv_property=prop,
                    valid_size=sz,
                    crc=0,
                    nv_data=data.ljust(104, b"\x00")
                )
                packed = it.pack(update_crc=True)
                slot_offset = b_offset + idx * NV_ITEM_SIZE
                img[slot_offset:slot_offset + NV_ITEM_SIZE] = packed

            # Set partition header
            hdr = NVEPartitionHeader(
                raw_offset=b_offset + NVE_BLOCK_SIZE - 128,
                partition_name="Hisi-NV-Partition",
                nve_version=1,
                nve_block_id=1,
                nve_block_count=1,
                valid_items=len(test_items_def),
                nv_checksum=0,
                nve_crc_support=2,
                reserved=b"\x00" * 68,
                nve_age=1000 + b_idx
            )
            hdr_offset = b_offset + NVE_BLOCK_SIZE - 128
            img[hdr_offset:hdr_offset + 128] = hdr.pack()

        with open(path, "wb") as f:
            f.write(img)

    def test_crc32c_vectors(self):
        """Test CRC32C against standard known test vectors."""
        self.assertEqual(crc32c(b""), 0x00000000)
        self.assertEqual(crc32c(b"123456789"), 0xe3069283)
        self.assertEqual(crc32c(b"\x00" * 32), 0x8a9136aa)

    def test_image_load_and_active_blocks(self):
        """Verify image structure."""
        self.assertEqual(len(self.nve.blocks), 8)
        self.assertEqual(len(self.nve.active_blocks), 7)
        self.assertTrue(self.nve.is_hashed_soc)

    def test_verify_all_crcs(self):
        """Verify that all items in all 7 blocks have 100% valid CRC32C."""
        res = self.nve.verify_integrity()
        self.assertEqual(res["invalid_crc_count"], 0)
        self.assertEqual(res["total_items_checked"], 7 * 7)
        self.assertEqual(res["valid_crc_count"], 7 * 7)

    def test_read_critical_keys(self):
        """Verify reading of known keys."""
        sn = self.nve.get_entry("SN")
        self.assertIsNotNone(sn)
        self.assertTrue(sn.value_text.startswith("SN_DUMMY_123456"))

        fblock = self.nve.get_entry("FBLOCK")
        self.assertIsNotNone(fblock)
        self.assertEqual(fblock.value_bytes, b"\x01")

        usrkey = self.nve.get_entry("USRKEY")
        self.assertIsNotNone(usrkey)
        self.assertEqual(len(usrkey.value_bytes), 32)

    def test_unlock_bootloader_usrkey(self):
        """Test setting bootloader unlock key and verifying CRC across all blocks."""
        test_code = "0123456789ABCDEF"
        res = self.nve.set_bootloader_unlock_key(test_code, auto_hash=True, auto_backup=False)
        self.assertTrue(res["success"])
        self.nve.save()

        reloaded = HisiNveImage(self.tmp_img)
        expected_hash = hashlib.sha256(test_code.encode("ascii")).digest()

        for blk in reloaded.active_blocks:
            item = blk.get_item("USRKEY")
            self.assertIsNotNone(item)
            self.assertEqual(item.value_bytes, expected_hash)
            self.assertTrue(item.verify_crc())

        int_res = reloaded.verify_integrity()
        self.assertEqual(int_res["invalid_crc_count"], 0)

    def test_unlock_frp_fblock(self):
        """Test setting FBLOCK to 0 (unlocked) and verifying CRC."""
        success = self.nve.set_frp_fblock(unlock=True, auto_backup=False)
        self.assertTrue(success)
        self.nve.save()

        reloaded = HisiNveImage(self.tmp_img)
        for blk in reloaded.active_blocks:
            item = blk.get_item("FBLOCK")
            self.assertIsNotNone(item)
            self.assertEqual(item.value_bytes, b"\x00")
            self.assertTrue(item.verify_crc())

        int_res = reloaded.verify_integrity()
        self.assertEqual(int_res["invalid_crc_count"], 0)

    def test_write_custom_entry(self):
        """Test modifying custom key like BOARDID."""
        new_board = "TEST_BOARD_GENERIC"
        success = self.nve.write_entry("BOARDID", new_board, auto_backup=False)
        self.assertTrue(success)
        self.nve.save()

        reloaded = HisiNveImage(self.tmp_img)
        for blk in reloaded.active_blocks:
            item = blk.get_item("BOARDID")
            self.assertIsNotNone(item)
            self.assertEqual(item.value_text, new_board)
            self.assertTrue(item.verify_crc())

    def test_dump_export(self):
        """Test export summary to dictionary."""
        summary = self.nve.export_summary()
        self.assertEqual(summary["total_entries"], 7)
        self.assertIn("SN", summary["items"])
        self.assertIn("USRKEY", summary["items"])
        self.assertIn("FBLOCK", summary["items"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
