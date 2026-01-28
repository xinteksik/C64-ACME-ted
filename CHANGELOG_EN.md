# Changelog - C64-ACME-ted

All notable changes to this project will be documented in this file.

---

## [1.1.0] - 2026-01-28 - Accurate ASM ↔ HEX Mapping via ACME Report File

### Major Improvements

1. **100% Accurate ASM → HEX Mapping**
   - Uses ACME report file (`-r` parameter) for precise mapping
   - Correctly handles multiple `* = offset` directives
   - Works with `!source` includes and macro expansions
   - Line 3649 now correctly maps to offset 0x186F instead of 0x1768
   - **Critical fix**: Abandoned manual byte counting in favor of ACME's native report format

2. **Byte-Level Highlighting in HEX Dump**
   - Changed from highlighting entire 8-byte rows to exact byte ranges
   - Shows only bytes that belong to current ASM instruction
   - Example: `!word $9879,$9882` highlights only 4 bytes, not full 8-byte row
   - Individual byte rendering with precise `A_REVERSE` highlighting

3. **Vertical Synchronization of ASM and HEX Views**
   - When cursor is on line 10 in ASM editor, highlighting appears on line 10 in HEX dump
   - Synchronized scroll positions maintain visual alignment
   - Formula: `hex_scroll_offset = highlighted_hex_line - asm_screen_pos`
   - Both views have identical height (height - 11) for perfect alignment

4. **Hex Bytes in Status Bar**
   - Current line's hex bytes displayed in status bar
   - Format: `[4C BA 92]` for easy byte inspection
   - Shows up to 8 bytes for current instruction
   - Extracted from precise ACME report mapping

5. **Improved Label Navigation**
   - 'j' key now jumps to label (instead of scrolling)
   - Supports `!word LABEL` and `!word LABEL-1` syntax
   - Math operators (+, -, *, /) automatically stripped from labels
   - Prioritizes label definitions over usage instances

6. **CBM vs Plain Format Detection**
   - Automatic detection of `!to "file", cbm` vs `!to "file", plain`
   - CBM format: skips 2-byte load address header
   - Plain format: data starts at offset 0
   - Correct offset calculation for both formats

### Technical Changes

**New Functions:**
- `build_mappings_from_report()` - Parse ACME report file for accurate line→offset mapping
- `get_hex_range_for_asm_line(asm_line)` - Get (offset, num_bytes) for specific line
- `get_hex_bytes_for_current_line()` - Extract hex bytes for status bar display

**Modified Functions:**
- `compile_asm()` - Added `-r self.report_file` parameter to ACME compilation
- `draw_hex_viewer()` - Complete rewrite with:
  - Byte-by-byte rendering instead of 8-byte chunks
  - Vertical scroll synchronization: `hex_scroll = highlighted_line - screen_pos`
  - Individual byte highlighting based on exact ranges
- `find_next_label_occurrence()` - Added math operator removal: `re.split(r'[+\-*/]', label)[0]`
- `get_word_under_cursor()` - Removed `-` from valid label characters
- Layout fixes - Both ASM editor and HEX dump now use `height - 11`

**Report File Format:**
```
  LINE_NUMBER  OFFSET HEXDATA  CODE
  3649  186f 7998829888...    !word $9879,$9882,$9888
```

**Vertical Sync Algorithm:**
```python
asm_screen_pos = self.cursor_line - self.scroll_offset
target_hex_scroll = highlighted_hex_line - asm_screen_pos
self.hex_scroll_offset = max(0, min(target_hex_scroll, max_scroll))
```

### Fixed Issues

1. **TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'**
   - Added null check before `highlighted_hex_line * 8` calculation
   - Graceful fallback to default header when no mapping exists

2. **NameError: cannot access local variable 'current_address'**
   - Restored `current_address = None` declaration
   - Needed for address incrementing in mapping functions

3. **ASM Editor showing extra line causing footer overlap**
   - Changed from `height - 10` to `height - 11` for ASM editor
   - Both panels now have identical height for proper alignment

4. **Highlighting not vertically aligned**
   - Fixed scroll calculation to account for visual screen position
   - Synchronized scrolling maintains cursor-to-highlight alignment

