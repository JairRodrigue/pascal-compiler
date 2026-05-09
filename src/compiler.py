"""
=============================================================================
COMPILADOR — Ponto de Entrada Principal
=============================================================================
Orquestra todas as fases do compilador:

  1. Análise Léxica   (Lexer)
  2. Análise Sintática (Parser)  → AST
  3. Verificação de Tipos        → Tabela de Símbolos preenchida
  4. Geração de Código Intermediário (TAC)

Uso via linha de comando:
  python compiler.py <arquivo.pas>          # compila arquivo
  python compiler.py --example             # compila o exemplo embutido
  python compiler.py --tokens <arquivo.pas> # imprime apenas tokens
  python compiler.py --ast   <arquivo.pas>  # imprime apenas a AST
  python compiler.py --help                # ajuda
=============================================================================
"""

import sys
import os
import argparse
from pathlib import Path

# Adiciona src/ ao path para imports relativos
sys.path.insert(0, os.path.dirname(__file__))

from lexer      import Lexer,        LexerError
from parser     import Parser,       ParseError
from ast_nodes  import ASTPrinter
from type_checker import TypeChecker
from symbol_table import SemanticError
from codegen    import CodeGenerator


# ---------------------------------------------------------------------------
# Programa de exemplo do projeto (do arquivo exemplo_pas.pdf)
# ---------------------------------------------------------------------------
EXEMPLO_BUILTIN = """\
program exemplo;
var
  x, y : integer;
  z    : real;

procedure teste;
var
  a : integer;
begin
  a := 10;
  if a > 5 then
    x := a
  else
    x := 0
end;

begin
  x := 1;
  y := 2;
  z := 3.5;
  teste();
  while x < y do
  begin
    x := x + 1
  end
end.
"""


# ---------------------------------------------------------------------------
# Resultado da compilação
# ---------------------------------------------------------------------------
class CompileResult:
    def __init__(self):
        self.tokens       = None
        self.ast          = None
        self.symbol_table = None
        self.tac          = None
        self.errors: list[str] = []
        self.success: bool = False


# ---------------------------------------------------------------------------
# Compilador
# ---------------------------------------------------------------------------
class Compiler:
    """
    Orquestra todas as fases.
    Uso:
        result = Compiler().compile(source_code)
    """

    def compile(self, source: str,
                verbose: bool = False) -> CompileResult:
        result = CompileResult()

        # ── Fase 1: Análise Léxica ──────────────────────────────────────
        self._phase("Análise Léxica", verbose)
        try:
            lexer = Lexer(source)
            tokens = lexer.tokenize()
            result.tokens = tokens
            if verbose:
                print(f"  {len(tokens)} tokens gerados.")
        except LexerError as e:
            result.errors.append(str(e))
            return result

        # ── Fase 2: Análise Sintática ───────────────────────────────────
        self._phase("Análise Sintática", verbose)
        try:
            parser = Parser(tokens)
            ast = parser.parse()
            result.ast = ast
            if verbose:
                print("  AST construída com sucesso.")
        except ParseError as e:
            result.errors.append(str(e))
            return result

        # ── Fase 3: Verificação de Tipos ────────────────────────────────
        self._phase("Verificação de Tipos", verbose)
        try:
            checker = TypeChecker()
            table = checker.check(ast)
            result.symbol_table = table
            if verbose:
                print(f"  Tabela de símbolos: "
                      f"{len(table.all_symbols())} símbolo(s) registrado(s).")
        except SemanticError as e:
            result.errors.append(str(e))
            return result

        # ── Fase 4: Geração de Código Intermediário ─────────────────────
        self._phase("Geração de Código Intermediário", verbose)
        try:
            gen = CodeGenerator()
            instrs = gen.generate(ast)
            result.tac = gen
            if verbose:
                print(f"  {len(instrs)} instrução(ões) TAC gerada(s).")
        except Exception as e:
            result.errors.append(f"[CodeGen] {e}")
            return result

        result.success = True
        return result

    def _phase(self, name: str, verbose: bool):
        if verbose:
            print(f"\n{'─'*50}")
            print(f"  {name}")
            print(f"{'─'*50}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        prog="compiler.py",
        description="Compilador para subconjunto de Pascal — Projeto Final"
    )
    ap.add_argument("arquivo", nargs="?",
                    help="Arquivo .pas a compilar")
    ap.add_argument("--example", action="store_true",
                    help="Compila o programa de exemplo embutido")
    ap.add_argument("--tokens", action="store_true",
                    help="Imprime apenas a lista de tokens e encerra")
    ap.add_argument("--ast",    action="store_true",
                    help="Imprime apenas a AST e encerra")
    ap.add_argument("--symbols",action="store_true",
                    help="Imprime apenas a tabela de símbolos e encerra")
    ap.add_argument("--tac",    action="store_true",
                    help="Imprime apenas o código intermediário e encerra")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="Modo verboso: exibe todas as fases")

    args = ap.parse_args()

    # ── Fonte ──────────────────────────────────────────────────────────
    if args.example:
        source = EXEMPLO_BUILTIN
        filename = "<exemplo embutido>"
    elif args.arquivo:
        path = Path(args.arquivo)
        if not path.exists():
            print(f"Erro: arquivo '{args.arquivo}' não encontrado.")
            sys.exit(1)
        source   = path.read_text(encoding="utf-8")
        filename = str(path)
    else:
        ap.print_help()
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"  Pascal Subset Compiler")
    print(f"  Fonte: {filename}")
    print(f"{'='*60}")

    # ── Compilar ───────────────────────────────────────────────────────
    compiler = Compiler()
    result   = compiler.compile(source, verbose=args.verbose)

    # ── Relatório de erros ─────────────────────────────────────────────
    if result.errors:
        print("\n❌  ERROS DE COMPILAÇÃO:")
        for err in result.errors:
            print(f"   {err}")
        sys.exit(1)

    # ── Saídas opcionais ───────────────────────────────────────────────
    if args.tokens or (not args.ast and not args.symbols and not args.tac
                       and not args.verbose):
        print("\n── TOKENS ──────────────────────────────────────────────")
        for tok in result.tokens:
            print(f"  {tok}")

    if args.ast:
        print("\n── ÁRVORE SINTÁTICA ABSTRATA (AST) ─────────────────────")
        printer = ASTPrinter()
        result.ast.accept(printer)
        print(printer.result())

    if args.symbols:
        print("\n── TABELA DE SÍMBOLOS ───────────────────────────────────")
        print(result.symbol_table.dump())

    if args.tac:
        print("\n── CÓDIGO INTERMEDIÁRIO (TAC) ───────────────────────────")
        print(result.tac.pretty_print())

    # ── Se verbose, imprime tudo ───────────────────────────────────────
    if args.verbose:
        print("\n── TOKENS ──────────────────────────────────────────────")
        for tok in result.tokens:
            print(f"  {tok}")

        print("\n── ÁRVORE SINTÁTICA ABSTRATA (AST) ─────────────────────")
        printer = ASTPrinter()
        result.ast.accept(printer)
        print(printer.result())

        print("\n── TABELA DE SÍMBOLOS ───────────────────────────────────")
        print(result.symbol_table.dump())

        print("\n── CÓDIGO INTERMEDIÁRIO (TAC) ───────────────────────────")
        print(result.tac.pretty_print())

    print(f"\n✅  Compilação concluída com sucesso!")


if __name__ == "__main__":
    main()
