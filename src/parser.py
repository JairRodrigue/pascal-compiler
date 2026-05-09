"""
=============================================================================
ANALISADOR SINTÁTICO (PARSER) — Pascal Subset Compiler
=============================================================================
Parser descendente recursivo (LL) que consome os tokens produzidos pelo Lexer
e constrói a AST definida em ast_nodes.py.

Gramática implementada (BNF simplificada, seguindo a especificação do projeto):

  Program                → Header Declarations Block .
  Header                 → program id ;
  Declarations           → VariableDeclarationSection ProcedureDeclarations*
  VariableDeclarationSection → VAR VariableDeclarations | ε
  VariableDeclarations   → VariableDeclaration+
  VariableDeclaration    → IdentifierList : Type ;
  IdentifierList         → id (, id)*
  Type                   → integer | real
  ProcedureDeclarations  → (ProcedureHeader Declarations Block ;)*
  ProcedureHeader        → procedure id ;
  Block                  → begin Statements end
  Statements             → Statement (; Statement)*
  Statement              → id := Expression
                         | id ()
                         | Block
                         | if Expression then Statement ElseClause
                         | while Expression do Statement
                         | ε
  ElseClause             → else Statement | ε
  Expression             → SimpleExpression (relop SimpleExpression)?
  SimpleExpression       → (addop)? Term (addop Term)*
  Term                   → Factor (mulop Factor)*
  Factor                 → id | num | ( Expression ) | not Factor
=============================================================================
"""

from typing import Optional, List
from lexer import Lexer, Token, TokenType
from ast_nodes import (
    Program, Header, Declarations, VariableDeclaration,
    ProcedureDeclaration, Block, AssignStmt, ProcCallStmt,
    IfStmt, WhileStmt, EmptyStmt, BinaryOp, UnaryOp,
    Identifier, Number, ASTNode
)