5. **Label navigation failed with math operations**
   - Strip operators from expressions like `LABEL-1` before search
   - Support for `!word` directive with label operands

### Why ACME Report File?

Manual byte counting failed because:
- Multiple `* = offset` directives change memory address without affecting file offset
- `!source` includes add bytes from external files not visible in main ASM
- Macros (`+macro_name`) expand to multiple instructions

ACME's report file provides:
- Exact line number → file offset mapping
- Pre-calculated byte positions after macro expansion
- Handles all directives and addressing modes correctly
- 100% accurate - no approximation needed

### Migration Notes

- Report file (`.asm.report`) automatically generated during compilation
- No changes to compilation workflow required
- Works with existing ACME assembler installations
- Compatible with both CBM and plain binary formats

---

## [1.0.0] - 2025-01-23 - Initial GitHub Release

### Added

1. **JSON Configuration System**
   - Automatic saving of last opened file
   - Config file `~/.acme_editor_config.json`
   - `load_config()` - load configuration on startup
   - `save_config()` - save after opening file
   - Config is not created on first run, only after opening first file

2. **Command-line Parameter Support**
   - Ability to open file directly on startup
   - Usage: `python c64-acme-ted.py filename.asm`
   - If no parameter is given, loads last file from config
   - If file doesn't exist, error message is shown in log

3. **MIT License**
   - LICENSE file added
   - Project is now officially open source with MIT license

4. **Documentation Updates**
   - README.md updated with configuration info
   - "Running" section expanded with parameter examples
   - "Configuration" section added with config file description
   - "License" section added and duplicates cleaned
   - Bilingual (Czech/English) documentation

### Technical Changes

- `__init__(self, stdscr, initial_file=None)` - new initial_file parameter
- `main(stdscr)` - reads sys.argv[1] as initial_file
- Added imports: `import json`, `import sys`
- `CONFIG_FILE = os.path.expanduser("~/.acme_editor_config.json")`

---

## 2026-01-22 v8 - UTF-8 encoding, Page Up/Down, Save hotkey, Sync fix

### New Features

1. **UTF-8 encoding for files**
   - All files are now loaded and saved with `encoding='utf-8'`
   - Support for Czech characters and other non-ASCII characters in comments
   - Compatible with modern text editors

2. **Page Up/Page Down navigation**
   - `Page Up` - scroll page up
   - `Page Down` - scroll page down
   - Fast navigation through long files

3. **'s' key for saving**
   - Press `s` in NORMAL mode to save file
   - Faster than `:s` in COMMAND mode
   - Logging to LOG window

4. **Complete ASM ↔ HEX synchronization fix**
   - HEX viewer now scrolls synchronously with ASM editor
   - Highlighted line in HEX stays visible when scrolling
   - **Critical fix 1**: `build_mappings()` now correctly processes `* = offset` directive
   - **Critical fix 2**: `!text`/`!tx` directives now count ALL parts (text + bytes)
   - **Critical fix 3**: Indexed instructions with labels (e.g. `LDA L_8000,X`) now correctly counted as 3 bytes instead of 2
   - **Critical fix 4**: ASL/LSR/ROL/ROR without operand now correctly recognized as accumulator mode (1 byte) instead of 2
   - Supports mixed formats: `!tx "text", $XX, "more text"` - counts everything correctly
   - Precise mapping of ASM lines to byte offsets even in files with set start address
   - Perfect tracking of ASM ↔ HEX correspondence even when using `* = 0` or `* = $xxxx`

### Technical Changes

- `open_file()` - added `encoding='utf-8'`
- `save_file()` - added `encoding='utf-8'`
- `handle_normal_mode()` - added `s` key for saving
- `handle_normal_mode()` - added `curses.KEY_PPAGE` and `curses.KEY_NPAGE`
- `draw_hex_viewer()` - changed scroll algorithm to bounds-checking (better stability)
- `build_mappings()` - added processing of `* = offset` directive (CRITICAL FIX 1)
- `build_mappings()` - fixed counting of `!text`/`!tx` directives with mixed format (CRITICAL FIX 2)
- `detect_addressing_mode()` - added support for labels with indexing (,X and ,Y) (CRITICAL FIX 3)
- `build_mappings()` - added special detection of ACC mode for ASL/LSR/ROL/ROR (CRITICAL FIX 4)
- HELP_TEXT updated

