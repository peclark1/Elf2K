"""Regression tests for disposable-tree RcAsm source normalization."""
from __future__ import annotations

import pathlib
import runpy
import tempfile
import unittest

BUILD = pathlib.Path(__file__).resolve().parents[1]
normalize_source = runpy.run_path(str(BUILD / "normalize-rcasm.py"))["normalize"]
normalize_include = runpy.run_path(str(BUILD / "normalize-rcasm-include.py"))["normalize"]


def transform(source: str, fn=normalize_source) -> str:
    with tempfile.TemporaryDirectory() as temporary:
        path = pathlib.Path(temporary) / "input.asm"
        path.write_text(source, encoding="utf-8")
        fn(path)
        return path.read_text(encoding="utf-8")


class RcAsmNormalizerTests(unittest.TestCase):
    def test_include_inline_semicolon_comment(self) -> None:
        source = "        INCLUDE config.inc              ;[RLA] addresses and options\n"
        result = transform(source)
        self.assertEqual(
            result,
            "        INCLUDE config.inc\n;[RLA] addresses and options\n",
        )

    def test_include_tabs_and_lowercase(self) -> None:
        result = transform("\tinclude\tbios.inc\t ; old include comment\n")
        lines = result.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].strip(), "include        bios.inc")
        self.assertEqual(lines[1], "; old include comment")

    def test_plain_include_and_preprocessor_include_unchanged(self) -> None:
        source = "include config.inc\n#include \"ops.inc\"\n"
        self.assertEqual(transform(source), source)

    def test_normalizer_preserves_comment_only_lines(self) -> None:
        source = "  ; include config.inc ; not executable\n"
        self.assertEqual(transform(source), source)

    def test_label_instruction_with_symbol_splits(self) -> None:
        self.assertEqual(
            transform("entry: lbr FORTH  ; branch\n"),
            "entry:\n        lbr FORTH  ; branch\n",
        )

    def test_equ_label_remains_on_same_line(self) -> None:
        source = "symbol: equ 1234h\nother: .EQU symbol\n"
        self.assertEqual(transform(source), source)

    def test_label_without_code_unchanged(self) -> None:
        source = "label:\nlabel2:   ; just a comment\n"
        self.assertEqual(transform(source), source)

    def test_idempotent(self) -> None:
        src = "  include config.inc ; comment\nstart: lbr XMODEM\n"
        once = transform(src)
        self.assertEqual(transform(once), once)

    def test_bios_equ_conversion(self) -> None:
        result = transform(
            "SERIAL: equ 0F000h ; docs\n#ifdef ELF2K\n#endif\n",
            normalize_include,
        )
        self.assertEqual(
            result,
            "#define SERIAL 0F000h\n; docs\n#ifdef ELF2K\n#endif\n",
        )

    def test_bios_non_equ_unchanged(self) -> None:
        source = "include config.inc\n"
        self.assertEqual(transform(source, normalize_include), source)


if __name__ == "__main__":
    unittest.main()
