# Changelog - C64-ACME-ted

Všechny významné změny v tomto projektu budou zdokumentovány v tomto souboru.

---

## [1.0.0] - 2025-01-23 - První vydání na GitHub

### Přidáno

1. **Systém JSON konfigurace**
   - Automatické ukládání posledního otevřeného souboru
   - Konfigurační soubor `~/.acme_editor_config.json`
   - `load_config()` - načtení konfigurace při startu
   - `save_config()` - uložení po otevření souboru
   - Při prvním spuštění se config nevytváří, až po prvním otevření souboru

2. **Podpora parametru příkazové řádky**
   - Možnost otevřít soubor přímo při spuštění
   - Použití: `python acme_terminal_editor.py filename.asm`
   - Pokud není zadán parametr, načte se poslední soubor z config
   - Pokud soubor neexistuje, zobrazí se chybová zpráva v logu

3. **MIT Licence**
   - Přidán LICENSE soubor
   - Projekt nyní oficiálně open source s MIT licencí

4. **Aktualizace dokumentace**
   - Aktualizace README.md s info o konfiguraci
   - Sekce "Spuštění" rozšířena o příklady s parametrem
   - Přidána sekce "Konfigurace" s popisem config souboru
   - Přidána sekce "Licence" a vyčištěné duplikáty
   - Bilingvální (Čeština/Angličtina) dokumentace

### Technické změny

- `__init__(self, stdscr, initial_file=None)` - nový parametr initial_file
- `main(stdscr)` - načítá sys.argv[1] jako initial_file
- Přidány importy: `import json`, `import sys`
- `CONFIG_FILE = os.path.expanduser("~/.acme_editor_config.json")`

---

## 2026-01-22 v8 - UTF-8 encoding, Page Up/Down, Save hotkey, Sync fix

### Nové funkce:

1. **UTF-8 encoding pro soubory**
   - Všechny soubory se nyní načítají a ukládají s `encoding='utf-8'`
   - Podpora českých znaků a jiných non-ASCII znaků v komentářích
   - Kompatibilní s moderními textovými editory

2. **Page Up/Page Down pohyb**
   - `Page Up` - posun o stránku nahoru
   - `Page Down` - posun o stránku dolů
   - Rychlá navigace dlouhým souborem

3. **Klávesa 's' pro ukládání**
   - Stisknutím `s` v NORMAL módu uložíte soubor
   - Rychlejší než `:s` v COMMAND módu
   - Logování do LOG window

4. **Kompletní oprava synchronizace ASM ↔ HEX**
   - HEX viewer se nyní posouvá synchronně s ASM editorem
   - Zvýrazněný řádek v HEX zůstává viditelný při scrollování
   - **Kritická oprava 1**: `build_mappings()` nyní správně zpracovává direktivu `* = offset`
   - **Kritická oprava 2**: `!text`/`!tx` direktivy nyní počítají VŠECHNY části (texty + byty)
   - **Kritická oprava 3**: Indexované instrukce s labely (např. `LDA L_8000,X`) nyní správně počítány jako 3 byty místo 2
   - **Kritická oprava 4**: ASL/LSR/ROL/ROR bez operandu nyní správně rozpoznány jako accumulator mode (1 byte) místo 2
   - Podporuje mix formátů: `!tx "text", $XX, "další text"` - počítá vše správně
   - Přesné mapování ASM řádků na byte offsety i v souborech s nastavenou startovní adresou
   - Perfektní sledování korespondence ASM ↔ HEX i při použití `* = 0` nebo `* = $xxxx`

### Technické změny:

- `open_file()` - přidán `encoding='utf-8'`
- `save_file()` - přidán `encoding='utf-8'`
- `handle_normal_mode()` - přidána klávesa `s` pro ukládání
- `handle_normal_mode()` - přidáno `curses.KEY_PPAGE` a `curses.KEY_NPAGE`
- `draw_hex_viewer()` - změněn scroll algoritmus na bounds-checking (lepší stabilita)
- `build_mappings()` - přidáno zpracování `* = offset` direktivy (KRITICKÁ OPRAVA 1)
- `build_mappings()` - opraveno počítání `!text`/`!tx` direktiv s mix formátem (KRITICKÁ OPRAVA 2)
- `detect_addressing_mode()` - přidána podpora pro labely s indexací (,X a ,Y) (KRITICKÁ OPRAVA 3)
- `build_mappings()` - přidána speciální detekce ACC módu pro ASL/LSR/ROL/ROR (KRITICKÁ OPRAVA 4)
- HELP_TEXT aktualizován

