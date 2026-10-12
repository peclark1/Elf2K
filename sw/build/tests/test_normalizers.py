"""Regression tests for disposable-tree RcAsm source normalization."""
from __future__ import annotations

import pathlib
import runpy
import tempfile
import unittest

BUILD = pathlib.Path(__file__).resolve().parents[1]
normalize_source = runpy.run_path(str(BUILD / "normalize-rcasm.py"))["normalize"]
normalize_include = runpy.run_path(str(BUILD / "normalize-rcasm-include.py"))["normalize"]
prepare_asm02 = runpy.run_path(str(BUILD / "prepare-asm02-source.py"))["normalize"]


def transform(source: str, fn=normalize_source) -> str:
    with tempfile.TemporaryDirectory() as temporary:
        path = pathlib.Path(temporary) / "input.asm"
        path.write_text(source, encoding="utf-8")
        (path.parent / "config.inc").write_text(
            "#define RAMPAGE 07F00H\n#define VISUAL 0B100H\n#define BIOS 0FF00H\n#define EBIOS 0F800H\n",
            encoding="utf-8",
        )
        (path.parent / "bios.inc").write_text(
            "#define f_type (BIOS+03h)\n"
            "#define f_inmsg (BIOS+66h)\n"
            "#define f_msg (BIOS+09h)\n"
            "#define f_input (BIOS+0fh)\n"
            "#define f_initcall (BIOS+3fh)\n",
            encoding="utf-8",
        )
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
        self.assertEqual(lines[0].strip(), "include bios.inc")
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



class Asm02IncludeTests(unittest.TestCase):
    def test_stock_visual02_includes(self) -> None:
        source = (
            "#include ../ops.inc\n"
            "#ifdef STGROM\n"
            "include config.inc\n"
            "include    ../bios.inc\n"
            "#endif\n"
        )
        self.assertEqual(
            transform(source, prepare_asm02),
            (
                "#include ops.inc\n"
                "#ifdef STGROM\n"
                "#include config.inc\n"
                "#include bios.inc\n"
                "#endif\n"
            ),
        )

    def test_non_stg_conditional_include_remains(self) -> None:
        source = "#ifdef ELFOS\n#include ../Elfos/kernel.inc\n#endif\n"
        self.assertEqual(transform(source, prepare_asm02), source)

    def test_include_conversion_idempotent(self) -> None:
        source = "   include ../bios.inc  ; relocated\n"
        first = transform(source, prepare_asm02)
        self.assertEqual(transform(first, prepare_asm02), first)

    def test_stgrom_services_derived_from_bios_include(self) -> None:
        source = (
            "#ifdef STGROM\n"
            "#define CODE VISUAL\n"
            "#define DATA RAMPAGE-0100h\n"
            "asm: mov r0,edtasm+3\n"
            "#endif\n"
        )
        result = transform(source, prepare_asm02)
        self.assertIn("#define FTYPE (0FF00H+03h)", result)
        self.assertIn("#define FINMSG (0FF00H+66h)", result)
        self.assertIn("#define FMSG (0FF00H+09h)", result)
        self.assertIn("#define FINPUT (0FF00H+0fh)", result)
        self.assertIn("asm: mov r0,EDTASM+3", result)

    def test_stgrom_aliases_are_not_duplicated_on_second_pass(self) -> None:
        source = (
            "#ifdef STGROM\n"
            "#define DATA RAMPAGE-0100h\n"
            "#endif\n"
        )
        first = transform(source, prepare_asm02)
        self.assertEqual(transform(first, prepare_asm02), first)

    def test_stock_constants_are_expanded_in_secondary_defines(self) -> None:
        source = "#define CODE VISUAL\n#define DATA RAMPAGE-0100h\n"
        self.assertEqual(
            transform(source, prepare_asm02),
            "#define CODE 0B100H\n#define DATA 07F00H-0100h\n",
        )

    def test_quoted_asm02_include_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unquoted"):
            transform('#include "ops.inc"\n', prepare_asm02)

    def test_known_upstream_orphan_removed(self) -> None:
        source = (
            "exit: sep scall\n"
            "      sep r0 ; exit\n"
            "#endif\n"
            "\n"
            "#ifdef ANYROM\n"
            "asm: nop\n"
            "#endif\n"
        )
        result = transform(source, prepare_asm02)
        self.assertNotIn("sep r0 ; exit\n#endif", result)
        self.assertEqual(result.count("#endif"), 1)

    def test_other_orphan_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unexpected unmatched"):
            transform("nop\n#endif\n", prepare_asm02)

    def test_unclosed_conditional_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unclosed"):
            transform("#ifdef STGROM\nnop\n", prepare_asm02)


if __name__ == "__main__":
    unittest.main()
