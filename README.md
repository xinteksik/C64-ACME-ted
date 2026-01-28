# ACME Terminal Editor

Terminálový editor pro ACME Assembler s integrovaným HEX viewerem a pokročilými funkcemi pro vývoj 6502 kódu.

Terminal editor for ACME Assembler with integrated HEX viewer and advanced features for 6502 development.

---
<img width="1305" height="634" alt="acme_editor_1" src="https://github.com/user-attachments/assets/393d5e82-948b-432e-a12a-cff548a74fb5" />

<img width="1305" height="634" alt="acme_editor_2" src="https://github.com/user-attachments/assets/89b278af-4b86-407f-910a-db4164d2b24b" />


## Funkce / Features

### Základní editace / Basic Editing
- **INSERT mode** (i) - editace textu s podporou šipek, Backspace, Delete, Enter / text editing with arrow keys, Backspace, Delete, Enter support
- **NORMAL mode** (ESC) - navigace a příkazy / navigation and commands
- **Vim-style navigace** - j/k (nahoru/dolů), h/→ (vlevo/vpravo), PgUp/PgDn / vim-style navigation
- **Uložení** (s) - uložení souboru / save file
- **Otevření** (:o) - otevření ASM nebo BIN souboru / open ASM or BIN file
- **Ukončení** (:q) - ukončení editoru / quit editor