## 2026-01-22 v7 - ASM ↔ HEX synchronization fix

### Fixed Issues

1. **Precise synchronization of ASM editor with HEX viewer**
   - Highlighted line in HEX dump now precisely corresponds to cursor in ASM editor
   - `build_mappings()` rewritten for precise byte offset calculation
   - Uses opcode table to determine actual instruction length
   - Precise processing of directives (!byte, !word, !text)

2. **Intelligent ASM code parsing**
   - Correct recognition of instructions vs. directives
   - Using `get_6502_opcode()` for precise length of each instruction
   - Preserving labels during offset calculation
   - Removing comments before parsing

3. **Precise directive processing**
   - `!byte`/`!by` - counts actual number of bytes from hex values
   - `!word`/`!wo` - always 2 bytes per value
   - `!text`/`!tx` - length of text string in quotes
   - Ignores directives that don't generate data (!to, !source, !pseudopc, etc.)

### Technical Changes

- Rewritten function `build_mappings()` (lines 1180-1234)
- Uses `extract_bytes_from_line()` for precise byte counting
- Uses `get_6502_opcode()` for precise instruction length
- Regex parsing of instructions to detect mnemonics
- Removing labels and comments before length calculation

## 2026-01-22 v6 - Bidirectional Instruction ↔ Bytes conversion

### New Features

1. **'c' key - Convert !by bytes back to instructions**
   - Reverse operation to `b` key
   - Converts `!by` directives with opcode back to readable instruction
   - Automatic detection of instruction type from opcode
   - Supports all 6502 instructions and addressing modes

2. **Intelligent processing**
   - Complete reverse 6502 opcode table
   - Automatic detection of instruction length (1-3 bytes)
   - Correct operand formatting according to addressing mode
   - Preserving comments on the line
   - Preserving remaining bytes if there are more

3. **Error reporting**
   - "Not a byte directive" - cursor is not on !by line
   - "Unknown opcode" - unknown opcode
   - "Not enough bytes" - insufficient bytes for instruction

### Important Features

- ✅ **Full bidirectionality**: `b` and `c` are mutually inverse operations
- ✅ **Preserving binary compatibility** - resulting .bin is identical
- ✅ Conversion doesn't change output file after compilation
- ✅ Unbroken code data structure
- ✅ Preserving comments

## 2026-01-22 v5 - Instruction and value to Bytes conversion

### New Features

1. **Automatic conversion of instructions, !word and numbers to !by**
   - `b` key in NORMAL mode
   - Supports:
     - **Instructions**: `JMP $0102` → `!by $4C, $02, $01`
     - **!word directive**: `!word $1234` → `!by $34, $12`
     - **Standalone number**: `$1234` → `!by $34, $12`
     - **All 6502 instructions** with various addressing modes

