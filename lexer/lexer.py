"""
C Language Lexical Analyzer - Core Engine
==========================================
Implements:
  - Tokenization of C source code (DFA-driven, regex-backed transition rules)
  - Symbol Table construction & management
  - Lexical Error Detection with meaningful messages

This module is GUI-agnostic. The Streamlit app (app.py) imports and drives it.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Token categories recognized by the lexer
# ---------------------------------------------------------------------------
TOKEN_TYPES = [
    "KEYWORD",
    "IDENTIFIER",
    "INTEGER_CONSTANT",
    "FLOAT_CONSTANT",
    "CHAR_CONSTANT",
    "STRING_LITERAL",
    "OPERATOR",
    "PUNCTUATION",
    "PREPROCESSOR",
    "COMMENT",
    "ERROR",
]

# Reserved keywords of the C language (C89/C99 core set)
C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "int", "long", "register", "return", "short", "signed", "sizeof",
    "static", "struct", "switch", "typedef", "union", "unsigned", "void",
    "volatile", "while", "inline", "restrict", "_Bool", "_Complex",
    "_Imaginary",
}

# Reserved words that belong to OTHER languages (Python / Java / C++) and are
# NOT valid C keywords. When the analyzer meets one of these as a bare word it
# is almost certainly non-C source, so we report it as a lexical error instead
# of silently accepting it as an ordinary identifier. Words that overlap with C
# (if/else/for/while/return/break/continue/case ...) are intentionally excluded
# so shared constructs are still accepted.
NON_C_KEYWORDS = {
    # --- Python-specific ---
    "def", "elif", "lambda", "import", "from", "as", "class", "try",
    "except", "finally", "raise", "with", "yield", "global", "nonlocal",
    "pass", "del", "assert", "and", "or", "not", "is", "in", "None",
    "True", "False", "async", "await", "print",
    # --- Java-specific ---
    "boolean", "byte", "transient", "extends", "implements", "package",
    "final", "abstract", "instanceof", "interface", "synchronized",
    "native", "super", "throws", "import",
    # --- C++-specific ---
    "public", "private", "protected", "namespace", "using", "template",
    "typename", "virtual", "friend", "this", "throw", "catch", "operator",
    "new", "delete", "nullptr", "explicit", "mutable", "bool", "true",
    "false",
}

# Multi-character operators must be listed before their single-char prefixes
MULTI_CHAR_OPERATORS = [
    "<<=", ">>=", "...", "->", "++", "--", "<<", ">>", "<=", ">=",
    "==", "!=", "&&", "||", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
]
SINGLE_CHAR_OPERATORS = set("+-*/%=<>!&|^~?:")
PUNCTUATION_CHARS = set("(){}[];,.")

IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Float: digits.digits / digits. / .digits, optional exponent, optional suffix
FLOAT_RE = re.compile(
    r"(\d+\.\d*([eE][+-]?\d+)?[fFlL]?)"
    r"|(\.\d+([eE][+-]?\d+)?[fFlL]?)"
    r"|(\d+[eE][+-]?\d+[fFlL]?)"
)
# Integer: hex, octal, decimal with optional suffix (u, l, ul, etc.)
INT_RE = re.compile(
    r"0[xX][0-9a-fA-F]+[uUlL]*"      # hex
    r"|0[0-7]+[uUlL]*"                # octal
    r"|\d+[uUlL]*"                    # decimal
)


@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    column: int


@dataclass
class LexError:
    message: str
    lexeme: str
    line: int
    column: int


@dataclass
class SymbolEntry:
    name: str
    category: str          # e.g. IDENTIFIER, KEYWORD-as-type-context, etc.
    first_line: int
    occurrences: int = 1
    data_type: Optional[str] = None  # best-effort inferred type, if detectable


class CLexicalAnalyzer:
    """
    A hand-rolled lexical analyzer for (a practical, teaching-oriented subset
    of) the C programming language.

    Design notes (for the project report):
      - The analyzer scans the source left-to-right maintaining (line, column).
      - At each position it applies the "maximal munch" rule: among all token
        patterns that match at the current position, the longest match wins.
        This is the same principle real lexers (lex/flex) use, implemented
        here explicitly via ordered pattern attempts (multi-char operators
        checked before single-char ones, etc.)
      - Comments and preprocessor directives are tokenized but excluded from
        the symbol table.
      - Unrecognized characters or malformed literals produce ERROR tokens
        with line/column and a descriptive message, then the scanner
        recovers by skipping the offending character(s) and continuing.
    """

    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []
        self.errors: List[LexError] = []
        self.symbol_table: Dict[str, SymbolEntry] = {}
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(source)

    # ------------------------------------------------------------------
    # Low-level character helpers
    # ------------------------------------------------------------------
    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        return self.source[idx] if idx < self.length else ""

    def _advance(self, n: int = 1) -> str:
        chunk = self.source[self.pos:self.pos + n]
        for ch in chunk:
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        self.pos += n
        return chunk

    def _add_token(self, ttype: str, lexeme: str, line: int, col: int):
        self.tokens.append(Token(ttype, lexeme, line, col))

    def _add_error(self, message: str, lexeme: str, line: int, col: int):
        self.errors.append(LexError(message, lexeme, line, col))
        self.tokens.append(Token("ERROR", lexeme, line, col))

    # ------------------------------------------------------------------
    # Symbol table management
    # ------------------------------------------------------------------
    def _record_symbol(self, name: str, category: str, line: int,
                        data_type: Optional[str] = None):
        if name in self.symbol_table:
            entry = self.symbol_table[name]
            entry.occurrences += 1
            if data_type and not entry.data_type:
                entry.data_type = data_type
        else:
            self.symbol_table[name] = SymbolEntry(
                name=name, category=category, first_line=line,
                occurrences=1, data_type=data_type
            )

    # ------------------------------------------------------------------
    # Main driver
    # ------------------------------------------------------------------
    def tokenize(self):
        last_type_keyword = None  # tracks a preceding type keyword e.g. 'int x'

        while self.pos < self.length:
            ch = self._peek()
            start_line, start_col = self.line, self.col

            # ---- whitespace ----
            if ch in " \t\r\n":
                self._advance()
                continue

            # ---- line comment ----
            if ch == "/" and self._peek(1) == "/":
                start = self.pos
                while self.pos < self.length and self._peek() != "\n":
                    self._advance()
                lexeme = self.source[start:self.pos]
                self._add_token("COMMENT", lexeme, start_line, start_col)
                continue

            # ---- block comment ----
            if ch == "/" and self._peek(1) == "*":
                start = self.pos
                self._advance(2)
                closed = False
                while self.pos < self.length:
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance(2)
                        closed = True
                        break
                    self._advance()
                lexeme = self.source[start:self.pos]
                if not closed:
                    self._add_error(
                        "Unterminated block comment", lexeme,
                        start_line, start_col
                    )
                else:
                    self._add_token("COMMENT", lexeme, start_line, start_col)
                continue

            # ---- preprocessor directive ----
            if ch == "#":
                start = self.pos
                while self.pos < self.length and self._peek() != "\n":
                    self._advance()
                lexeme = self.source[start:self.pos]
                self._add_token("PREPROCESSOR", lexeme, start_line, start_col)
                continue

            # ---- string literal ----
            if ch == '"':
                start = self.pos
                self._advance()
                closed = False
                while self.pos < self.length:
                    c = self._peek()
                    if c == "\\":
                        self._advance(2)
                        continue
                    if c == '"':
                        self._advance()
                        closed = True
                        break
                    if c == "\n":
                        break
                    self._advance()
                lexeme = self.source[start:self.pos]
                if not closed:
                    self._add_error(
                        "Unterminated string literal", lexeme,
                        start_line, start_col
                    )
                else:
                    self._add_token("STRING_LITERAL", lexeme, start_line, start_col)
                continue

            # ---- char literal ----
            if ch == "'":
                start = self.pos
                self._advance()
                closed = False
                while self.pos < self.length:
                    c = self._peek()
                    if c == "\\":
                        self._advance(2)
                        continue
                    if c == "'":
                        self._advance()
                        closed = True
                        break
                    if c == "\n":
                        break
                    self._advance()
                lexeme = self.source[start:self.pos]
                if not closed:
                    self._add_error(
                        "Unterminated character literal", lexeme,
                        start_line, start_col
                    )
                elif not (3 <= len(lexeme) <= 4):
                    self._add_error(
                        "Invalid character constant (must contain exactly one character)",
                        lexeme, start_line, start_col
                    )
                else:
                    self._add_token("CHAR_CONSTANT", lexeme, start_line, start_col)
                continue

            # ---- numbers (int / float) ----
            if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
                start = self.pos

                # First, find the full "numeric-looking" span: digits, dots,
                # and letters glued together with no separator. This lets us
                # detect malformed literals like "45xy" or "3.14.15" as a
                # single span before deciding whether it is well-formed.
                j = self.pos
                while j < self.length and (self.source[j].isalnum() or self.source[j] == "."):
                    j += 1
                full_span = self.source[start:j]

                m_float = FLOAT_RE.match(self.source, self.pos)
                m_int = INT_RE.match(self.source, self.pos)

                is_float = bool(m_float) and (
                    "." in m_float.group(0) or "e" in m_float.group(0).lower()
                )
                best_match = None
                best_type = None
                if is_float and m_int:
                    if len(m_float.group(0)) >= len(m_int.group(0)):
                        best_match, best_type = m_float.group(0), "FLOAT_CONSTANT"
                    else:
                        best_match, best_type = m_int.group(0), "INTEGER_CONSTANT"
                elif is_float:
                    best_match, best_type = m_float.group(0), "FLOAT_CONSTANT"
                elif m_int:
                    best_match, best_type = m_int.group(0), "INTEGER_CONSTANT"

                if best_match is not None and best_match == full_span:
                    # The well-formed numeric pattern consumes the ENTIRE
                    # contiguous numeric-looking span -> valid literal.
                    self._advance(len(best_match))
                    self._add_token(best_type, best_match, start_line, start_col)
                else:
                    # Either no valid pattern matched, or a valid prefix
                    # matched but extra alnum/dot characters trail it
                    # (e.g. "45xy", "3.14.15") -> malformed literal.
                    self._advance(len(full_span))
                    self._add_error(
                        f"Malformed numeric literal '{full_span}'", full_span,
                        start_line, start_col
                    )
                continue

            # ---- identifiers / keywords ----
            if ch.isalpha() or ch == "_":
                m = IDENTIFIER_RE.match(self.source, self.pos)
                lexeme = m.group(0)
                self._advance(len(lexeme))
                if lexeme in C_KEYWORDS:
                    self._add_token("KEYWORD", lexeme, start_line, start_col)
                    if lexeme in {"int", "float", "char", "double", "void",
                                  "long", "short", "unsigned", "signed"}:
                        last_type_keyword = lexeme
                    else:
                        last_type_keyword = None
                elif lexeme in NON_C_KEYWORDS:
                    last_type_keyword = None
                    self._add_error(
                        f"'{lexeme}' is a reserved keyword in another language "
                        f"and is not valid in C",
                        lexeme, start_line, start_col
                    )
                else:
                    self._add_token("IDENTIFIER", lexeme, start_line, start_col)
                    self._record_symbol(
                        lexeme, "IDENTIFIER", start_line,
                        data_type=last_type_keyword
                    )
                continue

            # ---- multi-char operators ----
            matched_multi = None
            for op in MULTI_CHAR_OPERATORS:
                if self.source.startswith(op, self.pos):
                    matched_multi = op
                    break
            if matched_multi:
                self._advance(len(matched_multi))
                self._add_token("OPERATOR", matched_multi, start_line, start_col)
                continue

            # ---- single-char operators ----
            if ch in SINGLE_CHAR_OPERATORS:
                self._advance()
                self._add_token("OPERATOR", ch, start_line, start_col)
                continue

            # ---- punctuation ----
            if ch in PUNCTUATION_CHARS:
                self._advance()
                self._add_token("PUNCTUATION", ch, start_line, start_col)
                continue

            # ---- unrecognized character ----
            self._advance()
            self._add_error(
                f"Illegal character '{ch}'", ch, start_line, start_col
            )

        return self.tokens, self.errors, self.symbol_table

    # ------------------------------------------------------------------
    # Convenience summary stats
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {t: 0 for t in TOKEN_TYPES}
        for tok in self.tokens:
            counts[tok.type] = counts.get(tok.type, 0) + 1
        return counts


def analyze_source(source: str):
    """Convenience wrapper: run the analyzer and return (tokens, errors, symtab, lexer)."""
    lexer = CLexicalAnalyzer(source)
    tokens, errors, symtab = lexer.tokenize()
    return tokens, errors, symtab, lexer