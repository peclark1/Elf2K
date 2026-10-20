"""Unit tests for the offline historical CHIP-8 game analyzer."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name("chip8-library.py")
spec = importlib.util.spec_from_file_location("chip8_library", SOURCE)
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)


class Chip8LibraryTests(unittest.TestCase):
    def test_known_vip_opcodes(self):
        for opcode in (0x00E0, 0x00EE, 0x6205, 0x8124, 0xD125, 0xE49E,
                       0xE4A1, 0xF207, 0xF20A, 0xF255, 0xF265):
            with self.subTest(opcode=hex(opcode)):
                self.assertEqual(library.opcode_type(opcode), "vip")

    def test_extended_opcodes(self):
        for opcode in (0x00FF, 0x00FB, 0x00C4, 0xD120, 0xF030,
                       0xF175, 0xF185, 0x8128):
            with self.subTest(opcode=hex(opcode)):
                self.assertEqual(library.opcode_type(opcode), "extended")

    def test_reachable_only_no_false_sprite_opcodes(self):
        # 1206 jumps over 00FF and 00E0 sprite/data to 00EE at 0206.
        result = library.audit_code(bytes.fromhex("120600FF00E000EE"))
        self.assertEqual(result["unsupported_opcodes"], [])
        self.assertEqual(result["reachable_instructions"], 2)

    def test_reachable_extended_excluded(self):
        result = library.audit_code(bytes.fromhex("00FF00EE"))
        self.assertIn("0200:00FF", result["unsupported_opcodes"])

    def test_bnnn_warned_not_misidentified(self):
        result = library.audit_code(bytes.fromhex("B2020000"))
        self.assertTrue(any("BNNN" in w for w in result["flow_warnings"]))

    def test_hex_full_and_partial_record_round_trip(self):
        payload = bytes(range(39))
        text = library.make_hex(payload)
        self.assertIn(":00000001FF", text)
        library.verify_hex(text, payload)

    def test_corrupt_hex_checksum_rejected(self):
        text = library.make_hex(bytes(range(12)))
        altered = text.replace("00010203", "00010204", 1)
        with self.assertRaises(ValueError):
            library.verify_hex(altered, bytes(range(12)))

    def test_full_2k_image_safe_end_address(self):
        payload = bytes([0x00, 0xEE]) * 1024
        text = library.make_hex(payload)
        library.verify_hex(text, payload)
        self.assertEqual(library.BASE + len(payload), 0xA00)

    def test_et660_not_mistaken_for_vip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "Airplane.ch8"
            p.write_bytes(bytes.fromhex("00E0"))
            status, reason = library.classify(
                p, p.read_bytes(), "", library.audit_code(p.read_bytes()))
            self.assertEqual(status, "incompatible")
            self.assertTrue(any("ETI-660" in s for s in reason))

    def test_known_1979_no_unsupported_is_likely(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "Breakout [Carmelo Cortez, 1979].ch8"
            p.write_bytes(bytes.fromhex("00EE"))
            status, reason = library.classify(
                p, p.read_bytes(), "", library.audit_code(p.read_bytes()))
            self.assertEqual((status, reason), ("likely", []))


if __name__ == "__main__":
    unittest.main()
