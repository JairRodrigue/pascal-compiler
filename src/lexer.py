"""
=============================================================================
ANALISADOR LÉXICO (SCANNER) — Pascal Subset Compiler
=============================================================================
Responsabilidade:
  Ler o código-fonte caractere a caractere e produzir uma sequência de Tokens.
  Ignora comentários ({ ... }) e espaços em branco.

Tokens reconhecidos:
  - Palavras reservadas: program, var, procedure, begin, end, if, then, else,
                         while, do, integer, real, not, div, mod, and, or
  - Identificadores (id)
  - Números inteiros e reais (num)
  - Operadores: :=, relops (=, <, >, <=, >=, <>), addops (+, -, or),
                mulops (*, /, div, mod, and)
  - Delimitadores: ; , : ( ) .
=============================================================================
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Tipos de Token
# ---------------------------------------------------------------------------
class TokenType(Enum):
    # Palavras reservadas
    PROGRAM    = auto()
    VAR        = auto()
    PROCEDURE  = auto()
    BEGIN      = auto()
    END        = auto()
    IF         = auto()
    THEN       = auto()
    ELSE       = auto()
    WHILE      = auto()
    DO         = auto()
    INTEGER    = auto()
    REAL       = auto()
    NOT        = auto()

    # Literais
    ID         = auto()   # identificador
    NUM        = auto()   # número (int ou real)

    # Operadores
    ASSIGNOP   = auto()   # :=
    RELOP      = auto()   # = < > <= >= <>
    ADDOP      = auto()   # + - OR
    MULOP      = auto()   # * / DIV MOD AND

    # Delimitadores
    SEMICOLON  = auto()   # ;
    COMMA      = auto()   # ,
    COLON      = auto()   # :
    LPAREN     = auto()   # (
    RPAREN     = auto()   # )
    DOT        = auto()   # .

    # Fim de arquivo
    EOF        = auto()


# Mapa de palavras reservadas (minúsculas → TokenType)
RESERVED_WORDS = {
    "program"  : TokenType.PROGRAM,
    "var"      : TokenType.VAR,
    "procedure": TokenType.PROCEDURE,
    "begin"    : TokenType.BEGIN,
    "end"      : TokenType.END,
    "if"       : TokenType.IF,
    "then"     : TokenType.THEN,
    "else"     : TokenType.ELSE,
    "while"    : TokenType.WHILE,
    "do"       : TokenType.DO,
    "integer"  : TokenType.INTEGER,
    "real"     : TokenType.REAL,
    "not"      : TokenType.NOT,
    "div"      : TokenType.MULOP,
    "mod"      : TokenType.MULOP,
    "and"      : TokenType.MULOP,
    "or"       : TokenType.ADDOP,
}


# ---------------------------------------------------------------------------
# Estrutura de Token
# ---------------------------------------------------------------------------
@dataclass
class Token:
    type:    TokenType
    lexeme:  str          # texto exato no fonte
    value:   object       # valor semântico: número convertido, etc.
    line:    int
    column:  int

    def __repr__(self):
        return (f"Token({self.type.name}, {self.lexeme!r}, "
                f"line={self.line}, col={self.column})")


# ---------------------------------------------------------------------------
# Erros léxicos
# ---------------------------------------------------------------------------
class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"[Léxico] {message} (linha {line}, col {column})")
        self.line   = line
        self.column = column


# ---------------------------------------------------------------------------
# Scanner / Analisador Léxico
# ---------------------------------------------------------------------------
class Lexer:
    """
    Analisador léxico para o subconjunto de Pascal.
    Uso:
        lexer  = Lexer(source_code)
        tokens = lexer.tokenize()   # retorna lista completa de Tokens
        # ou acesso incremental:
        token  = lexer.next_token()
    """

    def __init__(self, source: str):
        self.source  = source
        self.pos     = 0          # posição atual no texto
        self.line    = 1
        self.column  = 1
        self._tokens: list[Token] = []

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------
    def tokenize(self) -> list[Token]:
        """Processa todo o fonte e retorna a lista de tokens."""
        self.pos    = 0
        self.line   = 1
        self.column = 1
        tokens = []
        while True:
            tok = self.next_token()
            tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        return tokens

    def next_token(self) -> Token:
        """Retorna o próximo token do fonte."""
        self._skip_whitespace_and_comments()

        if self.pos >= len(self.source):
            return self._make_token(TokenType.EOF, "EOF", None)

        ch = self._peek()

        # Identificadores e palavras reservadas
        if ch.isalpha():
            return self._read_id_or_keyword()

        # Números
        if ch.isdigit():
            return self._read_number()

        # Operadores e delimitadores
        return self._read_operator_or_delimiter()

    # ------------------------------------------------------------------
    # Leitura de identificadores / palavras reservadas
    # ------------------------------------------------------------------
    def _read_id_or_keyword(self) -> Token:
        start_line, start_col = self.line, self.column
        lexeme = []
        while self.pos < len(self.source) and (
                self._peek().isalpha() or self._peek().isdigit()):
            lexeme.append(self._advance())
        word = "".join(lexeme)
        lower = word.lower()

        ttype = RESERVED_WORDS.get(lower)
        if ttype:
            # addop / mulop carregam o lexema como valor
            if ttype in (TokenType.ADDOP, TokenType.MULOP):
                return Token(ttype, word, lower, start_line, start_col)
            return Token(ttype, word, lower, start_line, start_col)

        return Token(TokenType.ID, word, word, start_line, start_col)

    # ------------------------------------------------------------------
    # Leitura de números
    # num → digits optional_fraction optional_exponent
    # ------------------------------------------------------------------
    def _read_number(self) -> Token:
        start_line, start_col = self.line, self.column
        lexeme = []
        is_real = False

        # Parte inteira
        while self.pos < len(self.source) and self._peek().isdigit():
            lexeme.append(self._advance())

        # Parte fracionária opcional
        if self.pos < len(self.source) and self._peek() == '.':
            # lookahead para evitar confundir com DOT final
            if self.pos + 1 < len(self.source) and self.source[self.pos + 1].isdigit():
                is_real = True
                lexeme.append(self._advance())  # consome '.'
                while self.pos < len(self.source) and self._peek().isdigit():
                    lexeme.append(self._advance())

        # Expoente opcional: E ou e, seguido de [+-]? digits
        if self.pos < len(self.source) and self._peek() in ('E', 'e'):
            is_real = True
            lexeme.append(self._advance())  # E
            if self.pos < len(self.source) and self._peek() in ('+', '-'):
                lexeme.append(self._advance())
            if not (self.pos < len(self.source) and self._peek().isdigit()):
                raise LexerError("Expoente inválido em literal numérico",
                                 start_line, start_col)
            while self.pos < len(self.source) and self._peek().isdigit():
                lexeme.append(self._advance())

        word = "".join(lexeme)
        value = float(word) if is_real else int(word)
        return Token(TokenType.NUM, word, value, start_line, start_col)

    # ------------------------------------------------------------------
    # Leitura de operadores e delimitadores
    # ------------------------------------------------------------------
    def _read_operator_or_delimiter(self) -> Token:
        start_line, start_col = self.line, self.column
        ch = self._advance()

        simple = {
            ';': TokenType.SEMICOLON,
            ',': TokenType.COMMA,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '.': TokenType.DOT,
            '+': TokenType.ADDOP,
            '-': TokenType.ADDOP,
            '*': TokenType.MULOP,
            '/': TokenType.MULOP,
            '=': TokenType.RELOP,
        }

        if ch in simple:
            return Token(simple[ch], ch, ch, start_line, start_col)

        # '<' → < | <= | <>
        if ch == '<':
            if self.pos < len(self.source) and self._peek() == '=':
                self._advance()
                return Token(TokenType.RELOP, '<=', '<=', start_line, start_col)
            if self.pos < len(self.source) and self._peek() == '>':
                self._advance()
                return Token(TokenType.RELOP, '<>', '<>', start_line, start_col)
            return Token(TokenType.RELOP, '<', '<', start_line, start_col)

        # '>' → > | >=
        if ch == '>':
            if self.pos < len(self.source) and self._peek() == '=':
                self._advance()
                return Token(TokenType.RELOP, '>=', '>=', start_line, start_col)
            return Token(TokenType.RELOP, '>', '>', start_line, start_col)

        # ':' → : | :=
        if ch == ':':
            if self.pos < len(self.source) and self._peek() == '=':
                self._advance()
                return Token(TokenType.ASSIGNOP, ':=', ':=', start_line, start_col)
            return Token(TokenType.COLON, ':', ':', start_line, start_col)

        raise LexerError(f"Caractere inesperado: {ch!r}", start_line, start_col)

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------
    def _peek(self) -> str:
        return self.source[self.pos]

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line  += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _make_token(self, ttype: TokenType, lexeme: str, value) -> Token:
        return Token(ttype, lexeme, value, self.line, self.column)

    def _skip_whitespace_and_comments(self):
        """Pula espaços em branco e comentários { ... }."""
        while self.pos < len(self.source):
            ch = self._peek()
            if ch in (' ', '\t', '\r', '\n'):
                self._advance()
            elif ch == '{':
                self._skip_comment()
            else:
                break

    def _skip_comment(self):
        """Consome { ... } incluindo comentários aninhados não permitidos."""
        start_line, start_col = self.line, self.column
        self._advance()  # consome '{'
        while self.pos < len(self.source):
            ch = self._advance()
            if ch == '}':
                return
        raise LexerError("Comentário não fechado", start_line, start_col)