2. **Complete 6502 processor support**
   - All standard 6502 instructions (LDA, STA, JMP, JSR, ADC, SBC, etc.)
   - All addressing modes:
     - Implied (RTS, NOP)
     - Immediate (#$XX)
     - Zero Page ($XX)
     - Zero Page,X/Y ($XX,X)
     - Absolute ($XXXX)
     - Absolute,X/Y ($XXXX,X)
     - Indirect (($XXXX))
     - Indexed Indirect (($XX,X))
     - Indirect Indexed (($XX),Y)
     - Relative (BNE, BEQ)
     - Accumulator (ASL A)

3. **Intelligent processing**
   - Automatic detection of instruction type and addressing mode
   - Correct opcode from 6502 table
   - Little-endian byte order for 16-bit addresses
   - Preserving comments on the line
   - **Guarantees same binary output** after compilation

4. **Error reporting**
   - "Unknown instruction" - unknown instruction or mode
   - "Invalid operand" - invalid operand format
   - "Not a word, hex value, or instruction" - cannot convert

### Important Features

- ✅ **Preserving binary compatibility** - `w` and `b` are mutually inverse operations
- ✅ Conversion doesn't change output .bin file after compilation
- ✅ Unbroken code data structure
- ✅ Preserving comments

## 2026-01-22 v4 - Bytes to Word conversion

### New Features

1. **Automatic !by -> !word conversion**
   - `w` key in NORMAL mode on line with `!by` or `!byte`
   - Supports multiple formats:
     - **2 bytes on one line**: `!by $01, $02` → `!word $0201`
     - **1 byte on each line**: `!by $01` + `!by $02` → `!word $0201`
     - **More bytes**: `!by $01, $02, $03` → `!word $0201` + `!by $03`

2. **Intelligent processing**
   - Preserves remaining bytes if there are more than 2
   - Automatically joins two consecutive `!by` lines
   - Word is in little-endian format: `$HHLL` (high byte, low byte)
   - Logs result to LOG window

3. **Error reporting**
   - "Not a byte directive" - cursor is not on !by line
   - "No bytes found" - line has no hex values
   - "Need 2 bytes to convert" - insufficient bytes

## 2026-01-22 v3 - Added LOG window

### New Features

1. **Log Window in bottom right corner**
   - Displays last 10 log messages
   - Located under HEX viewer
   - Automatic scroll to newest messages
   - Labeled: `[ LOG ]`

2. **Logging all operations**
   - **Compilation**: "Compiling...", "Compile OK", "Compile FAILED"
   - **Error messages from ACME**: Displays stderr/stdout on error (max 5 lines)
   - **File opening**: "Opened: filename"
   - **Saving**: "Saved: filename"
   - **HEX loading**: "Loaded N bytes to HEX viewer"
   - **Errors**: All errors with prefix "ERR:" (bold)
   - **Info**: Normal messages with prefix "INF:"

3. **Timestamp**
   - Each message has timestamp: `[HH:MM:SS] INF: message`
   - Errors: `[HH:MM:SS] ERR: error message`

4. **Error highlighting**
   - Error messages displayed **bold** (A_BOLD)
   - Easy identification of problems

## 2026-01-22 v2 - INSERT mode fix

### Fixed Issues

1. **Cursor in INSERT mode now visible**
   - Cursor is displayed in INSERT and COMMAND mode
   - Positioned at correct location (line + column)

2. **Movement in INSERT mode**
   - Arrows (↑↓←→) work for text movement
   - ← at beginning of line goes to end of previous line
   - → at end of line goes to beginning of next line

3. **ESC exits INSERT mode**
   - ESC switches back to NORMAL mode
   - Cursor is correctly turned off

4. **Backspace functionality**
   - Backspace at beginning of line joins with previous line
   - Correct cursor position preservation

5. **Tab support**
   - Tab inserts 4 spaces (suitable for ASM code indentation)

## 2026-01-22 v1 - Redesign based on chars_hex_editor.py

### Main Changes

1. **Color scheme** - Simplified to chars_hex_editor.py style
   - Removed all color pairs (green, yellow, cyan, etc.)
   - Uses only:
     - `curses.A_BOLD` for highlighting important text
     - `curses.A_REVERSE` for cursor and status bar
     - Default terminal colors for regular text

2. **Status Bar** - Exactly like chars_hex_editor.py
   - Uses `A_REVERSE` for entire status bar
   - Contains: filename, line number, mode and HELP_TEXT
   - In COMMAND mode displays command line with ":"
   - Help text: `i=INSERT  :q=Quit  :o=Open  :s=Save  F5=Compile  F6=Compile+Hex  j/k=Move`

3. **Syntax Highlighting** - Simple, based on A_BOLD
   - Comments (`;`) - normal text
   - Directives (`!`) - **bold**
   - Labels (`:`) - **bold**
   - Instructions (LDA, STA, etc.) - **first word bold**, rest normal
   - Supports all 6502 instructions

4. **Cursor line**
   - Entire line inverted (`A_REVERSE`)
   - Clearly visible like in chars_hex_editor.py

5. **`:o` Command** - Fixed
   - `:o` without parameter shows prompt "Open file: "
   - `:o filename.asm` opens file directly
   - Prompt uses same style as status bar (A_REVERSE)

6. **Monospace Font**
   - Curses automatically uses monospace font
   - All elements correctly aligned in columns