## 2026-01-22 v7 - Oprava synchronizace ASM ↔ HEX

### Opravené problémy:

1. **Přesná synchronizace ASM editoru s HEX viewerem**
   - Zvýrazněný řádek v HEX dumpu nyní přesně odpovídá kurzoru v ASM editoru
   - `build_mappings()` přepsán pro přesný výpočet byte offsetů
   - Využívá opcode tabulku pro určení skutečné délky instrukcí
   - Přesné zpracování direktiv (!byte, !word, !text)

2. **Inteligentní parsování ASM kódu**
   - Správné rozpoznání instrukcí vs. direktiv
   - Použití `get_6502_opcode()` pro přesnou délku každé instrukce
   - Zachování labelů při výpočtu offsetů
   - Odstranění komentářů před parsováním

3. **Přesné zpracování direktiv**
   - `!byte`/`!by` - počítá skutečný počet bytů z hex hodnot
   - `!word`/`!wo` - vždy 2 byty na každou hodnotu
   - `!text`/`!tx` - délka textového řetězce v uvozovkách
   - Ignoruje direktivy které negenerují data (!to, !source, !pseudopc, atd.)

### Technické změny:

- Přepsána funkce `build_mappings()` (řádky 1180-1234)
- Používá `extract_bytes_from_line()` pro přesné počítání bytů
- Používá `get_6502_opcode()` pro přesnou délku instrukcí
- Regex parsování instrukcí pro detekci mnemonics
- Odstranění labelů a komentářů před výpočtem délky

### Příklad:

```asm
; Před opravou:
L_8000: JMP $0102    ; ASM řádek 10
                     ; HEX zvýraznil řádek 00000030 (CHYBNĚ!)

; Po opravě:
L_8000: JMP $0102    ; ASM řádek 10
                     ; HEX zvýrazní řádek 00000000 (SPRÁVNĚ!)
                     ; JMP zabere 3 byty: $4C $02 $01
```

## 2026-01-22 v6 - Obousměrná konverze Instrukce ↔ Bytes

### Nové funkce:

1. **Klávesa `c` - Konverze !by bytů zpět na instrukce**
   - Reverzní operace k `b` klávese
   - Převádí `!by` direktivy s opcode zpět na čitelnou instrukci
   - Automatická detekce typu instrukce z opcode
   - Podporuje všechny 6502 instrukce a adresovací režimy

2. **Inteligentní zpracování**
   - Kompletní reverzní tabulka opcodů 6502
   - Automatická detekce délky instrukce (1-3 byty)
   - Správné formátování operandů podle adresovacího režimu
   - Zachování komentářů na řádku
   - Zachování zbylých bytů pokud je jich více

3. **Příklady použití**
   ```asm
   ; Příklad 1: JMP instrukce
   !by $4C, $02, $01    ; Kurzor zde, stiskni 'c'
   ↓
   JMP $0102

   ; Příklad 2: JSR instrukce
   !by $20, $A3, $FD    ; Kurzor zde, stiskni 'c'
   ↓
   JSR $FDA3

   ; Příklad 3: LDA immediate
   !by $A9, $FF         ; Kurzor zde, stiskni 'c'
   ↓
   LDA #$FF

   ; Příklad 4: STA absolute
   !by $8D, $20, $D0    ; Kurzor zde, stiskni 'c'
   ↓
   STA $D020

   ; Příklad 5: RTS (bez operandu)
   !by $60              ; Kurzor zde, stiskni 'c'
   ↓
   RTS

   ; Příklad 6: Více bytů - zachová zbylé
   !by $4C, $00, $80, $FF, $AA    ; Kurzor zde, stiskni 'c'
   ↓
   JMP $8000
   !by $FF, $AA
   ```