# ---------------------------------------------------------------------------
# Erro sintático
# ---------------------------------------------------------------------------
class ParseError(Exception):
    def __init__(self, message: str, token: Token):
        super().__init__(
            f"[Sintático] {message} — "
            f"encontrado '{token.lexeme}' (linha {token.line}, col {token.column})"
        )
        self.token = token


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
class Parser:
    """
    Analisador sintático descendente recursivo.
    Recebe a lista de tokens do Lexer e produz a AST.

    Uso:
        tokens = Lexer(source).tokenize()
        ast    = Parser(tokens).parse()
    """

    def __init__(self, tokens: List[Token]):
        self.tokens  = tokens
        self.pos     = 0

    # ------------------------------------------------------------------
    # Utilitários de navegação
    # ------------------------------------------------------------------
    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._current().type in types

    def _match(self, *types: TokenType) -> Optional[Token]:
        """Consome o token corrente se o tipo bater; retorna None caso contrário."""
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, ttype: TokenType, description: str = "") -> Token:
        """Consome o token corrente exigindo que seja do tipo ttype."""
        if self._check(ttype):
            return self._advance()
        desc = description or ttype.name
        raise ParseError(f"Esperado '{desc}'", self._current())

    # ------------------------------------------------------------------
    # Ponto de entrada
    # ------------------------------------------------------------------
    def parse(self) -> Program:
        """
        Program → Header Declarations Block .
        """
        line    = self._current().line
        header  = self._parse_header()
        decls   = self._parse_declarations()
        block   = self._parse_block()
        self._expect(TokenType.DOT, ".")
        if not self._check(TokenType.EOF):
            tok = self._current()
            raise ParseError("Conteúdo inesperado após o fim do programa", tok)
        return Program(header=header, declarations=decls, block=block, line=line)

    # ------------------------------------------------------------------
    # Header → program id ;
    # ------------------------------------------------------------------
    def _parse_header(self) -> Header:
        line = self._current().line
        self._expect(TokenType.PROGRAM, "program")
        name_tok = self._expect(TokenType.ID, "identificador")
        self._expect(TokenType.SEMICOLON, ";")
        return Header(name=name_tok.lexeme, line=line)

    # ------------------------------------------------------------------
    # Declarations → VariableDeclarationSection ProcedureDeclarations*
    # ------------------------------------------------------------------
    def _parse_declarations(self) -> Declarations:
        line = self._current().line
        var_section = self._parse_variable_declaration_section()
        procedures  = self._parse_procedure_declarations()
        return Declarations(var_section=var_section,
                            procedures=procedures, line=line)

    # VariableDeclarationSection → VAR VariableDeclarations | ε
    def _parse_variable_declaration_section(self) -> List[VariableDeclaration]:
        if not self._match(TokenType.VAR):
            return []
        return self._parse_variable_declarations()

    # VariableDeclarations → VariableDeclaration+
    def _parse_variable_declarations(self) -> List[VariableDeclaration]:
        decls = [self._parse_variable_declaration()]
        # continua enquanto o próximo token for um identificador (início de nova declaração)
        while self._check(TokenType.ID):
            decls.append(self._parse_variable_declaration())
        return decls

    # VariableDeclaration → IdentifierList : Type ;
    def _parse_variable_declaration(self) -> VariableDeclaration:
        line  = self._current().line
        names = self._parse_identifier_list()
        self._expect(TokenType.COLON, ":")
        vtype = self._parse_type()
        self._expect(TokenType.SEMICOLON, ";")
        return VariableDeclaration(identifiers=names, var_type=vtype, line=line)

    # IdentifierList → id (, id)*
    def _parse_identifier_list(self) -> List[str]:
        first = self._expect(TokenType.ID, "identificador")
        names = [first.lexeme]
        while self._match(TokenType.COMMA):
            tok = self._expect(TokenType.ID, "identificador")
            names.append(tok.lexeme)
        return names

    # Type → integer | real
    def _parse_type(self) -> str:
        if self._check(TokenType.INTEGER):
            self._advance()
            return "integer"
        if self._check(TokenType.REAL):
            self._advance()
            return "real"
        raise ParseError("Tipo esperado ('integer' ou 'real')", self._current())

    # ------------------------------------------------------------------
    # ProcedureDeclarations → (ProcedureHeader Declarations Block ;)*
    # ------------------------------------------------------------------
    def _parse_procedure_declarations(self) -> List[ProcedureDeclaration]:
        procs = []
        while self._check(TokenType.PROCEDURE):
            procs.append(self._parse_procedure_declaration())
        return procs

    def _parse_procedure_declaration(self) -> ProcedureDeclaration:
        line = self._current().line
        # ProcedureHeader → procedure id ;
        self._expect(TokenType.PROCEDURE, "procedure")
        name_tok = self._expect(TokenType.ID, "identificador")
        self._expect(TokenType.SEMICOLON, ";")

        decls = self._parse_declarations()
        block = self._parse_block()
        self._expect(TokenType.SEMICOLON, ";")
        return ProcedureDeclaration(name=name_tok.lexeme,
                                    declarations=decls,
                                    block=block, line=line)

    # ------------------------------------------------------------------
    # Block → begin Statements end
    # ------------------------------------------------------------------
    def _parse_block(self) -> Block:
        line = self._current().line
        self._expect(TokenType.BEGIN, "begin")
        stmts = self._parse_statements()
        self._expect(TokenType.END, "end")
        return Block(statements=stmts, line=line)

    # ------------------------------------------------------------------
    # Statements → Statement (; Statement)*
    # ------------------------------------------------------------------
    def _parse_statements(self) -> List[ASTNode]:
        stmts = [self._parse_statement()]
        while self._match(TokenType.SEMICOLON):
            stmts.append(self._parse_statement())
        return stmts

    # ------------------------------------------------------------------
    # Statement → id := Expression
    #           | id ()
    #           | Block
    #           | if Expression then Statement ElseClause
    #           | while Expression do Statement
    #           | ε
    # ------------------------------------------------------------------
    def _parse_statement(self) -> ASTNode:
        tok = self._current()

        # id := Expression   ou   id ()
        if tok.type == TokenType.ID:
            next_tok = self._peek(1)
            if next_tok.type == TokenType.ASSIGNOP:
                return self._parse_assign()
            elif (next_tok.type == TokenType.LPAREN and
                  self._peek(2).type == TokenType.RPAREN):
                return self._parse_proc_call()
            else:
                # Pode ser expressão isolada (não esperado na gramática),
                # mas tratamos como statement vazio com aviso.
                return EmptyStmt(line=tok.line)

        if tok.type == TokenType.BEGIN:
            return self._parse_block()

        if tok.type == TokenType.IF:
            return self._parse_if()

        if tok.type == TokenType.WHILE:
            return self._parse_while()

        # ε — statement vazio
        return EmptyStmt(line=tok.line)

    # id := Expression
    def _parse_assign(self) -> AssignStmt:
        line     = self._current().line
        name_tok = self._expect(TokenType.ID, "identificador")
        self._expect(TokenType.ASSIGNOP, ":=")
        expr = self._parse_expression()
        return AssignStmt(target=name_tok.lexeme, expression=expr, line=line)

    # id ()
    def _parse_proc_call(self) -> ProcCallStmt:
        line     = self._current().line
        name_tok = self._expect(TokenType.ID, "identificador")
        self._expect(TokenType.LPAREN, "(")
        self._expect(TokenType.RPAREN, ")")
        return ProcCallStmt(name=name_tok.lexeme, line=line)

    # if Expression then Statement ElseClause
    def _parse_if(self) -> IfStmt:
        line = self._current().line
        self._expect(TokenType.IF, "if")
        cond = self._parse_expression()
        self._expect(TokenType.THEN, "then")
        then_branch = self._parse_statement()
        else_branch = None
        if self._match(TokenType.ELSE):
            else_branch = self._parse_statement()
        return IfStmt(condition=cond, then_branch=then_branch,
                      else_branch=else_branch, line=line)

    # while Expression do Statement
    def _parse_while(self) -> WhileStmt:
        line = self._current().line
        self._expect(TokenType.WHILE, "while")
        cond = self._parse_expression()
        self._expect(TokenType.DO, "do")
        body = self._parse_statement()
        return WhileStmt(condition=cond, body=body, line=line)

    # ------------------------------------------------------------------
    # Expressões
    # ------------------------------------------------------------------
    # Expression → SimpleExpression (relop SimpleExpression)?
    def _parse_expression(self) -> ASTNode:
        line = self._current().line
        left = self._parse_simple_expression()
        if self._check(TokenType.RELOP):
            op  = self._advance()
            right = self._parse_simple_expression()
            return BinaryOp(left=left, operator=op.lexeme, right=right, line=line)
        return left

    # SimpleExpression → (addop)? Term (addop Term)*
    def _parse_simple_expression(self) -> ASTNode:
        line = self._current().line

        # addop unário
        unary_op = None
        if self._check(TokenType.ADDOP):
            unary_op = self._advance()

        node = self._parse_term()

        if unary_op:
            node = UnaryOp(operator=unary_op.lexeme, operand=node, line=line)

        while self._check(TokenType.ADDOP):
            op    = self._advance()
            right = self._parse_term()
            node  = BinaryOp(left=node, operator=op.lexeme, right=right, line=line)

        return node

    # Term → Factor (mulop Factor)*
    def _parse_term(self) -> ASTNode:
        line = self._current().line
        node = self._parse_factor()
        while self._check(TokenType.MULOP):
            op    = self._advance()
            right = self._parse_factor()
            node  = BinaryOp(left=node, operator=op.lexeme, right=right, line=line)
        return node

    # Factor → id | num | ( Expression ) | not Factor
    def _parse_factor(self) -> ASTNode:
        tok = self._current()

        if tok.type == TokenType.ID:
            self._advance()
            return Identifier(name=tok.lexeme, line=tok.line)

        if tok.type == TokenType.NUM:
            self._advance()
            return Number(value=tok.value, line=tok.line)

        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN, ")")
            return expr

        if tok.type == TokenType.NOT:
            line = tok.line
            self._advance()
            operand = self._parse_factor()
            return UnaryOp(operator="not", operand=operand, line=line)

        raise ParseError("Fator esperado (id, número, '(' ou 'not')", tok)
