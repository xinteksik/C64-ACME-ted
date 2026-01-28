"""
ACME Assembler Terminal Editor
Terminálový editor pro assemblerový kód s HEX pohledem
Inspirováno chars_hex_editor.py - čistý terminálový styl
"""

import curses
import subprocess
import os
import re
import json
import sys
from pathlib import Path

# Help text zobrazený ve status baru
HELP_TEXT = "[i]nsert [s]ave ^F=[f]ind [l]abel [v]iew [w]ord [b]yte [c]onv [d]ec [D]isasm :o=open :q=quit F5/F6=compile"

# Config file path
CONFIG_FILE = os.path.expanduser("~/.acme_editor_config.json")


class AcmeTerminalEditor:
    def __init__(self, stdscr, initial_file=None):
        self.stdscr = stdscr
        self.current_file = None
        self.initial_file = initial_file
        self.bin_file = None
        self.acme_path = "acme"

        # Editor state
        self.asm_lines = []
        self.hex_data = None
        self.cursor_line = 0
        self.cursor_col = 0
        self.scroll_offset = 0
        self.hex_scroll_offset = 0

        # Mapování
        self.asm_to_bin_map = {}
        self.hex_line_map = {}
        self.pseudopc_map = []  # List of (start_line, end_line, pseudopc_address, bin_offset)

        # Sprite preview
        self.show_sprite_preview = False
        self.sprite_preview_line = None

        # Label search
        self.label_search_text = None
        self.label_search_results = []
        self.label_search_index = 0

        # Search mode
        self.search_buffer = ""

        # Disassembler mode
        self.disasm_mode = False
        self.reference_file = None

        # Mode: 'NORMAL', 'INSERT', 'COMMAND', 'SEARCH'
        self.mode = 'NORMAL'
        self.command_buffer = ""

        # Log zpráv (max 50 řádků, zobrazíme posledních 10)
        self.log_messages = []
        self.log_scroll_offset = 0

        # Inicializace barev
        self.init_colors()

    def init_colors(self):
        """Inicializace barevného schématu - jednoduché jako chars_hex_editor"""
        curses.start_color()
        curses.use_default_colors()
        # Minimální barevné páry - většinou použijeme A_REVERSE a A_BOLD
        curses.init_pair(1, curses.COLOR_WHITE, -1)    # Normální text

    def load_config(self):
        """Načte konfiguraci z JSON souboru"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return config.get('last_file', None)
        except Exception as e:
            self.add_log(f"Error loading config: {e}", error=True)
        return None

    def save_config(self, filepath):
        """Uloží konfiguraci do JSON souboru"""
        try:
            config = {'last_file': filepath}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.add_log(f"Error saving config: {e}", error=True)

    def add_log(self, message, error=False):
        """Přidá zprávu do logu"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = "ERR" if error else "INF"
        log_line = f"[{timestamp}] {prefix}: {message}"
        self.log_messages.append(log_line)
        # Omezit na posledních 50 zpráv
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]
        # Auto-scroll na konec
        if len(self.log_messages) > 10:
            self.log_scroll_offset = len(self.log_messages) - 10

    def draw_status_bar(self):
        """Kreslení status baru - přesně jako chars_hex_editor"""
        height, width = self.stdscr.getmaxyx()
        status_y = height - 1

        try:
            # File info a pozice
            file_name = os.path.basename(self.current_file) if self.current_file else "[No file]"

            # V COMMAND módu zobrazit příkazový řádek
            if self.mode == 'COMMAND':
                status_line = f":{self.command_buffer}"
            elif self.mode == 'SEARCH':
                status_line = f"Search: {self.search_buffer}"
            else:
                # Jinak zobrazit info + help text jako chars_hex_editor
                disasm_indicator = " [DISASM]" if self.disasm_mode else ""

                # Získat hex bytes aktuálního řádku
                hex_bytes_str = self.get_hex_bytes_for_current_line()

                info = f"{file_name}  Ln {self.cursor_line + 1}  {self.mode}{disasm_indicator}  {hex_bytes_str}  {HELP_TEXT}"
                status_line = info

            # Oříznout a doplnit status line na šířku obrazovky
            status_line = (status_line[:width-1]).ljust(width - 1)

            # Celý status bar s A_REVERSE
            self.stdscr.attron(curses.A_REVERSE)
            self.stdscr.move(status_y, 0)
            self.stdscr.clrtoeol()
            self.stdscr.addstr(status_y, 0, status_line)
            self.stdscr.attroff(curses.A_REVERSE)
        except curses.error:
            pass

    def draw_title_bar(self):
        """Kreslení horního baru - jednoduchý styl s A_BOLD"""
        height, width = self.stdscr.getmaxyx()

        try:
            # ASM Editor title
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(0, 2, "[ ASM EDITOR ]")
            self.stdscr.attroff(curses.A_BOLD)

            # HEX Viewer title
            hex_start = width // 2 + 2
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(0, hex_start, "[ HEX DUMP ]")
            self.stdscr.attroff(curses.A_BOLD)
        except curses.error:
            pass

    def draw_asm_editor(self):
        """Kreslení ASM editoru"""
        height, width = self.stdscr.getmaxyx()
        # Výška editoru: stejná jako HEX dump (height - 11) kvůli footer hlavičce HEX dumpu
        editor_height = height - 11
        editor_width = width // 2 - 1

        for i in range(editor_height):
            line_num = self.scroll_offset + i
            y_pos = i + 2  # +2 pro title bar (1) + spacing (1)

            # Zabránit kreslení do oblasti separátoru a logu (separator začíná na height - 8)
            if y_pos >= height - 8:
                break

            try:
                if line_num < len(self.asm_lines):
                    line = self.asm_lines[line_num]

                    # Line number
                    line_num_str = f"{line_num + 1:4d} "
                    self.stdscr.addstr(y_pos, 0, line_num_str)

                    # Line content s syntax highlighting
                    self.draw_asm_line(y_pos, 5, line, editor_width - 5, line_num == self.cursor_line)
                else:
                    # Empty line indicator
                    self.stdscr.addstr(y_pos, 0, "~")
            except curses.error:
                pass

    def draw_asm_line(self, y, x, line, max_width, is_cursor_line):
        """Kreslení jednoho řádku ASM kódu s jednoduchým syntax highlighting"""
        height, width = self.stdscr.getmaxyx()

        # Zkrátit řádek pokud je potřeba
        if len(line) > max_width:
            line = line[:max_width]

        try:
            if is_cursor_line:
                # Kurzorový řádek - celý invertovaný
                self.stdscr.addstr(y, x, line[:max_width].ljust(max_width), curses.A_REVERSE)
            else:
                # Syntax highlighting - jednoduché zvýraznění pomocí A_BOLD
                stripped = line.strip()

                # Komentáře - normální text (bez tučného písma)
                if stripped.startswith(';'):
                    self.stdscr.addstr(y, x, line[:max_width])
                # Direktivy - tučně
                elif stripped.startswith('!'):
                    self.stdscr.addstr(y, x, line[:max_width], curses.A_BOLD)
                # Labely - tučně
                elif ':' in line and stripped.endswith(':'):
                    self.stdscr.addstr(y, x, line[:max_width], curses.A_BOLD)
                else:
                    # Instrukce - zvýraznit první slovo (instrukci) tučně
                    words = line.split()
                    if words and words[0].upper() in [
                        'LDA', 'STA', 'LDX', 'STX', 'LDY', 'STY',
                        'JMP', 'JSR', 'RTS', 'BNE', 'BEQ', 'BCC',
                        'BCS', 'BMI', 'BPL', 'ADC', 'SBC', 'AND',
                        'ORA', 'EOR', 'CMP', 'CPX', 'CPY', 'INC',
                        'DEC', 'INX', 'DEX', 'INY', 'DEY', 'ASL',
                        'LSR', 'ROL', 'ROR', 'NOP', 'BRK', 'SEI',
                        'CLI', 'CLC', 'SEC', 'CLV', 'CLD', 'SED',
                        'TAX', 'TAY', 'TXA', 'TYA', 'TSX', 'TXS',
                        'PHA', 'PLA', 'PHP', 'PLP', 'RTI', 'BIT'
                    ]:
                        # Najít pozici instrukce v řádku
                        instr_start = line.find(words[0])
                        instr_end = instr_start + len(words[0])

                        # Vykreslit před instrukcí (mezery)
                        if instr_start > 0:
                            self.stdscr.addstr(y, x, line[:instr_start])

                        # Vykreslit instrukci tučně
                        self.stdscr.addstr(y, x + instr_start, words[0], curses.A_BOLD)

                        # Vykreslit zbytek řádku normálně
                        rest = line[instr_end:max_width]
                        if rest:
                            self.stdscr.addstr(y, x + instr_end, rest)
                    else:
                        # Jinak normální text
                        self.stdscr.addstr(y, x, line[:max_width])
        except curses.error:
            pass

    def draw_hex_viewer(self):
        """Kreslení HEX vieweru"""
        height, width = self.stdscr.getmaxyx()
        hex_start_x = width // 2 + 1
        hex_width = width - hex_start_x - 1
        # Výška pro HEX data (bez footer hlavičky): height - 10 - 1 = height - 11
        # -10 pro základní layout, -1 pro footer hlavičku
        editor_height = height - 11

        if not self.hex_data:
            try:
                self.stdscr.addstr(3, hex_start_x + 2, "No binary data loaded")
            except curses.error:
                pass
            return

        # Najít highlighted byte range podle cursor pozice
        highlighted_start_offset, highlighted_num_bytes = self.get_hex_range_for_asm_line(self.cursor_line)

        # Pokud máme platné zvýraznění, synchronizovat scroll
        if highlighted_start_offset is not None:
            highlighted_hex_line = highlighted_start_offset // 8

            # Synchronizovat scroll HEX vieweru s ASM editorem
            # Cíl: highlighted HEX řádek by měl být na stejné vizuální pozici jako ASM kurzor

            # Vypočítat pozici kurzoru na obrazovce (0 = první viditelný řádek)
            asm_screen_pos = self.cursor_line - self.scroll_offset

            # Nastavit HEX scroll tak, aby highlighted řádek byl na stejné obrazovkové pozici
            # Příklad: cursor je na 10. viditelném řádku -> highlighted byte by měl být také na 10. viditelném řádku
            target_hex_scroll = highlighted_hex_line - asm_screen_pos

            # Omezit scroll na platný rozsah
            max_hex_lines = (len(self.hex_data) + 7) // 8  # Celkový počet HEX řádků
            max_scroll = max(0, max_hex_lines - editor_height)

            self.hex_scroll_offset = max(0, min(target_hex_scroll, max_scroll))
        else:
            highlighted_hex_line = None

        # Vykreslit hlavičku HEX dumpu podle zvýrazněného řádku
        if highlighted_hex_line is not None:
            highlighted_offset = highlighted_hex_line * 8
            # Zjistit, zda adresa končí na 0 nebo 8
            if (highlighted_offset & 0x0F) < 8:
                # Adresa končí 0-7, zobrazit 00-07
                header = "00 01 02 03 04 05 06 07"
            else:
                # Adresa končí 8-F, zobrazit 08-0F
                header = "08 09 0A 0B 0C 0D 0E 0F"
        else:
            # Defaultní hlavička
            header = "00 01 02 03 04 05 06 07"

        try:
            self.stdscr.addstr(1, hex_start_x + 10, header, curses.A_BOLD)
        except curses.error:
            pass

        # Vypočítat pozici footer hlavičky
        footer_y = height - 9  # Poslední řádek před separátorem bude pro footer

        for i in range(editor_height):
            line_num = self.hex_scroll_offset + i
            y_pos = i + 2

            # Zabránit kreslení do řádku s footer hlavičkou
            if y_pos >= footer_y:
                break

            offset = line_num * 8  # 8 bytů na řádek
            if offset >= len(self.hex_data):
                break

            chunk = self.hex_data[offset:offset + 8]  # Načíst 8 bytů

            try:
                # Adresa
                addr_str = f"{offset:08X}  "
                self.stdscr.addstr(y_pos, hex_start_x, addr_str, curses.A_BOLD)

                # Hex bytes - vykreslit po jednotlivých bytech se zvýrazněním
                hex_x = hex_start_x + 10
                for j, b in enumerate(chunk):
                    byte_offset_in_file = offset + j

                    # Je tento byte zvýrazněný?
                    is_byte_highlighted = False
                    if highlighted_start_offset is not None and highlighted_num_bytes > 0:
                        if highlighted_start_offset <= byte_offset_in_file < highlighted_start_offset + highlighted_num_bytes:
                            is_byte_highlighted = True

                    hex_byte = f"{b:02X} "
                    if hex_x + 3 <= width - 1:
                        if is_byte_highlighted:
                            self.stdscr.addstr(y_pos, hex_x, hex_byte, curses.A_REVERSE)
                        else:
                            self.stdscr.addstr(y_pos, hex_x, hex_byte)
                        hex_x += 3

                # ASCII - vykreslit po jednotlivých znacích se zvýrazněním
                if hex_width > 35:
                    ascii_x = hex_start_x + 35
                    for j, b in enumerate(chunk):
                        byte_offset_in_file = offset + j

                        # Je tento byte zvýrazněný?
                        is_byte_highlighted = False
                        if highlighted_start_offset is not None and highlighted_num_bytes > 0:
                            if highlighted_start_offset <= byte_offset_in_file < highlighted_start_offset + highlighted_num_bytes:
                                is_byte_highlighted = True

                        ascii_char = chr(b) if 32 <= b <= 126 else "."
                        if ascii_x + 1 <= width - 1:
                            if is_byte_highlighted:
                                self.stdscr.addstr(y_pos, ascii_x, ascii_char, curses.A_REVERSE)
                            else:
                                self.stdscr.addstr(y_pos, ascii_x, ascii_char)
                            ascii_x += 1
            except curses.error:
                pass  # Ignorovat chyby při kreslení na okraj

        # Vykreslit footer hlavičku HEX dumpu na posledním řádku před separátorem
        footer_y = height - 9  # Poslední řádek před separátorem (height - 8)
        try:
            self.stdscr.addstr(footer_y, hex_start_x + 10, header, curses.A_BOLD)
        except curses.error:
            pass

        # Vykreslit sprite preview, pokud je aktivní
        if self.show_sprite_preview and self.sprite_preview_line is not None:
            self.draw_sprite_preview(hex_start_x, hex_width, width, height)

    def draw_sprite_preview(self, hex_start_x, hex_width, width, height):
        """Vykreslení sprite preview vedle HEX dumpu"""
        if self.sprite_preview_line >= len(self.asm_lines):
            return

        current_line = self.asm_lines[self.sprite_preview_line].strip()
        bytes_values = self.extract_bytes_from_line(current_line)

        if len(bytes_values) != 8:
            return

        # Převést hodnoty na inty
        try:
            sprite_bytes = [int(b, 16) for b in bytes_values]
        except ValueError:
            return

        # Pozice pro sprite preview (vpravo od ASCII sloupce)
        sprite_x = hex_start_x + 45
        sprite_y = 2

        # Zkontrolovat, zda máme dostatek místa
        if sprite_x + 20 > width - 1 or sprite_y + 10 > height - 2:
            return

        try:
            # Nadpis
            self.stdscr.addstr(sprite_y, sprite_x, "Sprite Preview:", curses.A_BOLD)
            sprite_y += 1

            # Vykreslit 8x8 matici
            for row in range(8):
                byte_val = sprite_bytes[row]
                row_str = ""
                for bit in range(7, -1, -1):  # Od MSB k LSB
                    if byte_val & (1 << bit):
                        row_str += "██"  # Pixel zapnutý
                    else:
                        row_str += "  "  # Pixel vypnutý

                self.stdscr.addstr(sprite_y + row, sprite_x, row_str)

        except curses.error:
            pass  # Ignorovat chyby při kreslení na okraj

    def get_hex_line_for_asm_line(self, asm_line):
        """Najde odpovídající HEX řádek pro ASM řádek"""
        if asm_line in self.asm_to_bin_map:
            byte_offset = self.asm_to_bin_map[asm_line]
            return byte_offset // 8
        return 0

    def get_hex_range_for_asm_line(self, asm_line):
        """Najde byte range (offset, délka) pro ASM řádek"""
        if asm_line not in self.asm_to_bin_map:
            return None, 0

        start_offset = self.asm_to_bin_map[asm_line]

        # Najít následující řádek v mapě pro výpočet délky
        next_offset = None
        for next_line in range(asm_line + 1, len(self.asm_lines)):
            if next_line in self.asm_to_bin_map:
                next_offset = self.asm_to_bin_map[next_line]
                break

        if next_offset is None:
            next_offset = len(self.hex_data)

        num_bytes = next_offset - start_offset

        # Omezit na rozumnou délku (max 16 bytů)
        num_bytes = min(num_bytes, 16)

        return start_offset, num_bytes

    def get_hex_bytes_for_current_line(self):
        """Získá hex bytes pro aktuální řádek ASM kódu"""
        # Zkontrolovat, zda máme načtená hex data
        if not self.hex_data:
            return ""

        if self.cursor_line >= len(self.asm_lines):
            return ""

        # Zjistit, zda je aktuální řádek namapovaný na binární data
        if self.cursor_line not in self.asm_to_bin_map:
            return ""

        line = self.asm_lines[self.cursor_line].strip()
        if not line or line.startswith(';'):
            return ""

        # Získat offset v binárním souboru
        byte_offset = self.asm_to_bin_map[self.cursor_line]

        # Zjistit kolik bytů zabírá tento řádek
        # Zkusit najít další řádek v mapě
        next_offset = None
        for next_line in range(self.cursor_line + 1, len(self.asm_lines)):
            if next_line in self.asm_to_bin_map:
                next_offset = self.asm_to_bin_map[next_line]
                break

        if next_offset is None:
            # Pokud není další řádek, použít délku do konce souboru
            next_offset = len(self.hex_data)

        num_bytes = next_offset - byte_offset

        # Omezit na max 8 bytů pro zobrazení
        num_bytes = min(num_bytes, 8)

        if num_bytes <= 0:
            return ""

        # Získat byty z hex_data
        if byte_offset + num_bytes > len(self.hex_data):
            return ""

        hex_bytes = self.hex_data[byte_offset:byte_offset + num_bytes]

        # Formátovat jako hex string
        hex_str = " ".join([f"{b:02X}" for b in hex_bytes])

        return f"[{hex_str}]"

    def draw_log_window(self):
        """Kreslení log okna pod ASM editorem a HEX viewerem (přes celou šířku)"""
        height, width = self.stdscr.getmaxyx()

        # Log zabere spodních 6 řádků + separator (1 separator + 1 title + 4 log messages + command + status)
        log_height = 4  # Počet řádků pro log zprávy
        log_start_y = height - log_height - 3  # -3 pro title + command + status

        try:
            # Separator line přes celou šířku
            self.stdscr.addstr(log_start_y - 1, 0, "─" * (width - 1))

            # Log title
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(log_start_y, 0, "[ LOG ]")
            self.stdscr.attroff(curses.A_BOLD)

            # Log messages (posledních N)
            display_start = max(0, len(self.log_messages) - log_height)
            for i in range(log_height):
                y_pos = log_start_y + 1 + i
                if y_pos >= height - 2:  # Zastavit před command a status barem
                    break

                msg_idx = display_start + i
                if msg_idx < len(self.log_messages):
                    msg = self.log_messages[msg_idx]
                    # Zvýraznit ERR zprávy
                    if "ERR:" in msg:
                        self.stdscr.attron(curses.A_BOLD)
                        self.stdscr.addstr(y_pos, 0, msg[:width - 1])
                        self.stdscr.attroff(curses.A_BOLD)
                    else:
                        self.stdscr.addstr(y_pos, 0, msg[:width - 1])
        except curses.error:
            pass

    def draw_command_line(self):
        """Kreslení command line - již není potřeba, vše je ve status baru"""
        # Command line je nyní součástí status baru
        # V COMMAND, SEARCH a INSERT módu ukázat kurzor
        try:
            if self.mode in ['COMMAND', 'SEARCH', 'INSERT']:
                curses.curs_set(1)
            else:
                curses.curs_set(0)
        except curses.error:
            pass

    def draw_screen(self):
        """Překreslení celé obrazovky"""
        self.stdscr.clear()
        self.draw_title_bar()
        self.draw_asm_editor()
        self.draw_hex_viewer()
        self.draw_log_window()
        self.draw_command_line()
        self.draw_status_bar()

        # Umístit kurzor na správné místo v INSERT módu
        if self.mode == 'INSERT':
            try:
                # Vypočítat pozici kurzoru na obrazovce
                screen_y = 2 + (self.cursor_line - self.scroll_offset)
                screen_x = 5 + self.cursor_col  # 5 = šířka čísel řádků + mezera
                height, width = self.stdscr.getmaxyx()

                # Zkontrolovat že jsme v platném rozsahu
                if 0 <= screen_y < height - 1 and 0 <= screen_x < width // 2:
                    self.stdscr.move(screen_y, screen_x)
            except curses.error:
                pass

        self.stdscr.refresh()

    def handle_normal_mode(self, key):
        """Zpracování kláves v NORMAL módu"""
        height, width = self.stdscr.getmaxyx()
        editor_height = height - 11

        if key == ord('q'):
            return False  # Quit
        elif key == ord('s'):
            # Uložit soubor
            self.save_file()
        elif key == ord(':'):
            self.mode = 'COMMAND'
            self.command_buffer = ""
        elif key == ord('i'):
            self.mode = 'INSERT'
        elif key == curses.KEY_DOWN:
            if self.cursor_line < len(self.asm_lines) - 1:
                self.cursor_line += 1
                if self.cursor_line >= self.scroll_offset + editor_height:
                    self.scroll_offset += 1
                # Aktualizovat sprite preview na nový řádek
                if self.show_sprite_preview:
                    self.update_sprite_preview_for_current_line()
        elif key == ord('k') or key == curses.KEY_UP:
            if self.cursor_line > 0:
                self.cursor_line -= 1
                if self.cursor_line < self.scroll_offset:
                    self.scroll_offset -= 1
                # Aktualizovat sprite preview na nový řádek
                if self.show_sprite_preview:
                    self.update_sprite_preview_for_current_line()
        elif key == ord('h') or key == curses.KEY_LEFT:
            if self.cursor_col > 0:
                self.cursor_col -= 1
        elif key == curses.KEY_RIGHT:
            if self.cursor_line < len(self.asm_lines):
                if self.cursor_col < len(self.asm_lines[self.cursor_line]):
                    self.cursor_col += 1
        elif key == ord('j'):
            # Hledat label na kterém stojím
            self.find_next_label_occurrence()
        elif key == 6:  # Ctrl+F
            # Otevřít search dialog
            self.mode = 'SEARCH'
            # Předvyplnit slovo pod kurzorem
            word = self.get_word_under_cursor()
            self.search_buffer = word if word else ""
        elif key == curses.KEY_PPAGE:  # Page Up
            self.cursor_line = max(0, self.cursor_line - editor_height)
            self.scroll_offset = max(0, self.scroll_offset - editor_height)
            # Aktualizovat sprite preview na nový řádek
            if self.show_sprite_preview:
                self.update_sprite_preview_for_current_line()
        elif key == curses.KEY_NPAGE:  # Page Down
            self.cursor_line = min(len(self.asm_lines) - 1, self.cursor_line + editor_height)
            if self.cursor_line >= self.scroll_offset + editor_height:
                self.scroll_offset = min(len(self.asm_lines) - 1, self.scroll_offset + editor_height)
            # Aktualizovat sprite preview na nový řádek
            if self.show_sprite_preview:
                self.update_sprite_preview_for_current_line()
        elif key == curses.KEY_F5:
            self.compile_asm()
        elif key == curses.KEY_F6:
            self.compile_and_show_hex()
        elif key == ord('w'):
            # Konverze byte(s) na word
            self.convert_bytes_to_word()
        elif key == ord('b'):
            # Konverze čehokoliv na bytes
            self.convert_to_bytes()
        elif key == ord('c'):
            # Konverze bytes zpět na instrukci
            self.convert_bytes_to_instruction()
        elif key == ord('v'):
            # Toggle sprite preview pro aktuální řádek
            self.toggle_sprite_preview()
        elif key == ord('d'):
            # Převod hexa čísel na decimální
            self.show_hex_as_decimal()
        elif key == ord('D'):
            # Toggle Disassembler mode
            self.toggle_disasm_mode()

        return True

    def handle_insert_mode(self, key):
        """Zpracování kláves v INSERT módu"""
        height, width = self.stdscr.getmaxyx()
        editor_height = height - 11

        if key == 27:  # ESC
            self.mode = 'NORMAL'
            return True

        # Pohyb šipkami v INSERT módu
        elif key == curses.KEY_UP:
            if self.cursor_line > 0:
                self.cursor_line -= 1
                if self.cursor_line < self.scroll_offset:
                    self.scroll_offset -= 1
                # Upravit cursor_col pokud je řádek kratší
                if self.cursor_line < len(self.asm_lines):
                    line_len = len(self.asm_lines[self.cursor_line])
                    if self.cursor_col > line_len:
                        self.cursor_col = line_len
        elif key == curses.KEY_DOWN:
            if self.cursor_line < len(self.asm_lines) - 1:
                self.cursor_line += 1
                if self.cursor_line >= self.scroll_offset + editor_height:
                    self.scroll_offset += 1
                # Upravit cursor_col pokud je řádek kratší
                if self.cursor_line < len(self.asm_lines):
                    line_len = len(self.asm_lines[self.cursor_line])
                    if self.cursor_col > line_len:
                        self.cursor_col = line_len
        elif key == curses.KEY_LEFT:
            if self.cursor_col > 0:
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                # Jít na konec předchozího řádku
                self.cursor_line -= 1
                if self.cursor_line < len(self.asm_lines):
                    self.cursor_col = len(self.asm_lines[self.cursor_line])
        elif key == curses.KEY_RIGHT:
            if self.cursor_line < len(self.asm_lines):
                if self.cursor_col < len(self.asm_lines[self.cursor_line]):
                    self.cursor_col += 1
                elif self.cursor_line < len(self.asm_lines) - 1:
                    # Jít na začátek dalšího řádku
                    self.cursor_line += 1
                    self.cursor_col = 0

        # Backspace
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self.cursor_col > 0:
                line = self.asm_lines[self.cursor_line]
                self.asm_lines[self.cursor_line] = line[:self.cursor_col-1] + line[self.cursor_col:]
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                # Spojit s předchozím řádkem
                prev_line = self.asm_lines[self.cursor_line - 1]
                curr_line = self.asm_lines[self.cursor_line]
                self.cursor_col = len(prev_line)
                self.asm_lines[self.cursor_line - 1] = prev_line + curr_line
                del self.asm_lines[self.cursor_line]
                self.cursor_line -= 1

        # Delete - smazat znak pod kurzorem
        elif key == curses.KEY_DC:
            if self.cursor_line < len(self.asm_lines):
                line = self.asm_lines[self.cursor_line]
                if self.cursor_col < len(line):
                    # Smazat znak pod kurzorem
                    self.asm_lines[self.cursor_line] = line[:self.cursor_col] + line[self.cursor_col+1:]
                elif self.cursor_line < len(self.asm_lines) - 1:
                    # Spojit s následujícím řádkem
                    next_line = self.asm_lines[self.cursor_line + 1]
                    self.asm_lines[self.cursor_line] = line + next_line
                    del self.asm_lines[self.cursor_line + 1]

        # Enter - nový řádek
        elif key == 10 or key == 13:
            line = self.asm_lines[self.cursor_line]
            self.asm_lines.insert(self.cursor_line + 1, line[self.cursor_col:])
            self.asm_lines[self.cursor_line] = line[:self.cursor_col]
            self.cursor_line += 1
            self.cursor_col = 0
            if self.cursor_line >= self.scroll_offset + editor_height:
                self.scroll_offset += 1

        # Tab
        elif key == 9:  # Tab
            if self.cursor_line < len(self.asm_lines):
                line = self.asm_lines[self.cursor_line]
                # Vložit 4 mezery
                self.asm_lines[self.cursor_line] = line[:self.cursor_col] + "    " + line[self.cursor_col:]
                self.cursor_col += 4

        # Printable characters
        elif 32 <= key <= 126:
            if self.cursor_line < len(self.asm_lines):
                line = self.asm_lines[self.cursor_line]
                self.asm_lines[self.cursor_line] = line[:self.cursor_col] + chr(key) + line[self.cursor_col:]
                self.cursor_col += 1

        return True

    def handle_command_mode(self, key):
        """Zpracování kláves v COMMAND módu"""
        if key == 27:  # ESC
            self.mode = 'NORMAL'
            self.command_buffer = ""
        elif key == 10 or key == 13:  # Enter
            self.execute_command(self.command_buffer)
            self.mode = 'NORMAL'
            self.command_buffer = ""
        elif key == curses.KEY_BACKSPACE or key == 127:
            if self.command_buffer:
                self.command_buffer = self.command_buffer[:-1]
        elif 32 <= key <= 126:
            self.command_buffer += chr(key)

        return True

    def handle_search_mode(self, key):
        """Zpracování kláves v SEARCH módu"""
        if key == 27:  # ESC
            self.mode = 'NORMAL'
            self.search_buffer = ""
        elif key == 10 or key == 13:  # Enter
            # Spustit hledání
            if self.search_buffer:
                self.execute_search(self.search_buffer)
            self.mode = 'NORMAL'
        elif key == curses.KEY_BACKSPACE or key == 127:
            if self.search_buffer:
                self.search_buffer = self.search_buffer[:-1]
        elif 32 <= key <= 126:
            self.search_buffer += chr(key)

        return True

    def execute_search(self, search_text):
        """Provést hledání textu"""
        if not search_text:
            self.add_log("Empty search text", error=True)
            return

        # Reset hledání
        self.label_search_text = search_text
        self.label_search_results = []
        self.label_search_index = 0

        # Najít všechny výskyty
        for i, line in enumerate(self.asm_lines):
            if search_text in line:
                self.label_search_results.append(i)

        if not self.label_search_results:
            self.add_log(f"Text '{search_text}' not found", error=True)
            return

        # Najít první výskyt za aktuálním řádkem
        for idx, line_num in enumerate(self.label_search_results):
            if line_num > self.cursor_line:
                self.label_search_index = idx
                break
        else:
            # Žádný výskyt za aktuálním řádkem, začít od začátku
            self.label_search_index = 0

        # Skočit na nalezený řádek
        target_line = self.label_search_results[self.label_search_index]
        self.cursor_line = target_line

        # Aktualizovat scroll
        height, width = self.stdscr.getmaxyx()
        editor_height = height - 11
        if self.cursor_line < self.scroll_offset:
            self.scroll_offset = self.cursor_line
        elif self.cursor_line >= self.scroll_offset + editor_height:
            self.scroll_offset = self.cursor_line - editor_height + 1

        self.add_log(f"Found {len(self.label_search_results)} occurrences of '{search_text}' ({self.label_search_index + 1}/{len(self.label_search_results)})")
        self.search_buffer = ""

    def execute_command(self, cmd):
        """Vykonání příkazu"""
        if cmd == 'q' or cmd == 'quit':
            self.running = False
        elif cmd == 's' or cmd == 'save':
            self.save_file()
        elif cmd.startswith('o ') or cmd.startswith('open '):
            filename = cmd.split(' ', 1)[1]
            self.open_file(filename)
        elif cmd == 'o' or cmd == 'open':
            # Prompt pro název souboru
            filename = self.prompt_input("Open file: ")
            if filename:
                self.open_file(filename)

    def open_file(self, filename):
        """Otevření souboru"""
        try:
            # Pokud je to .bin soubor, načíst jako binární a převést na !by řádky
            if filename.lower().endswith('.bin'):
                with open(filename, 'rb') as f:
                    binary_data = f.read()

                # Převést každý byte na !by řádek
                self.asm_lines = []
                for byte in binary_data:
                    self.asm_lines.append(f"    !by ${byte:02X}")

                self.current_file = filename
                self.add_log(f"Opened binary: {os.path.basename(filename)} ({len(binary_data)} bytes)")
            else:
                # Textový ASM soubor
                with open(filename, 'r', encoding='utf-8') as f:
                    self.asm_lines = f.read().splitlines()
                self.current_file = filename
                self.add_log(f"Opened: {os.path.basename(filename)}")

            self.cursor_line = 0
            self.cursor_col = 0
            self.scroll_offset = 0

            # Vytvořit mapování i když nemáme binární data
            if len(self.asm_lines) > 0:
                self.build_mappings()

            # Uložit do konfigurace
            self.save_config(filename)
        except Exception as e:
            self.add_log(f"Failed to open {filename}: {str(e)}", error=True)

    def save_file(self):
        """Uložení souboru"""
        if not self.current_file:
            self.add_log("No file to save", error=True)
            return

        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.asm_lines))
            self.add_log(f"Saved: {os.path.basename(self.current_file)}")
        except Exception as e:
            self.add_log(f"Save failed: {str(e)}", error=True)

    def prompt_input(self, msg):
        """Prompt pro vstup od uživatele"""
        height, width = self.stdscr.getmaxyx()
        if width <= 2:
            return None
        prompt_msg = (msg[:width - 1]).ljust(width - 1)
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        try:
            self.stdscr.attron(curses.A_REVERSE)
            self.stdscr.move(height - 1, 0)
            self.stdscr.clrtoeol()
            self.stdscr.addstr(height - 1, 0, prompt_msg)
            self.stdscr.attroff(curses.A_REVERSE)
            self.stdscr.refresh()

            curses.echo()
            maxlen = max(1, width - len(msg) - 1)
            self.stdscr.move(height - 1, len(msg))
            s = self.stdscr.getstr(height - 1, len(msg), maxlen)
            s = s.decode('utf-8', 'ignore').strip()
            curses.noecho()
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            return s
        except Exception:
            try:
                curses.noecho()
                curses.curs_set(0)
            except curses.error:
                pass
            return None

    def convert_bytes_to_word(self):
        """Konverze dvou !by/!byte direktiv na !word"""
        if self.cursor_line >= len(self.asm_lines):
            return

        current_line = self.asm_lines[self.cursor_line].strip()

        # Kontrola, zda je to !by nebo !byte direktiva
        if not (current_line.startswith('!by ') or current_line.startswith('!byte ')):
            self.add_log("Not a byte directive - use 'w' on !by or !byte line", error=True)
            return

        # Extrakce bytů z aktuálního řádku
        bytes_current = self.extract_bytes_from_line(current_line)

        if not bytes_current:
            self.add_log("No bytes found on current line", error=True)
            return

        # Případ 1: Dva byty na jednom řádku (!by $01, $02)
        if len(bytes_current) >= 2:
            byte1 = bytes_current[0]
            byte2 = bytes_current[1]
            # Vytvořit word: low byte, high byte -> $HHLL
            word_value = f"${byte2}{byte1}"

            # Nahradit řádek
            remaining_bytes = bytes_current[2:]
            if remaining_bytes:
                # Pokud jsou další byty, ponechat je jako !by
                self.asm_lines[self.cursor_line] = f"    !word {word_value}"
                self.asm_lines.insert(self.cursor_line + 1, f"    !by {', '.join(['$' + b for b in remaining_bytes])}")
                self.add_log(f"Converted 2 bytes to word: {word_value} (kept remaining bytes)")
            else:
                self.asm_lines[self.cursor_line] = f"    !word {word_value}"
                self.add_log(f"Converted 2 bytes to word: {word_value}")
            return

        # Případ 2: Jeden byte na aktuálním řádku, zkus najít další na dalším
        if len(bytes_current) == 1 and self.cursor_line + 1 < len(self.asm_lines):
            next_line = self.asm_lines[self.cursor_line + 1].strip()

            if next_line.startswith('!by ') or next_line.startswith('!byte '):
                bytes_next = self.extract_bytes_from_line(next_line)

                if bytes_next:
                    byte1 = bytes_current[0]
                    byte2 = bytes_next[0]
                    word_value = f"${byte2}{byte1}"

                    # Nahradit oba řádky
                    remaining_bytes = bytes_next[1:]
                    self.asm_lines[self.cursor_line] = f"    !word {word_value}"

                    if remaining_bytes:
                        # Pokud jsou další byty na druhém řádku, ponechat je
                        self.asm_lines[self.cursor_line + 1] = f"    !by {', '.join(['$' + b for b in remaining_bytes])}"
                        self.add_log(f"Converted 2 bytes to word: {word_value} (kept remaining bytes)")
                    else:
                        # Smazat druhý řádek
                        del self.asm_lines[self.cursor_line + 1]
                        self.add_log(f"Converted 2 bytes to word: {word_value}")
                    return

        self.add_log("Need 2 bytes to convert to word", error=True)

    def extract_bytes_from_line(self, line):
        """Extrahuje hex hodnoty bytů z !by nebo !byte řádku"""
        import re
        # Odstranit !by nebo !byte z začátku
        line = re.sub(r'^!by(te)?\s+', '', line)
        # Najít všechny hex hodnoty ($XX)
        hex_values = re.findall(r'\$([0-9A-Fa-f]{2})', line)
        return hex_values

    def get_6502_opcode(self, mnemonic, addressing_mode, operand=None):
        """Vrací opcode a délku instrukce pro 6502 procesor"""
        # Tabulka opcodů 6502: (mnemonic, addressing_mode) -> (opcode, length)
        opcodes = {
            # ADC
            ('ADC', 'IMM'): (0x69, 2), ('ADC', 'ZP'): (0x65, 2), ('ADC', 'ZPX'): (0x75, 2),
            ('ADC', 'ABS'): (0x6D, 3), ('ADC', 'ABSX'): (0x7D, 3), ('ADC', 'ABSY'): (0x79, 3),
            ('ADC', 'INDX'): (0x61, 2), ('ADC', 'INDY'): (0x71, 2),
            # AND
            ('AND', 'IMM'): (0x29, 2), ('AND', 'ZP'): (0x25, 2), ('AND', 'ZPX'): (0x35, 2),
            ('AND', 'ABS'): (0x2D, 3), ('AND', 'ABSX'): (0x3D, 3), ('AND', 'ABSY'): (0x39, 3),
            ('AND', 'INDX'): (0x21, 2), ('AND', 'INDY'): (0x31, 2),
            # ASL
            ('ASL', 'ACC'): (0x0A, 1), ('ASL', 'ZP'): (0x06, 2), ('ASL', 'ZPX'): (0x16, 2),
            ('ASL', 'ABS'): (0x0E, 3), ('ASL', 'ABSX'): (0x1E, 3),
            # Branch instructions
            ('BCC', 'REL'): (0x90, 2), ('BCS', 'REL'): (0xB0, 2), ('BEQ', 'REL'): (0xF0, 2),
            ('BMI', 'REL'): (0x30, 2), ('BNE', 'REL'): (0xD0, 2), ('BPL', 'REL'): (0x10, 2),
            ('BVC', 'REL'): (0x50, 2), ('BVS', 'REL'): (0x70, 2),
            # BIT
            ('BIT', 'ZP'): (0x24, 2), ('BIT', 'ABS'): (0x2C, 3),
            # BRK, CLC, CLD, CLI, CLV, CMP, CPX, CPY
            ('BRK', 'IMP'): (0x00, 1),
            ('CLC', 'IMP'): (0x18, 1), ('CLD', 'IMP'): (0xD8, 1), ('CLI', 'IMP'): (0x58, 1),
            ('CLV', 'IMP'): (0xB8, 1),
            ('CMP', 'IMM'): (0xC9, 2), ('CMP', 'ZP'): (0xC5, 2), ('CMP', 'ZPX'): (0xD5, 2),
            ('CMP', 'ABS'): (0xCD, 3), ('CMP', 'ABSX'): (0xDD, 3), ('CMP', 'ABSY'): (0xD9, 3),
            ('CMP', 'INDX'): (0xC1, 2), ('CMP', 'INDY'): (0xD1, 2),
            ('CPX', 'IMM'): (0xE0, 2), ('CPX', 'ZP'): (0xE4, 2), ('CPX', 'ABS'): (0xEC, 3),
            ('CPY', 'IMM'): (0xC0, 2), ('CPY', 'ZP'): (0xC4, 2), ('CPY', 'ABS'): (0xCC, 3),
            # DEC, DEX, DEY
            ('DEC', 'ZP'): (0xC6, 2), ('DEC', 'ZPX'): (0xD6, 2), ('DEC', 'ABS'): (0xCE, 3),
            ('DEC', 'ABSX'): (0xDE, 3),
            ('DEX', 'IMP'): (0xCA, 1), ('DEY', 'IMP'): (0x88, 1),
            # EOR
            ('EOR', 'IMM'): (0x49, 2), ('EOR', 'ZP'): (0x45, 2), ('EOR', 'ZPX'): (0x55, 2),
            ('EOR', 'ABS'): (0x4D, 3), ('EOR', 'ABSX'): (0x5D, 3), ('EOR', 'ABSY'): (0x59, 3),
            ('EOR', 'INDX'): (0x41, 2), ('EOR', 'INDY'): (0x51, 2),
            # INC, INX, INY
            ('INC', 'ZP'): (0xE6, 2), ('INC', 'ZPX'): (0xF6, 2), ('INC', 'ABS'): (0xEE, 3),
            ('INC', 'ABSX'): (0xFE, 3),
            ('INX', 'IMP'): (0xE8, 1), ('INY', 'IMP'): (0xC8, 1),
            # JMP, JSR
            ('JMP', 'ABS'): (0x4C, 3), ('JMP', 'IND'): (0x6C, 3),
            ('JSR', 'ABS'): (0x20, 3),
            # LDA, LDX, LDY
            ('LDA', 'IMM'): (0xA9, 2), ('LDA', 'ZP'): (0xA5, 2), ('LDA', 'ZPX'): (0xB5, 2),
            ('LDA', 'ABS'): (0xAD, 3), ('LDA', 'ABSX'): (0xBD, 3), ('LDA', 'ABSY'): (0xB9, 3),
            ('LDA', 'INDX'): (0xA1, 2), ('LDA', 'INDY'): (0xB1, 2),
            ('LDX', 'IMM'): (0xA2, 2), ('LDX', 'ZP'): (0xA6, 2), ('LDX', 'ZPY'): (0xB6, 2),
            ('LDX', 'ABS'): (0xAE, 3), ('LDX', 'ABSY'): (0xBE, 3),
            ('LDY', 'IMM'): (0xA0, 2), ('LDY', 'ZP'): (0xA4, 2), ('LDY', 'ZPX'): (0xB4, 2),
            ('LDY', 'ABS'): (0xAC, 3), ('LDY', 'ABSX'): (0xBC, 3),
            # LSR
            ('LSR', 'ACC'): (0x4A, 1), ('LSR', 'ZP'): (0x46, 2), ('LSR', 'ZPX'): (0x56, 2),
            ('LSR', 'ABS'): (0x4E, 3), ('LSR', 'ABSX'): (0x5E, 3),
            # NOP
            ('NOP', 'IMP'): (0xEA, 1),
            # ORA
            ('ORA', 'IMM'): (0x09, 2), ('ORA', 'ZP'): (0x05, 2), ('ORA', 'ZPX'): (0x15, 2),
            ('ORA', 'ABS'): (0x0D, 3), ('ORA', 'ABSX'): (0x1D, 3), ('ORA', 'ABSY'): (0x19, 3),
            ('ORA', 'INDX'): (0x01, 2), ('ORA', 'INDY'): (0x11, 2),
            # PHA, PHP, PLA, PLP
            ('PHA', 'IMP'): (0x48, 1), ('PHP', 'IMP'): (0x08, 1),
            ('PLA', 'IMP'): (0x68, 1), ('PLP', 'IMP'): (0x28, 1),
            # ROL, ROR
            ('ROL', 'ACC'): (0x2A, 1), ('ROL', 'ZP'): (0x26, 2), ('ROL', 'ZPX'): (0x36, 2),
            ('ROL', 'ABS'): (0x2E, 3), ('ROL', 'ABSX'): (0x3E, 3),
            ('ROR', 'ACC'): (0x6A, 1), ('ROR', 'ZP'): (0x66, 2), ('ROR', 'ZPX'): (0x76, 2),
            ('ROR', 'ABS'): (0x6E, 3), ('ROR', 'ABSX'): (0x7E, 3),
            # RTI, RTS
            ('RTI', 'IMP'): (0x40, 1), ('RTS', 'IMP'): (0x60, 1),
            # SBC
            ('SBC', 'IMM'): (0xE9, 2), ('SBC', 'ZP'): (0xE5, 2), ('SBC', 'ZPX'): (0xF5, 2),
            ('SBC', 'ABS'): (0xED, 3), ('SBC', 'ABSX'): (0xFD, 3), ('SBC', 'ABSY'): (0xF9, 3),
            ('SBC', 'INDX'): (0xE1, 2), ('SBC', 'INDY'): (0xF1, 2),
            # SEC, SED, SEI
            ('SEC', 'IMP'): (0x38, 1), ('SED', 'IMP'): (0xF8, 1), ('SEI', 'IMP'): (0x78, 1),
            # STA, STX, STY
            ('STA', 'ZP'): (0x85, 2), ('STA', 'ZPX'): (0x95, 2), ('STA', 'ABS'): (0x8D, 3),
            ('STA', 'ABSX'): (0x9D, 3), ('STA', 'ABSY'): (0x99, 3),
            ('STA', 'INDX'): (0x81, 2), ('STA', 'INDY'): (0x91, 2),
            ('STX', 'ZP'): (0x86, 2), ('STX', 'ZPY'): (0x96, 2), ('STX', 'ABS'): (0x8E, 3),
            ('STY', 'ZP'): (0x84, 2), ('STY', 'ZPX'): (0x94, 2), ('STY', 'ABS'): (0x8C, 3),
            # TAX, TAY, TSX, TXA, TXS, TYA
            ('TAX', 'IMP'): (0xAA, 1), ('TAY', 'IMP'): (0xA8, 1), ('TSX', 'IMP'): (0xBA, 1),
            ('TXA', 'IMP'): (0x8A, 1), ('TXS', 'IMP'): (0x9A, 1), ('TYA', 'IMP'): (0x98, 1),
        }

        key = (mnemonic.upper(), addressing_mode)
        return opcodes.get(key, (None, None))

    def detect_addressing_mode(self, operand_str):
        """Detekuje adresovací režim z operandu"""
        if not operand_str:
            return 'IMP', None  # Implied

        operand_str = operand_str.strip()

        # Immediate: #$XX
        if operand_str.startswith('#'):
            return 'IMM', operand_str[1:].strip()

        # Indirect: ($XXXX)
        if operand_str.startswith('(') and operand_str.endswith(')'):
            return 'IND', operand_str[1:-1].strip()

        # Indexed Indirect: ($XX,X)
        if operand_str.startswith('(') and ',X)' in operand_str.upper():
            addr = operand_str[1:operand_str.upper().index(',X)')].strip()
            return 'INDX', addr

        # Indirect Indexed: ($XX),Y
        if operand_str.startswith('(') and '),Y' in operand_str.upper():
            addr = operand_str[1:operand_str.index(')')].strip()
            return 'INDY', addr

        # Absolute,X or ZP,X: $XXXX,X or $XX,X or LABEL,X
        if ',X' in operand_str.upper():
            addr = operand_str[:operand_str.upper().index(',X')].strip()
            if addr.startswith('$'):
                hex_val = addr[1:]
                if len(hex_val) <= 2:
                    return 'ZPX', addr
                else:
                    return 'ABSX', addr
            else:
                # It's a label - assume absolute addressing
                return 'ABSX', addr

        # Absolute,Y or ZP,Y: $XXXX,Y or $XX,Y or LABEL,Y
        if ',Y' in operand_str.upper():
            addr = operand_str[:operand_str.upper().index(',Y')].strip()
            if addr.startswith('$'):
                hex_val = addr[1:]
                if len(hex_val) <= 2:
                    return 'ZPY', addr
                else:
                    return 'ABSY', addr
            else:
                # It's a label - assume absolute addressing
                return 'ABSY', addr

        # Accumulator: A
        if operand_str.upper() == 'A':
            return 'ACC', None

        # Absolute or Zero Page: $XXXX or $XX
        if operand_str.startswith('$'):
            hex_val = operand_str[1:]
            if len(hex_val) <= 2:
                return 'ZP', operand_str
            else:
                return 'ABS', operand_str

        # Label without $ - could be ABS (for JMP/JSR) or REL (for branches)
        # We'll return ABS by default since most labels are absolute addresses
        # Branch instructions will still work because they have REL mode in the opcode table
        return 'ABS', operand_str

    def parse_hex_value(self, hex_str):
        """Parsuje hex hodnotu ze stringu ($XXXX nebo XXXX)"""
        if hex_str.startswith('$'):
            hex_str = hex_str[1:]
        return int(hex_str, 16)

    def convert_to_bytes(self):
        """Konverze !word, čísla nebo instrukce na !byte direktivu"""
        if self.cursor_line >= len(self.asm_lines):
            return

        current_line = self.asm_lines[self.cursor_line].strip()
        import re

        # 1. Kontrola, zda je to !word direktiva
        if current_line.startswith('!word ') or current_line.startswith('!wo '):
            word_match = re.search(r'\$([0-9A-Fa-f]{4})', current_line)
            if word_match:
                word_str = word_match.group(1)
                high_byte = word_str[:2]
                low_byte = word_str[2:]
                self.asm_lines[self.cursor_line] = f"    !by ${low_byte}, ${high_byte}"
                self.add_log(f"Converted word ${word_str} to bytes: ${low_byte}, ${high_byte}")
                return
            else:
                self.add_log("No valid word value found", error=True)
                return

        # 2. Kontrola, zda je to samostatné číslo
        hex_match = re.search(r'^\s*\$([0-9A-Fa-f]{3,4})\s*$', current_line)
        if hex_match:
            hex_str = hex_match.group(1)
            if len(hex_str) == 4:
                high_byte = hex_str[:2]
                low_byte = hex_str[2:]
                self.asm_lines[self.cursor_line] = f"    !by ${low_byte}, ${high_byte}"
                self.add_log(f"Converted ${hex_str} to bytes: ${low_byte}, ${high_byte}")
                return
            elif len(hex_str) == 3:
                full_hex = "0" + hex_str
                high_byte = full_hex[:2]
                low_byte = full_hex[2:]
                self.asm_lines[self.cursor_line] = f"    !by ${low_byte}, ${high_byte}"
                self.add_log(f"Converted ${hex_str} to bytes: ${low_byte}, ${high_byte}")
                return

        # 3. Kontrola, zda je to instrukce (mnemonic + operand)
        # Pattern: mnemonic [operand] [;comment]
        instr_match = re.match(r'^\s*([A-Z]{3})\s*(.*)$', current_line, re.IGNORECASE)
        if instr_match:
            mnemonic = instr_match.group(1).upper()
            rest = instr_match.group(2).strip()

            # Oddělit operand a komentář
            operand = rest.split(';')[0].strip() if rest else ""
            comment = ';' + rest.split(';')[1] if ';' in rest else ""

            # Detekovat adresovací režim
            addr_mode, addr_value = self.detect_addressing_mode(operand)

            # Získat opcode
            opcode, length = self.get_6502_opcode(mnemonic, addr_mode, addr_value)

            if opcode is None:
                self.add_log(f"Unknown instruction: {mnemonic} {addr_mode}", error=True)
                return

            # Sestavit byty
            bytes_list = [f"${opcode:02X}"]

            if length == 2:
                # 1 byte operand
                if addr_value:
                    try:
                        val = self.parse_hex_value(addr_value)
                        bytes_list.append(f"${val:02X}")
                    except:
                        self.add_log(f"Invalid operand: {addr_value}", error=True)
                        return
            elif length == 3:
                # 2 byte operand (little-endian)
                if addr_value:
                    try:
                        val = self.parse_hex_value(addr_value)
                        low_byte = val & 0xFF
                        high_byte = (val >> 8) & 0xFF
                        bytes_list.append(f"${low_byte:02X}")
                        bytes_list.append(f"${high_byte:02X}")
                    except:
                        self.add_log(f"Invalid operand: {addr_value}", error=True)
                        return

            # Vytvořit nový řádek s !by
            new_line = f"    !by {', '.join(bytes_list)}"
            if comment:
                new_line += f"  {comment}"

            self.asm_lines[self.cursor_line] = new_line
            self.add_log(f"Converted {mnemonic} to bytes: {', '.join(bytes_list)}")
            return

        # Pokud nic nepasuje
        self.add_log("Not a word, hex value, or instruction - use 'b' on !word, $XXXX, or instruction", error=True)

    def get_instruction_from_opcode(self, opcode):
        """Vrací mnemonic a addressing mode pro daný opcode (reverzní lookup)"""
        # Reverzní tabulka: opcode -> (mnemonic, addressing_mode, length)
        reverse_opcodes = {
            # ADC
            0x69: ('ADC', 'IMM', 2), 0x65: ('ADC', 'ZP', 2), 0x75: ('ADC', 'ZPX', 2),
            0x6D: ('ADC', 'ABS', 3), 0x7D: ('ADC', 'ABSX', 3), 0x79: ('ADC', 'ABSY', 3),
            0x61: ('ADC', 'INDX', 2), 0x71: ('ADC', 'INDY', 2),
            # AND
            0x29: ('AND', 'IMM', 2), 0x25: ('AND', 'ZP', 2), 0x35: ('AND', 'ZPX', 2),
            0x2D: ('AND', 'ABS', 3), 0x3D: ('AND', 'ABSX', 3), 0x39: ('AND', 'ABSY', 3),
            0x21: ('AND', 'INDX', 2), 0x31: ('AND', 'INDY', 2),
            # ASL
            0x0A: ('ASL', 'ACC', 1), 0x06: ('ASL', 'ZP', 2), 0x16: ('ASL', 'ZPX', 2),
            0x0E: ('ASL', 'ABS', 3), 0x1E: ('ASL', 'ABSX', 3),
            # Branches
            0x90: ('BCC', 'REL', 2), 0xB0: ('BCS', 'REL', 2), 0xF0: ('BEQ', 'REL', 2),
            0x30: ('BMI', 'REL', 2), 0xD0: ('BNE', 'REL', 2), 0x10: ('BPL', 'REL', 2),
            0x50: ('BVC', 'REL', 2), 0x70: ('BVS', 'REL', 2),
            # BIT
            0x24: ('BIT', 'ZP', 2), 0x2C: ('BIT', 'ABS', 3),
            # BRK, CLC, CLD, CLI, CLV
            0x00: ('BRK', 'IMP', 1),
            0x18: ('CLC', 'IMP', 1), 0xD8: ('CLD', 'IMP', 1), 0x58: ('CLI', 'IMP', 1),
            0xB8: ('CLV', 'IMP', 1),
            # CMP, CPX, CPY
            0xC9: ('CMP', 'IMM', 2), 0xC5: ('CMP', 'ZP', 2), 0xD5: ('CMP', 'ZPX', 2),
            0xCD: ('CMP', 'ABS', 3), 0xDD: ('CMP', 'ABSX', 3), 0xD9: ('CMP', 'ABSY', 3),
            0xC1: ('CMP', 'INDX', 2), 0xD1: ('CMP', 'INDY', 2),
            0xE0: ('CPX', 'IMM', 2), 0xE4: ('CPX', 'ZP', 2), 0xEC: ('CPX', 'ABS', 3),
            0xC0: ('CPY', 'IMM', 2), 0xC4: ('CPY', 'ZP', 2), 0xCC: ('CPY', 'ABS', 3),
            # DEC, DEX, DEY
            0xC6: ('DEC', 'ZP', 2), 0xD6: ('DEC', 'ZPX', 2), 0xCE: ('DEC', 'ABS', 3),
            0xDE: ('DEC', 'ABSX', 3),
            0xCA: ('DEX', 'IMP', 1), 0x88: ('DEY', 'IMP', 1),
            # EOR
            0x49: ('EOR', 'IMM', 2), 0x45: ('EOR', 'ZP', 2), 0x55: ('EOR', 'ZPX', 2),
            0x4D: ('EOR', 'ABS', 3), 0x5D: ('EOR', 'ABSX', 3), 0x59: ('EOR', 'ABSY', 3),
            0x41: ('EOR', 'INDX', 2), 0x51: ('EOR', 'INDY', 2),
            # INC, INX, INY
            0xE6: ('INC', 'ZP', 2), 0xF6: ('INC', 'ZPX', 2), 0xEE: ('INC', 'ABS', 3),
            0xFE: ('INC', 'ABSX', 3),
            0xE8: ('INX', 'IMP', 1), 0xC8: ('INY', 'IMP', 1),
            # JMP, JSR
            0x4C: ('JMP', 'ABS', 3), 0x6C: ('JMP', 'IND', 3),
            0x20: ('JSR', 'ABS', 3),
            # LDA, LDX, LDY
            0xA9: ('LDA', 'IMM', 2), 0xA5: ('LDA', 'ZP', 2), 0xB5: ('LDA', 'ZPX', 2),
            0xAD: ('LDA', 'ABS', 3), 0xBD: ('LDA', 'ABSX', 3), 0xB9: ('LDA', 'ABSY', 3),
            0xA1: ('LDA', 'INDX', 2), 0xB1: ('LDA', 'INDY', 2),
            0xA2: ('LDX', 'IMM', 2), 0xA6: ('LDX', 'ZP', 2), 0xB6: ('LDX', 'ZPY', 2),
            0xAE: ('LDX', 'ABS', 3), 0xBE: ('LDX', 'ABSY', 3),
            0xA0: ('LDY', 'IMM', 2), 0xA4: ('LDY', 'ZP', 2), 0xB4: ('LDY', 'ZPX', 2),
            0xAC: ('LDY', 'ABS', 3), 0xBC: ('LDY', 'ABSX', 3),
            # LSR
            0x4A: ('LSR', 'ACC', 1), 0x46: ('LSR', 'ZP', 2), 0x56: ('LSR', 'ZPX', 2),
            0x4E: ('LSR', 'ABS', 3), 0x5E: ('LSR', 'ABSX', 3),
            # NOP
            0xEA: ('NOP', 'IMP', 1),
            # ORA
            0x09: ('ORA', 'IMM', 2), 0x05: ('ORA', 'ZP', 2), 0x15: ('ORA', 'ZPX', 2),
            0x0D: ('ORA', 'ABS', 3), 0x1D: ('ORA', 'ABSX', 3), 0x19: ('ORA', 'ABSY', 3),
            0x01: ('ORA', 'INDX', 2), 0x11: ('ORA', 'INDY', 2),
            # PHA, PHP, PLA, PLP
            0x48: ('PHA', 'IMP', 1), 0x08: ('PHP', 'IMP', 1),
            0x68: ('PLA', 'IMP', 1), 0x28: ('PLP', 'IMP', 1),
            # ROL, ROR
            0x2A: ('ROL', 'ACC', 1), 0x26: ('ROL', 'ZP', 2), 0x36: ('ROL', 'ZPX', 2),
            0x2E: ('ROL', 'ABS', 3), 0x3E: ('ROL', 'ABSX', 3),
            0x6A: ('ROR', 'ACC', 1), 0x66: ('ROR', 'ZP', 2), 0x76: ('ROR', 'ZPX', 2),
            0x6E: ('ROR', 'ABS', 3), 0x7E: ('ROR', 'ABSX', 3),
            # RTI, RTS
            0x40: ('RTI', 'IMP', 1), 0x60: ('RTS', 'IMP', 1),
            # SBC
            0xE9: ('SBC', 'IMM', 2), 0xE5: ('SBC', 'ZP', 2), 0xF5: ('SBC', 'ZPX', 2),
            0xED: ('SBC', 'ABS', 3), 0xFD: ('SBC', 'ABSX', 3), 0xF9: ('SBC', 'ABSY', 3),
            0xE1: ('SBC', 'INDX', 2), 0xF1: ('SBC', 'INDY', 2),
            # SEC, SED, SEI
            0x38: ('SEC', 'IMP', 1), 0xF8: ('SED', 'IMP', 1), 0x78: ('SEI', 'IMP', 1),
            # STA, STX, STY
            0x85: ('STA', 'ZP', 2), 0x95: ('STA', 'ZPX', 2), 0x8D: ('STA', 'ABS', 3),
            0x9D: ('STA', 'ABSX', 3), 0x99: ('STA', 'ABSY', 3),
            0x81: ('STA', 'INDX', 2), 0x91: ('STA', 'INDY', 2),
            0x86: ('STX', 'ZP', 2), 0x96: ('STX', 'ZPY', 2), 0x8E: ('STX', 'ABS', 3),
            0x84: ('STY', 'ZP', 2), 0x94: ('STY', 'ZPX', 2), 0x8C: ('STY', 'ABS', 3),
            # TAX, TAY, TSX, TXA, TXS, TYA
            0xAA: ('TAX', 'IMP', 1), 0xA8: ('TAY', 'IMP', 1), 0xBA: ('TSX', 'IMP', 1),
            0x8A: ('TXA', 'IMP', 1), 0x9A: ('TXS', 'IMP', 1), 0x98: ('TYA', 'IMP', 1),
        }
        return reverse_opcodes.get(opcode, (None, None, None))

    def format_operand(self, addr_mode, operand_bytes):
        """Formátuje operand podle adresovacího režimu"""
        if addr_mode == 'IMP':
            return ""
        elif addr_mode == 'ACC':
            return "A"
        elif addr_mode == 'IMM':
            return f"#${operand_bytes[0]:02X}"
        elif addr_mode == 'ZP':
            return f"${operand_bytes[0]:02X}"
        elif addr_mode == 'ZPX':
            return f"${operand_bytes[0]:02X},X"
        elif addr_mode == 'ZPY':
            return f"${operand_bytes[0]:02X},Y"
        elif addr_mode == 'ABS':
            addr = operand_bytes[0] | (operand_bytes[1] << 8)
            return f"${addr:04X}"
        elif addr_mode == 'ABSX':
            addr = operand_bytes[0] | (operand_bytes[1] << 8)
            return f"${addr:04X},X"
        elif addr_mode == 'ABSY':
            addr = operand_bytes[0] | (operand_bytes[1] << 8)
            return f"${addr:04X},Y"
        elif addr_mode == 'IND':
            addr = operand_bytes[0] | (operand_bytes[1] << 8)
            return f"(${addr:04X})"
        elif addr_mode == 'INDX':
            return f"(${operand_bytes[0]:02X},X)"
        elif addr_mode == 'INDY':
            return f"(${operand_bytes[0]:02X}),Y"
        elif addr_mode == 'REL':
            return f"${operand_bytes[0]:02X}"  # Relative addressing
        return ""

    def convert_bytes_to_instruction(self):
        """Konverze !by direktiv zpět na instrukci"""
        if self.cursor_line >= len(self.asm_lines):
            return

        current_line = self.asm_lines[self.cursor_line].strip()
        import re

        # Kontrola, zda je to !by nebo !byte direktiva
        if not (current_line.startswith('!by ') or current_line.startswith('!byte ')):
            self.add_log("Not a byte directive - use 'c' on !by line", error=True)
            return

        # Extrahovat byty
        bytes_values = self.extract_bytes_from_line(current_line)

        if not bytes_values:
            self.add_log("No bytes found on line", error=True)
            return

        # Získat komentář pokud existuje
        comment = ""
        if ';' in current_line:
            comment = ';' + current_line.split(';', 1)[1]

        # Parsovat první byte jako opcode
        try:
            opcode = int(bytes_values[0], 16)
        except ValueError:
            self.add_log(f"Invalid opcode: ${bytes_values[0]}", error=True)
            return

        # Najít instrukci pro tento opcode
        mnemonic, addr_mode, length = self.get_instruction_from_opcode(opcode)

        if mnemonic is None:
            self.add_log(f"Unknown opcode: ${opcode:02X}", error=True)
            return

        # Zkontrolovat, zda máme dostatek bytů
        if len(bytes_values) < length:
            self.add_log(f"Not enough bytes for {mnemonic} (need {length}, have {len(bytes_values)})", error=True)
            return

        # Sestavit operand
        operand_bytes = []
        if length > 1:
            for i in range(1, length):
                operand_bytes.append(int(bytes_values[i], 16))

        operand_str = self.format_operand(addr_mode, operand_bytes)

        # Vytvořit instrukci
        if operand_str:
            instruction = f"    {mnemonic} {operand_str}"
        else:
            instruction = f"    {mnemonic}"

        if comment:
            instruction += f"  {comment}"

        # Pokud jsou další byty, zachovat je
        remaining_bytes = bytes_values[length:]
        if remaining_bytes:
            self.asm_lines[self.cursor_line] = instruction
            # Přidat zbylé byty na další řádek
            self.asm_lines.insert(self.cursor_line + 1, f"    !by {', '.join(['$' + b for b in remaining_bytes])}")
            self.add_log(f"Converted {length} bytes to {mnemonic} (kept {len(remaining_bytes)} remaining bytes)")
        else:
            self.asm_lines[self.cursor_line] = instruction
            self.add_log(f"Converted to instruction: {mnemonic} {operand_str}".strip())

    def toggle_sprite_preview(self):
        """Toggle sprite preview pro aktuální řádek"""
        if self.cursor_line >= len(self.asm_lines):
            return

        current_line = self.asm_lines[self.cursor_line].strip()

        # Kontrola, zda je to !by nebo !byte direktiva
        if not (current_line.startswith('!by ') or current_line.startswith('!byte ')):
            self.add_log("Not a byte directive - use 'v' on !by line", error=True)
            return

        # Extrahovat byty
        bytes_values = self.extract_bytes_from_line(current_line)

        if len(bytes_values) != 8:
            self.add_log(f"Sprite preview requires exactly 8 bytes (found {len(bytes_values)})", error=True)
            return

        # Toggle preview
        if self.show_sprite_preview and self.sprite_preview_line == self.cursor_line:
            # Vypnout preview
            self.show_sprite_preview = False
            self.sprite_preview_line = None
            self.add_log("Sprite preview OFF")
        else:
            # Zapnout preview
            self.show_sprite_preview = True
            self.sprite_preview_line = self.cursor_line
            self.add_log("Sprite preview ON")

    def show_hex_as_decimal(self):
        """Zobrazit hexa čísla na aktuálním řádku jako decimální"""
        if self.cursor_line >= len(self.asm_lines):
            return

        current_line = self.asm_lines[self.cursor_line]

        # Najít všechna hexa čísla začínající $
        import re
        hex_numbers = re.findall(r'\$([0-9A-Fa-f]+)', current_line)

        if not hex_numbers:
            self.add_log("No hex numbers found on this line", error=True)
            return

        # Vytvořit nový řádek s decimálními čísly
        decimal_line = current_line
        for hex_num in hex_numbers:
            try:
                dec_value = int(hex_num, 16)
                # Nahradit $XX za decimální hodnotu
                decimal_line = decimal_line.replace(f'${hex_num}', str(dec_value), 1)
            except ValueError:
                continue

        # Zobrazit ve stavové liště (přidáme do logu, který se zobrazuje dole)
        self.add_log(f"Decimal: {decimal_line.strip()}")

    def toggle_disasm_mode(self):
        """Toggle Disassembler mode"""
        if self.disasm_mode:
            # Vypnout disasm mode
            self.disasm_mode = False
            self.add_log("Disassembler mode OFF")

            # Zeptat se, zda smazat referenční soubor
            if self.reference_file and os.path.exists(self.reference_file):
                self.add_log("Delete reference file? Press 'y' to confirm, any other key to keep")

                # Překreslit obrazovku, aby byla zpráva vidět
                self.draw_screen()

                # Čekat na odpověď
                self.stdscr.nodelay(0)
                key = self.stdscr.getch()
                self.stdscr.nodelay(1)

                if key == ord('y') or key == ord('Y'):
                    try:
                        os.remove(self.reference_file)
                        self.add_log(f"Deleted: {os.path.basename(self.reference_file)}")
                    except Exception as e:
                        self.add_log(f"Failed to delete: {str(e)}", error=True)
                else:
                    self.add_log(f"Kept: {os.path.basename(self.reference_file)}")

                self.reference_file = None
        else:
            # Zapnout disasm mode
            self.disasm_mode = True
            self.add_log("Disassembler mode ON - creating reference file...")

            # Provést kompilaci a vytvořit referenční soubor
            self.compile_and_show_hex()

    def compare_with_reference(self):
        """Porovnat aktuální binární soubor s referenčním"""
        if not self.reference_file or not os.path.exists(self.reference_file):
            return

        if not self.bin_file or not os.path.exists(self.bin_file):
            return

        try:
            # Načíst referenční soubor
            with open(self.reference_file, 'rb') as f:
                ref_data = f.read()

            # Načíst aktuální binární soubor
            with open(self.bin_file, 'rb') as f:
                current_data = f.read()

            # Porovnat
            if ref_data == current_data:
                self.add_log("Binary IDENTICAL to reference")
            else:
                # Najít první rozdíl
                min_len = min(len(ref_data), len(current_data))
                first_diff = None

                for i in range(min_len):
                    if ref_data[i] != current_data[i]:
                        first_diff = i
                        break

                if first_diff is not None:
                    self.add_log(f"Binary DIFFERS at offset ${first_diff:04X}: ref=${ref_data[first_diff]:02X} cur=${current_data[first_diff]:02X}")
                elif len(ref_data) != len(current_data):
                    self.add_log(f"Binary DIFFERS in size: ref={len(ref_data)} cur={len(current_data)}")

        except Exception as e:
            self.add_log(f"Comparison failed: {str(e)}", error=True)

    def update_sprite_preview_for_current_line(self):
        """Aktualizovat sprite preview pro aktuální řádek (při pohybu)"""
        if self.cursor_line >= len(self.asm_lines):
            # Vypnout preview pokud jsme mimo rozsah
            self.show_sprite_preview = False
            self.sprite_preview_line = None
            return

        current_line = self.asm_lines[self.cursor_line].strip()

        # Kontrola, zda je to !by nebo !byte direktiva s 8 byty
        if not (current_line.startswith('!by ') or current_line.startswith('!byte ')):
            # Pokud není !by řádek, vypnout preview
            self.show_sprite_preview = False
            self.sprite_preview_line = None
            return

        # Extrahovat byty
        bytes_values = self.extract_bytes_from_line(current_line)

        if len(bytes_values) != 8:
            # Pokud není 8 bytů, vypnout preview
            self.show_sprite_preview = False
            self.sprite_preview_line = None
            return

        # Aktualizovat preview na nový řádek
        self.sprite_preview_line = self.cursor_line

    def find_line_by_address(self, target_address):
        """Najít řádek ASM kódu podle absolutní adresy pomocí pseudopc mapy"""
        for block in self.pseudopc_map:
            pseudopc_start = block['pseudopc_address']
            bin_offset_start = block['bin_offset']

            # Projít všechny řádky v tomto pseudopc bloku
            for line_num in range(block['start_line'], block['end_line'] + 1):
                if line_num in self.asm_to_bin_map:
                    bin_offset = self.asm_to_bin_map[line_num]
                    # Vypočítat virtuální adresu pro tento řádek
                    virtual_address = pseudopc_start + (bin_offset - bin_offset_start)

                    # Pokud se adresa shoduje, vrátit číslo řádku
                    if virtual_address == target_address:
                        return line_num

                    # Pokud jsme překročili cílovou adresu, vrátit předchozí řádek
                    if virtual_address > target_address and line_num > block['start_line']:
                        return line_num - 1

        return None

    def jump_to_line(self, line_num):
        """Skočit na zadaný řádek a aktualizovat scroll"""
        self.cursor_line = line_num

        # Aktualizovat scroll
        height, width = self.stdscr.getmaxyx()
        editor_height = height - 11
        if self.cursor_line < self.scroll_offset:
            self.scroll_offset = self.cursor_line
        elif self.cursor_line >= self.scroll_offset + editor_height:
            self.scroll_offset = self.cursor_line - editor_height + 1

    def get_word_under_cursor(self):
        """Získat slovo pod kurzorem"""
        if self.cursor_line >= len(self.asm_lines):
            return None

        line = self.asm_lines[self.cursor_line]
        if self.cursor_col >= len(line):
            return None

        # Najít začátek a konec slova (label)
        # Label může obsahovat písmena, čísla, podtržítka a tečky
        # NEOBSAHUJE: minus (-), plus (+), hvězdičku (*), lomítko (/) - to jsou matematické operátory
        start = self.cursor_col
        end = self.cursor_col

        # Najít začátek slova
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] in '_.'):
            start -= 1

        # Najít konec slova
        while end < len(line) and (line[end].isalnum() or line[end] in '_.'):
            end += 1

        if start == end:
            return None

        return line[start:end]

    def find_next_label_occurrence(self):
        """Najít další výskyt labelu na kterém stojím"""
        import re
        word = self.get_word_under_cursor()

        # Pokud není slovo pod kurzorem (např. jsme na TAB nebo mezeře),
        # zkusit najít instrukci na řádku
        if not word and self.cursor_line < len(self.asm_lines):
            line = self.asm_lines[self.cursor_line]
            parts = line.split()
            if parts:
                word = parts[0]  # První slovo na řádku

        if not word:
            self.add_log("No label under cursor", error=True)
            return

        # Odstranit matematické operace ze slova (může tam být když je word celý operand)
        # Např. když řádek je "!word L_8077-1" a word je celý "L_8077-1"
        # Toto by se ale nemělo stát díky úpravě get_word_under_cursor(), ale pro jistotu
        word = re.split(r'[+\-*/]', word)[0].strip()
        if not word:
            self.add_log("No valid label found", error=True)
            return

        # Pokud je word instrukce nebo direktiva s operandem, najít label/adresu v operandu
        if word.upper() in [
            'JMP', 'JSR', 'BNE', 'BEQ', 'BCC', 'BCS',
            'BMI', 'BPL', 'BVC', 'BVS', 'JML', 'BRA',
            '!WORD', '!WO'
        ]:
            # Extrahovat label z operandu
            if self.cursor_line < len(self.asm_lines):
                line = self.asm_lines[self.cursor_line]
                # Najít label za instrukcí (oddělený mezerou nebo tabulátorem)
                parts = line.split()
                if len(parts) >= 2:
                    # Druhá část by měl být label (může být s nebo bez #, $, atd.)
                    operand = parts[1]

                    # Kontrola, zda je to absolutní adresa ($XXXX)
                    if operand.startswith('$'):
                        # Je to adresa - zkusit najít pomocí pseudopc mapy
                        try:
                            target_address = int(operand[1:].rstrip(','), 16)
                            target_line = self.find_line_by_address(target_address)
                            if target_line is not None:
                                self.jump_to_line(target_line)
                                self.add_log(f"Jumped to address ${target_address:04X}")
                                return
                            else:
                                self.add_log(f"Address ${target_address:04X} not found in pseudopc blocks", error=True)
                                return
                        except ValueError:
                            self.add_log("Invalid address format", error=True)
                            return

                    # Odstranit addressing mode symboly
                    operand = operand.lstrip('#$')
                    # Odstranit komentář pokud je na konci
                    if ';' in operand:
                        operand = operand.split(';')[0].strip()
                    # Odstranit čárky (pro X,Y indexing)
                    operand = operand.rstrip(',')
                    # Odstranit matematické operace (+1, -1, +2, atd.)
                    # L_8077-1 -> L_8077
                    # L_8077+1 -> L_8077
                    import re
                    operand = re.split(r'[+\-*/]', operand)[0].strip()
                    if operand:
                        word = operand
                    else:
                        self.add_log("No label found in instruction operand", error=True)
                        return
                else:
                    self.add_log("No operand found for instruction", error=True)
                    return

        # Pokud hledáme nový label nebo je to první hledání
        if self.label_search_text != word:
            # Nové hledání
            self.label_search_text = word
            self.label_search_results = []
            self.label_search_index = 0

            # Najít všechny výskyty - hledat definici labelu (s dvojtečkou)
            for i, line in enumerate(self.asm_lines):
                # Zkontrolovat, zda řádek obsahuje definici labelu (word:)
                stripped = line.strip()
                # Zkontrolovat různé formáty:
                # 1. "LABEL:" na začátku řádku
                # 2. "LABEL: instrukce" (label s kódem na stejném řádku)
                if stripped.startswith(word + ':') or f' {word}:' in line:
                    self.label_search_results.append(i)
                    continue

                # Pokud nenajdeme definici, přidat všechny ostatní výskyty
                # (ale až po kontrole definice)

            # Pokud jsme nenašli definici, hledat všechny výskyty
            if not self.label_search_results:
                for i, line in enumerate(self.asm_lines):
                    if word in line:
                        self.label_search_results.append(i)

            if not self.label_search_results:
                self.add_log(f"Label '{word}' not found", error=True)
                return

            # Najít první výskyt za aktuálním řádkem
            for idx, line_num in enumerate(self.label_search_results):
                if line_num > self.cursor_line:
                    self.label_search_index = idx
                    break
            else:
                # Žádný výskyt za aktuálním řádkem, začít od začátku
                self.label_search_index = 0

            self.add_log(f"Found {len(self.label_search_results)} occurrences of '{word}'")
        else:
            # Pokračovat v hledání - přejít na další výskyt
            if not self.label_search_results:
                return

            self.label_search_index = (self.label_search_index + 1) % len(self.label_search_results)

        # Skočit na nalezený řádek
        target_line = self.label_search_results[self.label_search_index]
        self.cursor_line = target_line

        # Aktualizovat scroll
        height, width = self.stdscr.getmaxyx()
        editor_height = height - 11
        if self.cursor_line < self.scroll_offset:
            self.scroll_offset = self.cursor_line
        elif self.cursor_line >= self.scroll_offset + editor_height:
            self.scroll_offset = self.cursor_line - editor_height + 1

        self.add_log(f"Jump to '{word}' ({self.label_search_index + 1}/{len(self.label_search_results)})")

    def compile_asm(self):
        """Kompilace ASM"""
        if not self.current_file:
            self.add_log("No file to compile", error=True)
            return

        self.save_file()
        self.add_log(f"Compiling {os.path.basename(self.current_file)}...")

        # Vytvořit report file pro přesné mapování
        self.report_file = self.current_file + ".report"

        try:
            result = subprocess.run(
                [self.acme_path, "-r", self.report_file, self.current_file],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Find output file
                for line in self.asm_lines:
                    if line.strip().startswith('!to'):
                        parts = line.split('"')
                        if len(parts) >= 2:
                            self.bin_file = os.path.join(
                                os.path.dirname(self.current_file),
                                parts[1]
                            )
                            self.add_log(f"Compile OK -> {os.path.basename(self.bin_file)}")
                            break
                if not self.bin_file:
                    self.add_log("Compile OK (no output file defined)")
            else:
                # Compile error
                self.add_log("Compile FAILED", error=True)
                # Přidat chybové zprávy z ACME
                if result.stderr:
                    for err_line in result.stderr.strip().split('\n')[:5]:  # Max 5 řádků
                        self.add_log(err_line.strip(), error=True)
                if result.stdout:
                    for out_line in result.stdout.strip().split('\n')[:5]:
                        self.add_log(out_line.strip(), error=True)
        except subprocess.TimeoutExpired:
            self.add_log("Compile timeout (>10s)", error=True)
        except FileNotFoundError:
            self.add_log("ACME not found - install it first", error=True)
        except Exception as e:
            self.add_log(f"Compile error: {str(e)}", error=True)

    def compile_and_show_hex(self):
        """Kompilace a zobrazení HEX"""
        self.compile_asm()

        if self.bin_file and os.path.exists(self.bin_file):
            try:
                # Pokud je disasm mode a ještě nemáme referenční soubor, vytvořit ho
                if self.disasm_mode and not self.reference_file:
                    self.reference_file = self.bin_file + ".ref"
                    import shutil
                    shutil.copy2(self.bin_file, self.reference_file)
                    self.add_log(f"Created reference: {os.path.basename(self.reference_file)}")

                with open(self.bin_file, 'rb') as f:
                    self.hex_data = f.read()

                # Použít report file pro přesné mapování (pokud existuje)
                if self.report_file and os.path.exists(self.report_file):
                    self.build_mappings_from_report()
                else:
                    self.build_mappings()

                self.add_log(f"Loaded {len(self.hex_data)} bytes to HEX viewer")

                # Pokud je disasm mode a máme referenční soubor, porovnat
                if self.disasm_mode and self.reference_file:
                    self.compare_with_reference()

            except Exception as e:
                self.add_log(f"Failed to load binary: {str(e)}", error=True)
        elif self.bin_file:
            self.add_log(f"Binary file not found: {self.bin_file}", error=True)

    def build_mappings_from_report(self):
        """Vytvoření mapování ASM -> BIN ze ACME report file (přesné!)"""
        self.asm_to_bin_map = {}

        try:
            with open(self.report_file, 'r', encoding='utf-8', errors='ignore') as f:
                in_main_source = False
                main_source_name = os.path.basename(self.current_file)

                for line in f:
                    # Detekovat začátek hlavního souboru
                    if f'Source: {main_source_name}' in line:
                        in_main_source = True
                        continue

                    # Detekovat začátek jiného souboru
                    if 'Source:' in line and main_source_name not in line:
                        in_main_source = False
                        continue

                    # Pokud jsme v hlavním souboru, parsovat řádky
                    if in_main_source:
                        # Formát: "  ČÍSLO_ŘÁDKU  OFFSET HEXDATA  KÓD"
                        # Příklad: "  3649  186f 7998829888988f98...    !word $9879,$9882,$9888,$988F,$9895"
                        match = re.match(r'^\s+(\d+)\s+([0-9a-fA-F]{4})\s+', line)
                        if match:
                            line_num = int(match.group(1)) - 1  # Čísla řádků začínají od 1
                            offset_hex = match.group(2)
                            byte_offset = int(offset_hex, 16)

                            # Uložit mapování
                            self.asm_to_bin_map[line_num] = byte_offset

            self.add_log(f"Loaded {len(self.asm_to_bin_map)} mappings from report file")

        except Exception as e:
            self.add_log(f"Failed to parse report file: {str(e)}", error=True)
            # Fallback na starší metodu
            self.build_mappings()

    def build_mappings(self):
        """Vytvoření mapování ASM -> BIN (přesné pomocí opcode tabulky)"""
        self.asm_to_bin_map = {}
        self.pseudopc_map = []
        byte_offset = 0
        current_pseudopc = None
        pseudopc_start_line = None
        pseudopc_start_offset = None

        # Detekovat formát souboru (!to "file", cbm nebo plain)
        is_cbm_format = False
        for line in self.asm_lines:
            if '!to' in line.lower() and 'cbm' in line.lower():
                is_cbm_format = True
                break

        # Pro .prg soubory s cbm formátem: první 2 byty jsou load adresa
        # Pro plain formát: data začínají na offsetu 0
        # byte_offset se pak inkrementuje sekvenčně celým souborem
        byte_offset = 2 if is_cbm_format else 0
        current_address = None  # Sleduje aktuální adresu v paměti (pro informaci)

        for line_num, line in enumerate(self.asm_lines):
            line_stripped = line.strip()

            # Ignorovat prázdné řádky a čisté komentáře
            if not line_stripped or line_stripped.startswith(';'):
                continue

            # Zpracovat * = offset directive
            # *= direktivy se ignorují pro byte_offset (ACME zapisuje sekvenčně)
            if line_stripped.startswith('*'):
                match = re.search(r'\*\s*=\s*(\$?[0-9A-Fa-f]+)', line_stripped)
                if match:
                    offset_str = match.group(1)
                    if offset_str.startswith('$'):
                        new_address = int(offset_str[1:], 16)
                    else:
                        new_address = int(offset_str)

                    current_address = new_address
                continue

            # Zpracovat !pseudopc directive
            if line_stripped.startswith('!pseudopc'):
                match = re.search(r'!pseudopc\s+\$([0-9A-Fa-f]+)', line_stripped)
                if match:
                    current_pseudopc = int(match.group(1), 16)
                    pseudopc_start_line = line_num + 1  # Začátek kódu je na dalším řádku
                    pseudopc_start_offset = byte_offset
                continue

            # Ignorovat uzavírací závorku z !pseudopc bloku
            if line_stripped == '}':
                # Uložit pseudopc blok do mapy
                if current_pseudopc is not None and pseudopc_start_line is not None:
                    self.pseudopc_map.append({
                        'start_line': pseudopc_start_line,
                        'end_line': line_num - 1,
                        'pseudopc_address': current_pseudopc,
                        'bin_offset': pseudopc_start_offset
                    })
                    current_pseudopc = None
                    pseudopc_start_line = None
                    pseudopc_start_offset = None
                continue

            # Ignorovat direktivy které negenerují data
            if any(line_stripped.startswith(d) for d in ['!to', '!source', '!src', '!zone', '!initmem']):
                continue

            # Ignorovat labely bez instrukcí
            if line_stripped.endswith(':') and ' ' not in line_stripped:
                continue

            # Uložit mapování pro tento řádek
            self.asm_to_bin_map[line_num] = byte_offset

            # Odstranit komentář pro parsování
            line_no_comment = line_stripped.split(';')[0].strip()
            if not line_no_comment:
                continue

            # Odstranit label pokud existuje
            if ':' in line_no_comment:
                parts = line_no_comment.split(':', 1)
                if len(parts) > 1:
                    line_no_comment = parts[1].strip()
                else:
                    continue

            # 1. !byte / !by direktivy
            if line_no_comment.startswith('!byte ') or line_no_comment.startswith('!by '):
                bytes_extracted = self.extract_bytes_from_line(line_no_comment)
                num_bytes = len(bytes_extracted)
                byte_offset += num_bytes
                if current_address is not None:
                    current_address += num_bytes

            # 2. !word / !wo direktivy
            elif line_no_comment.startswith('!word ') or line_no_comment.startswith('!wo '):
                # Každé !word zabere 2 byty, spočítat kolik jich je
                words_count = line_no_comment.count('$')
                if words_count == 0:
                    words_count = line_no_comment.count(',') + 1
                num_bytes = words_count * 2
                byte_offset += num_bytes
                if current_address is not None:
                    current_address += num_bytes

            # 3. !text / !tx direktivy
            elif line_no_comment.startswith('!text ') or line_no_comment.startswith('!tx '):
                # Počítat texty v uvozovkách + byty ($XX)
                byte_count = 0

                # Najít všechny texty v uvozovkách
                strings = re.findall(r'"([^"]*)"', line_no_comment)
                for s in strings:
                    byte_count += len(s)

                # Najít všechny byty ($XX)
                hex_bytes = re.findall(r'\$([0-9A-Fa-f]{2})', line_no_comment)
                byte_count += len(hex_bytes)

                byte_offset += byte_count
                if current_address is not None:
                    current_address += byte_count

            # 4. Instrukce - použít opcode tabulku pro přesnou délku
            else:
                # Parsovat instrukci
                instr_match = re.match(r'^\s*([A-Z]{3})\s*(.*)', line_no_comment, re.IGNORECASE)
                if instr_match:
                    mnemonic = instr_match.group(1).upper()
                    operand = instr_match.group(2).strip()

                    # Detekovat adresovací režim
                    addr_mode, _ = self.detect_addressing_mode(operand)

                    # SPECIAL CASE: ASL/LSR/ROL/ROR bez operandu = accumulator mode, ne implied
                    if not operand and mnemonic in ['ASL', 'LSR', 'ROL', 'ROR']:
                        addr_mode = 'ACC'

                    # Získat délku instrukce z opcode tabulky
                    opcode, length = self.get_6502_opcode(mnemonic, addr_mode, operand)

                    if length is not None:
                        byte_offset += length
                        if current_address is not None:
                            current_address += length
                    else:
                        # Neznámá instrukce, použít odhad 2 byty
                        byte_offset += 2
                        if current_address is not None:
                            current_address += 2

    def run(self):
        """Hlavní smyčka editoru"""
        self.running = True

        # Úvodní zpráva
        self.add_log("ACME Terminal Editor started")
        self.add_log("Press :o to open file, i for INSERT mode")

        # Načíst soubor pokud byl zadán
        if self.initial_file:
            if os.path.exists(self.initial_file):
                self.open_file(self.initial_file)
            else:
                self.add_log(f"File not found: {self.initial_file}", error=True)
        else:
            # Pokud není zadán soubor, zkusit načíst poslední z konfigurace
            last_file = self.load_config()
            if last_file and os.path.exists(last_file):
                self.open_file(last_file)
                self.add_log(f"Loaded from config: {os.path.basename(last_file)}")

        while self.running:
            self.draw_screen()

            try:
                key = self.stdscr.getch()
            except KeyboardInterrupt:
                break

            if self.mode == 'NORMAL':
                if not self.handle_normal_mode(key):
                    break
            elif self.mode == 'INSERT':
                self.handle_insert_mode(key)
            elif self.mode == 'COMMAND':
                self.handle_command_mode(key)
            elif self.mode == 'SEARCH':
                self.handle_search_mode(key)


def main(stdscr):
    # Nastavení terminálu
    curses.curs_set(0)
    stdscr.clear()

    # Zkontrolovat command-line argument
    initial_file = None
    if len(sys.argv) > 1:
        initial_file = sys.argv[1]

    editor = AcmeTerminalEditor(stdscr, initial_file)
    editor.run()


if __name__ == "__main__":
    curses.wrapper(main)