4. **Chybové hlášení**
   - "Not a byte directive" - kurzor není na !by řádku
   - "Unknown opcode" - neznámý opcode
   - "Not enough bytes" - nedostatek bytů pro instrukci

### Důležité vlastnosti:

- ✅ **Plná obousměrnost**: `b` a `c` jsou vzájemně inverzní operace
- ✅ **Zachování binární kompatibility** - výsledný .bin je identický
- ✅ Konverze nezmění výstupní soubor po kompilaci
- ✅ Nerozbitá datová struktura kódu
- ✅ Zachování komentářů

### Technické změny:

- Nová klávesa `c` v NORMAL módu
- `convert_bytes_to_instruction()` - hlavní konverzní funkce
- `get_instruction_from_opcode()` - reverzní tabulka opcodů
- `format_operand()` - formátování operandů podle režimu
- Aktualizovaný HELP_TEXT: `c=Bytes->Instr`

## 2026-01-22 v5 - Konverze instrukcí a hodnot na Bytes

### Nové funkce:

1. **Automatická konverze instrukcí, !word a čísel na !by**
   - Klávesa `b` v NORMAL módu
   - Podporuje:
     - **Instrukce**: `JMP $0102` → `!by $4C, $02, $01`
     - **!word direktiva**: `!word $1234` → `!by $34, $12`
     - **Samostatné číslo**: `$1234` → `!by $34, $12`
     - **Všechny 6502 instrukce** s různými adresovacími režimy

2. **Kompletní podpora 6502 procesorů**
   - Všechny standardní 6502 instrukce (LDA, STA, JMP, JSR, ADC, SBC, atd.)
   - Všechny adresovací režimy:
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

3. **Inteligentní zpracování**
   - Automatická detekce typu instrukce a adresovacího režimu
   - Správné opcode z tabulky 6502
   - Little-endian pořadí bytů u 16-bit adres
   - Zachování komentářů na řádku
   - **Garantuje stejný binární výstup** po kompilaci

4. **Chybové hlášení**
   - "Unknown instruction" - neznámá instrukce nebo režim
   - "Invalid operand" - chybný formát operandu
   - "Not a word, hex value, or instruction" - nelze převést

### Příklady použití:

```asm
; Příklad 1: JMP instrukce
JMP $0102       ; Kurzor zde, stiskni 'b'
↓
!by $4C, $02, $01

; Příklad 2: JSR instrukce
JSR $FDA3       ; Kurzor zde, stiskni 'b'
↓
!by $20, $A3, $FD

; Příklad 3: LDA immediate
LDA #$FF        ; Kurzor zde, stiskni 'b'
↓
!by $A9, $FF

; Příklad 4: STA absolute
STA $D020       ; Kurzor zde, stiskni 'b'
↓
!by $8D, $20, $D0

; Příklad 5: Word direktiva
!word $1234     ; Kurzor zde, stiskni 'b'
↓
!by $34, $12

; Příklad 6: S komentářem
JMP $8000 ; start  ; Kurzor zde, stiskni 'b'
↓
!by $4C, $00, $80  ; start
```

### Technické změny:

- Nová klávesa `b` v NORMAL módu
- `convert_to_bytes()` - hlavní konverzní funkce
- `get_6502_opcode()` - kompletní tabulka opcodů 6502
- `detect_addressing_mode()` - detekce adresovacího režimu
- `parse_hex_value()` - parsování hex hodnot
- Regex pro extrakci instrukcí, word hodnot a hex čísel
- Aktualizovaný HELP_TEXT: `b=Word->Bytes`

### Důležité vlastnosti:

- ✅ **Zachování binární kompatibility** - `w` a `b` jsou vzájemně inverzní operace
- ✅ Konverze nezmění výstupní .bin soubor po kompilaci
- ✅ Nerozbitá datová struktura kódu
- ✅ Zachování komentářů

## 2026-01-22 v4 - Bytes to Word konverze

### Nové funkce:

1. **Automatická konverze !by -> !word**
   - Klávesa `w` v NORMAL módu na řádku s `!by` nebo `!byte`
   - Podporuje více formátů:
     - **2 byty na jednom řádku**: `!by $01, $02` → `!word $0201`
     - **1 byte na každém řádku**: `!by $01` + `!by $02` → `!word $0201`
     - **Více bytů**: `!by $01, $02, $03` → `!word $0201` + `!by $03`

2. **Inteligentní zpracování**
   - Zachová zbylé byty pokud je jich více než 2
   - Automaticky spojí dva po sobě jdoucí `!by` řádky
   - Word je ve formátu little-endian: `$HHLL` (high byte, low byte)
   - Loguje výsledek operace do LOG window

3. **Chybové hlášení**
   - "Not a byte directive" - kurzor není na !by řádku
   - "No bytes found" - řádek nemá hex hodnoty
   - "Need 2 bytes to convert" - nedostatek bytů

### Příklady použití:

```asm
; Příklad 1: Dva byty na jednom řádku
!by $34, $12     ; Kurzor zde, stiskni 'w'
↓
!word $1234

; Příklad 2: Jeden byte na každém řádku
!by $34          ; Kurzor zde, stiskni 'w'
!by $12
↓
!word $1234

; Příklad 3: Více bytů
!by $34, $12, $AB, $CD     ; Kurzor zde, stiskni 'w'
↓
!word $1234
!by $AB, $CD
```

### Technické změny:

- Nová klávesa `w` v NORMAL módu
- `convert_bytes_to_word()` - hlavní konverzní funkce
- `extract_bytes_from_line()` - extrakce hex hodnot pomocí regex
- Aktualizovaný HELP_TEXT: `w=Bytes->Word`

## 2026-01-22 v3 - Přidán LOG window

### Nové funkce:

1. **Log Window v pravém dolním rohu**
   - Zobrazuje posledních 10 log zpráv
   - Umístěn pod HEX viewerem
   - Automatický scroll na nejnovější zprávy
   - Označení: `[ LOG ]`

2. **Logování všech operací**
   - **Kompilace**: "Compiling...", "Compile OK", "Compile FAILED"
   - **Chybové zprávy z ACME**: Zobrazuje stderr/stdout při chybě (max 5 řádků)
   - **Otevření souboru**: "Opened: filename"
   - **Uložení**: "Saved: filename"
   - **HEX načtení**: "Loaded N bytes to HEX viewer"
   - **Chyby**: Všechny chyby s prefixem "ERR:" (tučně)
   - **Info**: Normální zprávy s prefixem "INF:"

3. **Časové razítko**
   - Každá zpráva má timestamp: `[HH:MM:SS] INF: zpráva`
   - Chyby: `[HH:MM:SS] ERR: chybová zpráva`

4. **Zvýraznění chyb**
   - Chybové zprávy zobrazeny **tučně** (A_BOLD)
   - Snadná identifikace problémů

### Technické změny:

- `add_log(message, error=False)` - nová metoda pro logování
- `draw_log_window()` - vykreslení log okna
- `log_messages` - seznam zpráv (max 50, zobrazuje 10)
- HEX viewer zkrácen o 12 řádků pro místo logu
- Všechny operace (compile, save, open) nyní logují

### Vizuální layout:

```
┌─────────────────┬─────────────────┐
│[ ASM EDITOR ]   │[ HEX DUMP ]     │
│  1  LDA #$FF    │00000000  31...  │
│  2  STA $D020   │00000008  4C...  │
│                 │─────────────────│
│                 │[ LOG ]          │
│                 │[12:34:56] INF:  │
│                 │Compiling...     │
│                 │[12:34:57] INF:  │
│                 │Compile OK       │
└─────────────────┴─────────────────┘
│filename  Ln 1  NORMAL  help...   │
└───────────────────────────────────┘
```

## 2026-01-22 v2 - Oprava INSERT módu

### Opravené problémy:

1. **Kurzor v INSERT módu nyní viditelný**
   - Kurzor se zobrazuje v INSERT a COMMAND módu
   - Umístěn na správné pozici (řádek + sloupec)

2. **Pohyb v INSERT módu**
   - Šipky (↑↓←→) fungují pro pohyb v textu
   - ← na začátku řádku jde na konec předchozího řádku
   - → na konci řádku jde na začátek dalšího řádku