### Kompilace / Compilation
- **F5** - kompilace ACME assembleru / compile with ACME assembler
- **F6** - kompilace + načtení HEX dumpu / compile + load HEX dump
- Automatická detekce výstupního BIN souboru z \`!to\` direktivy / automatic detection of output BIN file from \`!to\` directive
- Log s chybovými hláškami / log with error messages

### Dual view (ASM + HEX)
- **Rozdělená obrazovka** - ASM editor vlevo, HEX dump vpravo / split screen - ASM editor left, HEX dump right
- **Přesné mapování** - využívá ACME report file pro 100% přesné mapování / uses ACME report file for 100% accurate mapping
  - Funguje i s makry (!source, +makro) / works even with macros (!source, +macro)
  - Automatická detekce CBM vs Plain formátu / automatic detection of CBM vs Plain format
- **Byte-level zvýraznění** - zvýrazní jen byty aktuálního řádku, ne celý 8-byte řádek / highlights only bytes of current line, not entire 8-byte row
- **Vertikální synchronizace** - kurzor a zvýraznění na stejné vizuální pozici / cursor and highlighting at same visual position
- **HEX formát** - 8 bytů na řádek s adresou, hex hodnotami a ASCII / 8 bytes per line with address, hex values and ASCII
- **Dynamická hlavička** - zobrazuje offset bytů (00-07 nebo 08-0F) / dynamic header showing byte offsets (00-07 or 08-0F)
- **Status bar** - zobrazuje hex byty aktuálního řádku (např. [4C BA 92]) / displays hex bytes of current line (e.g. [4C BA 92])

### Konverze / Conversion
- **w** - konverze bytů na word (little-endian) / convert bytes to word (little-endian)
- **b** - konverze instrukcí na byty / convert instructions to bytes
- **c** - konverze bytů zpět na instrukce (disassembly) / convert bytes back to instructions (disassembly)
- **d** - zobrazení hex čísel jako decimální v logu / display hex numbers as decimal in log

### Vyhledávání a navigace / Search and Navigation
- **Ctrl+F** - vlastní textové vyhledávání s předvyplněním / custom text search with pre-fill
- **j** - skok na label/adresu (přemapováno z "l") / jump to label/address (remapped from "l")
  - Detekce labelů v instrukcích (JMP, JSR, BNE, !word atd.) / label detection in instructions (JMP, JSR, BNE, !word etc.)
  - Podpora matematických operací (LABEL-1, LABEL+2) / support for math operations (LABEL-1, LABEL+2)
  - Automatické odstranění operátorů před vyhledáním / automatic removal of operators before search
  - Prioritní hledání definic labelů (LABEL:) / priority search for label definitions (LABEL:)
  - Skok na absolutní adresy pomocí !pseudopc mapování / jump to absolute addresses using !pseudopc mapping
  - Cyklické procházení výskytů / cyclic browsing through occurrences

### Sprite Preview
- **v** - zobrazení 8 bytů jako 8x8 sprite matice / display 8 bytes as 8x8 sprite matrix
- Automatický refresh při pohybu mezi řádky / automatic refresh when moving between lines
- Zobrazení vedle HEX dumpu / displayed next to HEX dump

### Disassembler Mode
- **Shift+D** - zapnutí/vypnutí / toggle on/off
- Vytvoření referenčního binárního souboru (.bin.ref) / create reference binary file (.bin.ref)
- Automatické porovnání při každé kompilaci / automatic comparison on each compilation
- Hlášení rozdílů (adresa + hodnoty) nebo shody / report differences (address + values) or match
- Volitelné smazání referenčního souboru při vypnutí / optional deletion of reference file on exit

### Pokročilé funkce / Advanced Features
- **Syntax highlighting** - direktivy, labely, instrukce, komentáře / directives, labels, instructions, comments
- **!pseudopc podpora** - mapování virtuálních adres na fyzické offsety / mapping virtual addresses to physical offsets
- **Načítání .bin** - automatický převod na \`!by\` direktivy (1 byte/řádek) / loading .bin files - automatic conversion to \`!by\` directives (1 byte/line)
- **6502 opcode tabulka** - přesné mapování instrukcí / precise instruction mapping
- **Log window** - zobrazení posledních 9 zpráv / display of last 9 messages
- **Víceřádkový editor** - až 24 řádků kódu najednou / multi-line editor - up to 24 lines of code at once
- **JSON konfigurace** - automatické ukládání posledního otevřeného souboru / automatic saving of last opened file
- **Parametr příkazové řádky** - možnost otevřít soubor přímo při spuštění / command-line parameter to open file on startup

### Formát a vzhled / Format and Appearance
- Terminálový interface inspirovaný Vi/Vim / terminal interface inspired by Vi/Vim
- Minimalistický design s A_BOLD a A_REVERSE / minimalist design with A_BOLD and A_REVERSE
- Status bar s aktuálním módem, pozicí a nápovědou / status bar with current mode, position and help
- Čísla řádků v ASM editoru / line numbers in ASM editor

---

## Klávesové zkratky / Keyboard Shortcuts

### Módy / Modes
- \`i\` - INSERT mode
- \`ESC\` - NORMAL mode
- \`:\` - COMMAND mode
- \`Ctrl+F\` - SEARCH mode

### Navigace / Navigation
- \`↓\` - dolů / down
- \`k\` / \`↑\` - nahoru / up
- \`h\` / \`←\` - vlevo / left
- \`→\` - vpravo / right
- \`j\` - skok na label/adresu pod kurzorem / jump to label/address under cursor
- \`PgUp\` / \`PgDn\` - stránka nahoru/dolů / page up/down

### Příkazy / Commands
- \`s\` - uložit / save
- \`:o\` - otevřít soubor / open file
- \`:q\` - ukončit / quit
- \`F5\` - kompilovat / compile
- \`F6\` - kompilovat + HEX / compile + HEX

### Nástroje / Tools
- \`w\` - bytes → word
- \`b\` - instruction → bytes
- \`c\` - bytes → instruction
- \`d\` - hex → decimal (zobrazení v logu) / hex → decimal (display in log)
- \`v\` - sprite preview (8x8)
- \`j\` - skok na label/adresu / jump to label/address
- \`Shift+D\` - Disassembler mode

---

## Požadavky / Requirements

- Python 3.x
- \`curses\` knihovna (součást standardní knihovny na Unix/Linux/macOS) / \`curses\` library (part of standard library on Unix/Linux/macOS)
- ACME Assembler (\`acme\` příkaz musí být dostupný v PATH) / ACME Assembler (\`acme\` command must be available in PATH)

### Windows
Na Windows je nutné nainstalovat \`windows-curses\`:
\`\`\`bash
pip install windows-curses
\`\`\`

On Windows, you need to install \`windows-curses\`:
\`\`\`bash
pip install windows-curses
\`\`\`

---

## Spuštění / Running

### Základní spuštění / Basic start
\`\`\`bash
python c64-acme-ted.py
\`\`\`

Po prvním spuštění použijte \`:o\` pro otevření ASM souboru. Editor si zapamatuje poslední otevřený soubor.

After first start, use \`:o\` to open an ASM file. The editor will remember the last opened file.

### Spuštění s parametrem / Start with file parameter
\`\`\`bash
python c64-acme-ted.py mycode.asm
\`\`\`

Otevře přímo zadaný soubor. / Opens the specified file directly.

### Konfigurace / Configuration

Editor automaticky vytváří konfigurační soubor \`~/.acme_editor_config.json\`, který ukládá:
- Cestu k poslednímu otevřenému souboru / path to last opened file

The editor automatically creates a config file \`~/.acme_editor_config.json\` which stores:
- Path to the last opened file

---

## Příklad použití / Usage Example

### Základní workflow / Basic Workflow

1. **Otevření souboru** / **Open file**: \`:o\` → zadejte název souboru / enter filename
2. **Editace** / **Edit**: stiskněte \`i\` pro INSERT mode, editujte kód / press \`i\` for INSERT mode, edit code
3. **Kompilace** / **Compile**: \`F6\` pro kompilaci a zobrazení HEX / \`F6\` to compile and show HEX
4. **Navigace** / **Navigation**: kurzor v ASM automaticky zvýrazní odpovídající byty v HEX / cursor in ASM automatically highlights corresponding bytes in HEX
5. **Uložení** / **Save**: \`s\` pro uložení změn / \`s\` to save changes

### Disassembler mode workflow

1. **Zapnutí** / **Enable**: \`Shift+D\` - vytvoří referenční soubor / creates reference file
2. **Editace a kompilace** / **Edit and compile**: změňte kód a stiskněte \`F6\` / change code and press \`F6\`
3. **Kontrola rozdílů** / **Check differences**: v logu se zobrazí, zda je binárka stejná nebo kde se liší / log shows if binary is identical or where it differs
4. **Vypnutí** / **Disable**: \`Shift+D\` → volba smazání referenčního souboru / option to delete reference file

### Sprite preview workflow

1. **Pozice** / **Position**: najeďte kurzorem na řádek s 8 byty (např. \`!by $FF,$80,$80,...\`) / move cursor to line with 8 bytes (e.g. \`!by $FF,$80,$80,...\`)
2. **Zapnutí** / **Enable**: stiskněte \`v\` / press \`v\`
3. **Procházení** / **Browse**: použijte šipky - sprite se automaticky aktualizuje / use arrows - sprite updates automatically
4. **Vypnutí** / **Disable**: stiskněte \`v\` znovu / press \`v\` again

---

## Příklady kódu / Code Examples

### Použití !pseudopc / Using !pseudopc
\`\`\`asm
!pseudopc $C000 {
    LDA #$00
    STA $D020
loop:
    INC $D020
    JMP loop    ; stiskněte 'l' na JMP pro skok na loop / press 'l' on JMP to jump to loop
}
\`\`\`

### Sprite data / Sprite Data
\`\`\`asm
sprite1:
    !by $FF,$80,$80,$80,$80,$80,$80,$80  ; stiskněte 'v' pro náhled / press 'v' for preview
    !by $FF,$00,$00,$00,$00,$00,$00,$00
    !by $FF,$C0,$C0,$C0,$C0,$C0,$C0,$C0
\`\`\`

### Konverze / Conversion
\`\`\`asm
    LDA #$1234      ; stiskněte 'b' pro konverzi na bytes / press 'b' to convert to bytes
    !by $A9,$34,$12 ; stiskněte 'c' pro konverzi na instrukci / press 'c' to convert to instruction
\`\`\`

---

## Symboly C64 / C64 Symbols

Editor obsahuje soubor \`c64symb.asm\` s definicemi KERNAL/BASIC rutin:

The editor includes \`c64symb.asm\` file with KERNAL/BASIC routine definitions:

\`\`\`asm
!source "c64symb.asm"

; Použití symbolů místo adres / Using symbols instead of addresses
    JSR CBM_CHROUT  ; místo JSR $FFD2 / instead of JSR $FFD2
    JSR CBM_CHRIN   ; místo JSR $FFCF / instead of JSR $FFCF
\`\`\`

---

## Přesné mapování ASM ↔ HEX / Accurate ASM ↔ HEX Mapping

Editor využívá **ACME report file** pro 100% přesné mapování mezi ASM kódem a binárními daty:

The editor uses **ACME report file** for 100% accurate mapping between ASM code and binary data:

### Jak to funguje / How it works

1. **Kompilace s report file** / Compilation with report file
   - ACME generuje `.report` soubor s mapováním / ACME generates `.report` file with mapping
   - Formát: `ŘÁDEK OFFSET HEXDATA KÓD` / Format: `LINE OFFSET HEXDATA CODE`
   - Příklad / Example: `3649  186f 7998829888...    !word $9879,$9882`

2. **Přesné zvýraznění** / Accurate highlighting
   - Zvýrazní se jen byty aktuálního řádku / Only bytes of current line are highlighted
   - Příklad / Example: `JMP $92BA` → zvýrazní `[4C BA 92]` (3 byty)
   - Status bar zobrazuje hex byty / Status bar displays hex bytes: `[4C BA 92]`

3. **Vertikální synchronizace** / Vertical synchronization
   - Kurzor na 10. řádku ASM → zvýraznění na 10. řádku HEX / Cursor on line 10 ASM → highlighting on line 10 HEX
   - Perfektní vizuální korespondence / Perfect visual correspondence

4. **Podpora maker** / Macro support
   - Funguje i s `!source` a `+makro` / Works with `!source` and `+macro`
   - Report file obsahuje rozvinutá makra / Report file contains expanded macros
   - Žádná aproximace, vše přesné / No approximation, everything accurate

### Příklad / Example

```asm
; ASM kód / ASM code
3649  !word $9879,$9882,$9888,$988F,$9895

↓ Kompilace / Compilation

; HEX dump
0000186F  [79 98 82 98 88 98 8F 98 95 98]  <- přesně 10 bytů zvýrazněno
                                               exactly 10 bytes highlighted

; Status bar
[79 98 82 98 88 98 8F 98 95 98]
```

---

## Známé problémy / Known Issues

- Editor je optimalizován pro terminály s minimální velikostí 80x24 / Editor is optimized for terminals with minimum size of 80x24
- Některé terminály mohou mít problémy se znaky pro kreslení rámečků / Some terminals may have issues with box-drawing characters
- Report file se generuje automaticky při F5/F6, pokud chybí, použije se aproximace / Report file is generated automatically on F5/F6, if missing, approximation is used

---

## Licence / License

MIT License - viz soubor LICENSE / see LICENSE file

---

## Autor / Author

Vytvořeno s pomocí Claude (Anthropic) / Created with help of Claude (Anthropic)

---

## Poděkování / Acknowledgments

- ACME Assembler autoři / ACME Assembler authors
- Commodore 64 komunita / Commodore 64 community
