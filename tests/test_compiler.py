"""
=============================================================================
TESTES — Pascal Subset Compiler
=============================================================================
Suite de testes unitários e de integração cobrindo:
  - Analisador léxico
  - Analisador sintático
  - Verificador de tipos
  - Gerador de código intermediário
  - Erros esperados (testa que erros corretos são lançados)

Execute com:
  python tests/test_compiler.py
ou com pytest:
  pytest tests/test_compiler.py -v
=============================================================================
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer        import Lexer,  LexerError, TokenType
from parser       import Parser, ParseError
from ast_nodes    import ASTPrinter
from type_checker import TypeChecker
from symbol_table import SemanticError
from codegen      import CodeGenerator
from compiler     import Compiler, EXEMPLO_BUILTIN


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários
# ─────────────────────────────────────────────────────────────────────────────
def compile_ok(source: str):
    """Compila e garante que não houve erro. Retorna CompileResult."""
    result = Compiler().compile(source)
    if not result.success:
        raise AssertionError("Compilação falhou:\n" + "\n".join(result.errors))
    return result


def compile_err(source: str) -> str:
    """Compila e garante que houve erro. Retorna a mensagem."""
    result = Compiler().compile(source)
    if result.success:
        raise AssertionError("Era esperado um erro, mas a compilação teve sucesso.")
    return "\n".join(result.errors)


# ─────────────────────────────────────────────────────────────────────────────
# Testes do Lexer
# ─────────────────────────────────────────────────────────────────────────────
class TestLexer(unittest.TestCase):

    def _tokens(self, source: str):
        return Lexer(source).tokenize()

    def test_identifiers(self):
        toks = self._tokens("hello world123")
        self.assertEqual(toks[0].type, TokenType.ID)
        self.assertEqual(toks[0].lexeme, "hello")
        self.assertEqual(toks[1].type, TokenType.ID)
        self.assertEqual(toks[1].lexeme, "world123")

    def test_reserved_words(self):
        src  = "program var procedure begin end if then else while do integer real not"
        toks = self._tokens(src)
        expected = [
            TokenType.PROGRAM, TokenType.VAR, TokenType.PROCEDURE,
            TokenType.BEGIN,   TokenType.END, TokenType.IF,
            TokenType.THEN,    TokenType.ELSE,TokenType.WHILE,
            TokenType.DO,      TokenType.INTEGER, TokenType.REAL,
            TokenType.NOT,     TokenType.EOF
        ]
        types = [t.type for t in toks]
        self.assertEqual(types, expected)

    def test_integers(self):
        toks = self._tokens("42 0 1234")
        self.assertEqual(toks[0].value, 42)
        self.assertEqual(toks[1].value, 0)
        self.assertEqual(toks[2].value, 1234)
        for t in toks[:3]:
            self.assertIsInstance(t.value, int)

    def test_real_numbers(self):
        toks = self._tokens("3.14 2.0 1E5 1.5e-3")
        for t in toks[:4]:
            self.assertIsInstance(t.value, float)
        self.assertAlmostEqual(toks[0].value, 3.14)
        self.assertAlmostEqual(toks[2].value, 1e5)

    def test_operators(self):
        src  = ":= = <> <= >= < >"
        toks = self._tokens(src)
        self.assertEqual(toks[0].type, TokenType.ASSIGNOP)
        self.assertEqual(toks[1].type, TokenType.RELOP)
        for t in toks[2:7]:
            self.assertEqual(t.type, TokenType.RELOP)

    def test_addops_mulops(self):
        toks = self._tokens("+ - or * / div mod and")
        addops = [t for t in toks if t.type == TokenType.ADDOP]
        mulops = [t for t in toks if t.type == TokenType.MULOP]
        self.assertEqual(len(addops), 3)  # + - or
        self.assertEqual(len(mulops), 5)  # * / div mod and

    def test_comment_skipped(self):
        toks = self._tokens("{ isto é um comentário } x")
        self.assertEqual(toks[0].type, TokenType.ID)
        self.assertEqual(toks[0].lexeme, "x")

    def test_multiline_comment(self):
        toks = self._tokens("{ linha1\nlinha2\nlinha3 } y")
        self.assertEqual(toks[0].type, TokenType.ID)

    def test_unclosed_comment_error(self):
        with self.assertRaises(LexerError):
            self._tokens("{ comentário sem fechar")

    def test_unexpected_char_error(self):
        with self.assertRaises(LexerError):
            self._tokens("x @ y")

    def test_line_tracking(self):
        toks = self._tokens("x\ny\nz")
        self.assertEqual(toks[0].line, 1)
        self.assertEqual(toks[1].line, 2)
        self.assertEqual(toks[2].line, 3)

    def test_case_insensitive_keywords(self):
        toks = self._tokens("BEGIN END IF")
        self.assertEqual(toks[0].type, TokenType.BEGIN)
        self.assertEqual(toks[1].type, TokenType.END)
        self.assertEqual(toks[2].type, TokenType.IF)


# ─────────────────────────────────────────────────────────────────────────────
# Testes do Parser
# ─────────────────────────────────────────────────────────────────────────────
class TestParser(unittest.TestCase):

    def _parse(self, src: str):
        tokens = Lexer(src).tokenize()
        return Parser(tokens).parse()

    def test_minimal_program(self):
        ast = self._parse("program p; begin end.")
        self.assertEqual(ast.header.name, "p")
        self.assertEqual(len(ast.block.statements), 1)  # EmptyStmt

    def test_var_declaration(self):
        ast = self._parse("program p; var x, y: integer; begin end.")
        self.assertEqual(len(ast.declarations.var_section), 1)
        decl = ast.declarations.var_section[0]
        self.assertIn("x", decl.identifiers)
        self.assertIn("y", decl.identifiers)
        self.assertEqual(decl.var_type, "integer")

    def test_procedure_declaration(self):
        src = """
        program p;
        procedure foo;
        begin end;
        begin end.
        """
        ast = self._parse(src)
        self.assertEqual(len(ast.declarations.procedures), 1)
        self.assertEqual(ast.declarations.procedures[0].name, "foo")

    def test_assign_statement(self):
        from ast_nodes import AssignStmt, Number
        ast = self._parse("program p; var x: integer; begin x := 42 end.")
        stmts = ast.block.statements
        assign = stmts[0]
        self.assertIsInstance(assign, AssignStmt)
        self.assertEqual(assign.target, "x")
        self.assertIsInstance(assign.expression, Number)
        self.assertEqual(assign.expression.value, 42)

    def test_if_else(self):
        from ast_nodes import IfStmt
        src = "program p; var x: integer; begin if x > 0 then x := 1 else x := 0 end."
        ast = self._parse(src)
        stmt = ast.block.statements[0]
        self.assertIsInstance(stmt, IfStmt)
        self.assertIsNotNone(stmt.else_branch)

    def test_while(self):
        from ast_nodes import WhileStmt
        src = "program p; var x: integer; begin while x > 0 do x := x - 1 end."
        ast = self._parse(src)
        stmt = ast.block.statements[0]
        self.assertIsInstance(stmt, WhileStmt)

    def test_nested_expression(self):
        from ast_nodes import BinaryOp
        src = "program p; var x: integer; begin x := (1 + 2) * 3 end."
        ast = self._parse(src)
        expr = ast.block.statements[0].expression
        self.assertIsInstance(expr, BinaryOp)
        self.assertEqual(expr.operator, "*")

    def test_missing_dot_error(self):
        with self.assertRaises(ParseError):
            self._parse("program p; begin end")

    def test_missing_semicolon_after_header(self):
        with self.assertRaises(ParseError):
            self._parse("program p begin end.")

    def test_proc_call(self):
        from ast_nodes import ProcCallStmt
        src = """
        program p;
        procedure foo; begin end;
        begin foo() end.
        """
        ast = self._parse(src)
        stmt = ast.block.statements[0]
        self.assertIsInstance(stmt, ProcCallStmt)
        self.assertEqual(stmt.name, "foo")


# ─────────────────────────────────────────────────────────────────────────────
# Testes do Type Checker
# ─────────────────────────────────────────────────────────────────────────────
class TestTypeChecker(unittest.TestCase):

    def _check(self, src: str):
        tokens = Lexer(src).tokenize()
        ast    = Parser(tokens).parse()
        return TypeChecker().check(ast)

    def test_variable_in_table(self):
        table = self._check("program p; var x: integer; begin end.")
        sym = table.lookup("x")
        self.assertIsNotNone(sym)
        self.assertEqual(sym.data_type, "integer")

    def test_real_variable(self):
        table = self._check("program p; var r: real; begin end.")
        sym = table.lookup("r")
        self.assertEqual(sym.data_type, "real")

    def test_procedure_in_table(self):
        src = "program p; procedure foo; begin end; begin end."
        table = self._check(src)
        sym = table.lookup("foo")
        self.assertIsNotNone(sym)
        from symbol_table import SymbolKind
        self.assertEqual(sym.kind, SymbolKind.PROCEDURE)

    def test_undeclared_variable_error(self):
        with self.assertRaises(SemanticError):
            self._check("program p; begin x := 1 end.")

    def test_redeclaration_error(self):
        with self.assertRaises(SemanticError):
            self._check("program p; var x: integer; x: real; begin end.")

    def test_real_to_integer_assignment_error(self):
        with self.assertRaises(SemanticError):
            self._check("""
                program p;
                var
                  i : integer;
                  r : real;
                begin
                  r := 3.14;
                  i := r
                end.
            """)

    def test_integer_to_real_ok(self):
        # Não deve lançar erro
        self._check("""
            program p;
            var
              i : integer;
              r : real;
            begin
              i := 5;
              r := i
            end.
        """)

    def test_call_variable_as_proc_error(self):
        with self.assertRaises(SemanticError):
            self._check("""
                program p;
                var x: integer;
                begin x() end.
            """)

    def test_type_promotion_in_expr(self):
        from ast_nodes import BinaryOp
        src = """
            program p;
            var i: integer; r: real;
            begin r := i + r end.
        """
        # Deve compilar sem erro
        table = self._check(src)
        self.assertIsNotNone(table.lookup("r"))


# ─────────────────────────────────────────────────────────────────────────────
# Testes do Gerador de Código
# ─────────────────────────────────────────────────────────────────────────────
class TestCodeGen(unittest.TestCase):

    def _gen(self, src: str) -> list:
        tokens = Lexer(src).tokenize()
        ast    = Parser(tokens).parse()
        TypeChecker().check(ast)
        gen = CodeGenerator()
        gen.generate(ast)
        return gen._instructions

    def test_assign_generates_instructions(self):
        instrs = self._gen("program p; var x: integer; begin x := 42 end.")
        # Deve conter ao menos um assign
        ops = [i.op for i in instrs]
        self.assertIn("assign", ops)

    def test_if_generates_labels(self):
        instrs = self._gen("""
            program p; var x: integer;
            begin if x > 0 then x := 1 else x := 0 end.
        """)
        labels = [i.result for i in instrs if i.op == "label"]
        self.assertGreaterEqual(len(labels), 2)

    def test_while_generates_goto(self):
        instrs = self._gen("""
            program p; var x: integer;
            begin while x > 0 do x := x - 1 end.
        """)
        gotos = [i for i in instrs if i.op == "goto"]
        self.assertGreaterEqual(len(gotos), 1)

    def test_proc_begin_end_markers(self):
        instrs = self._gen("""
            program p;
            procedure foo; begin end;
            begin foo() end.
        """)
        ops = [i.op for i in instrs]
        self.assertIn("begin_proc", ops)
        self.assertIn("end_proc", ops)

    def test_proc_call_instruction(self):
        instrs = self._gen("""
            program p;
            procedure foo; begin end;
            begin foo() end.
        """)
        calls = [i for i in instrs if i.op == "call"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].result, "foo")


# ─────────────────────────────────────────────────────────────────────────────
# Teste de integração — exemplo do PDF
# ─────────────────────────────────────────────────────────────────────────────
class TestIntegration(unittest.TestCase):

    def test_exemplo_builtin(self):
        """Compila o programa exemplo_pas.pdf sem erros."""
        result = compile_ok(EXEMPLO_BUILTIN)
        self.assertTrue(result.success)

    def test_exemplo_symbol_table(self):
        result = compile_ok(EXEMPLO_BUILTIN)
        table  = result.symbol_table
        # Variáveis globais
        self.assertIsNotNone(table.lookup("x"))
        self.assertIsNotNone(table.lookup("y"))
        self.assertIsNotNone(table.lookup("z"))
        # Procedimento
        self.assertIsNotNone(table.lookup("teste"))
        # Variável local do procedimento (está no escopo fechado do procedure)
        # O type checker fecha o escopo ao terminar — verificamos via lookup global
        # que x, y, z e teste existem no escopo global
        self.assertIsNotNone(table.lookup("x"))

    def test_exemplo_tac_not_empty(self):
        result = compile_ok(EXEMPLO_BUILTIN)
        self.assertGreater(len(result.tac._instructions), 0)

    def test_empty_program(self):
        result = compile_ok("program vazio; begin end.")
        self.assertTrue(result.success)

    def test_multiple_procedures(self):
        src = """
        program multi;
        var n: integer;
        procedure p1; begin n := 1 end;
        procedure p2; begin n := 2 end;
        begin p1(); p2() end.
        """
        result = compile_ok(src)
        self.assertTrue(result.success)

    def test_nested_if_while(self):
        src = """
        program nested;
        var i, j: integer;
        begin
          i := 0;
          while i < 10 do
          begin
            if i > 5 then
              j := i
            else
              j := 0;
            i := i + 1
          end
        end.
        """
        result = compile_ok(src)
        self.assertTrue(result.success)

    def test_comments_ignored(self):
        src = """
        { Este é um comentário }
        program comentarios;
        { Outro comentário }
        var x: integer; { inline }
        begin
          x := 1 { atribuição }
        end.
        """
        result = compile_ok(src)
        self.assertTrue(result.success)

    def test_not_operator(self):
        src = """
        program nottest;
        var x: integer;
        begin
          x := 0;
          if not x > 0 then
            x := 1
        end.
        """
        result = compile_ok(src)
        self.assertTrue(result.success)


# ─────────────────────────────────────────────────────────────────────────────
# Ponto de entrada
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Pascal Subset Compiler — Suite de Testes")
    print("=" * 60)
    unittest.main(verbosity=2)