3. **ESC opouští INSERT mód**
   - ESC přepíná zpět do NORMAL módu
   - Kurzor se správně vypne

4. **Backspace funkcionalita**
   - Backspace na začátku řádku spojí s předchozím řádkem
   - Správné zachování pozice kurzoru

5. **Tab podpora**
   - Tab vkládá 4 mezery (vhodné pro odsazení ASM kódu)

### Technické změny:

- `draw_command_line()` - zapíná kurzor v INSERT i COMMAND módu
- `handle_insert_mode()` - přidána podpora šipek, lepší backspace
- `draw_screen()` - umisťuje kurzor na správnou pozici v INSERT módu

## 2026-01-22 v1 - Redesign podle chars_hex_editor.py

### Hlavní změny:

1. **Barevné schéma** - Zjednodušeno na styl chars_hex_editor.py
   - Odstraněny všechny barevné páry (zelená, žlutá, cyan, atd.)
   - Používá se pouze:
     - `curses.A_BOLD` pro zvýraznění důležitého textu
     - `curses.A_REVERSE` pro kurzor a status bar
     - Výchozí terminálové barvy pro běžný text

2. **Status Bar** - Přesně jako chars_hex_editor.py
   - Používá `A_REVERSE` pro celý status bar
   - Obsahuje: název souboru, číslo řádku, mód a HELP_TEXT
   - V COMMAND módu zobrazuje příkazový řádek s ":"
   - Help text: `i=INSERT  :q=Quit  :o=Open  :s=Save  F5=Compile  F6=Compile+Hex  j/k=Move`

3. **Syntax Highlighting** - Jednoduché, založené na A_BOLD
   - Komentáře (`;`) - normální text
   - Direktivy (`!`) - **tučně**
   - Labely (`:`) - **tučně**
   - Instrukce (LDA, STA, atd.) - **první slovo tučně**, zbytek normálně
   - Podporuje všechny 6502 instrukce

4. **Kurzorový řádek**
   - Celý řádek invertovaný (`A_REVERSE`)
   - Jasně viditelný jako v chars_hex_editor.py

5. **`:o` Příkaz** - Opraveno
   - `:o` bez parametru zobrazí prompt "Open file: "
   - `:o filename.asm` otevře soubor přímo
   - Prompt používá stejný styl jako status bar (A_REVERSE)

6. **Monospace Font**
   - Curses automaticky používá monospace font
   - Všechny prvky správně zarovnány ve sloupcích

### Technické detaily:

- **Konstanty**: Přidána `HELP_TEXT` konstanta (stejně jako chars_hex_editor.py)
- **Čistý kód**: Odstraněny nepotřebné barevné páry
- **Konzistence**: Všechny draw funkce používají stejný přístup

### Vizuální porovnání:

```
chars_hex_editor.py:
┌────────────────────────────────┐
│ Line(HEX)   00 01 02 03 04...  │ <- A_BOLD
│ 00000000    31 80 BB 0E...     │ <- cursor line A_REVERSE
│ 00000008    4C 45 80 4C...     │ <- normal text
│────────────────────────────────│
│ file.bin  size=256  cursor=00  │ <- A_REVERSE status
└────────────────────────────────┘

acme_terminal_editor.py (nyní):
┌──────────────────┬──────────────┐
│[ ASM EDITOR ]    │[ HEX DUMP ]  │ <- A_BOLD
│   1  LDA #$FF    │00000000  31..│ <- A_REVERSE cursor
│   2  STA $D020   │00000008  4C..│ <- A_BOLD instrukce
│   3  ;koment     │              │ <- normal text
│──────────────────────────────── │
│file.asm  Ln 1  NORMAL  i=INSERT│ <- A_REVERSE status
└──────────────────────────────────┘
```

### Testování:

```bash
cd "/Users/tomas/Documents/Cloud/ACME editor"
./run_terminal_editor.sh

# Vyzkoušet:
# - :o pro otevření souboru
# - j/k pro pohyb
# - i pro INSERT mód
# - F6 pro kompilaci + HEX
# - Kurzor je jasně viditelný (A_REVERSE)
```
