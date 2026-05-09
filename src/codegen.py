"""
=============================================================================
GERADOR DE CÓDIGO INTERMEDIÁRIO — Pascal Subset Compiler
=============================================================================
Produz código de três endereços (Three-Address Code / TAC) a partir da AST.

Formato das instruções TAC:
  t1 := t2 op t3       # operação binária
  t1 := op t2          # operação unária
  t1 := t2             # cópia simples
  goto L               # salto incondicional
  if t goto L          # salto condicional (true)
  ifFalse t goto L     # salto condicional (false)
  param t              # passagem de parâmetro
  call p, n            # chamada de procedimento p com n argumentos
  label L:             # rótulo

Cada instrução é representada pela classe TACInstr.
O gerador mantém:
  - um contador de temporários (t1, t2, …)
  - um contador de rótulos (L1, L2, …)
  - uma lista linear de instruções produzidas
=============================================================================
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
from ast_nodes import (
    ASTVisitor, ASTNode,
    Program, Header, Declarations, VariableDeclaration,
    ProcedureDeclaration, Block, AssignStmt, ProcCallStmt,
    IfStmt, WhileStmt, EmptyStmt, BinaryOp, UnaryOp,
    Identifier, Number
)


# ---------------------------------------------------------------------------
# Instrução TAC
# ---------------------------------------------------------------------------
@dataclass
class TACInstr:
    """
    Representa uma instrução de código de três endereços.

    Campos:
      op      : operação ("assign", "binop", "unop", "goto", "if", "ifFalse",
                           "label", "call", "begin_proc", "end_proc")
      result  : destino (temporário ou variável)
      arg1    : primeiro argumento
      arg2    : segundo argumento (opcional)
    """
    op:     str
    result: Optional[str] = None
    arg1:   Optional[str] = None
    arg2:   Optional[str] = None

    def __str__(self) -> str:
        match self.op:
            case "label":
                return f"{self.result}:"
            case "assign":
                return f"    {self.result} := {self.arg1}"
            case "binop":
                return f"    {self.result} := {self.arg1} {self.arg2} ?"
                # arg2 será formatado no gerador
            case "goto":
                return f"    goto {self.result}"
            case "if":
                return f"    if {self.arg1} goto {self.result}"
            case "ifFalse":
                return f"    ifFalse {self.arg1} goto {self.result}"
            case "call":
                return f"    call {self.result}, {self.arg1}"
            case "begin_proc":
                return f"\n[proc {self.result}]"
            case "end_proc":
                return f"[end proc {self.result}]"
            case _:
                parts = [f"    {self.op}"]
                if self.result: parts.append(self.result)
                if self.arg1:   parts.append(self.arg1)
                if self.arg2:   parts.append(self.arg2)
                return " ".join(parts)


# ---------------------------------------------------------------------------
# Gerador de Código Intermediário
# ---------------------------------------------------------------------------
class CodeGenerator(ASTVisitor):
    """
    Percorre a AST e emite instrucões TAC.

    Uso:
        gen   = CodeGenerator()
        instrs = gen.generate(ast)
        print(gen.pretty_print())
    """

    def __init__(self):
        self._instructions: List[TACInstr] = []
        self._temp_count  = 0
        self._label_count = 0

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------
    def generate(self, node: Program) -> List[TACInstr]:
        node.accept(self)
        return self._instructions

    def pretty_print(self) -> str:
        lines = ["=== Código Intermediário (TAC) ===\n"]
        for instr in self._instructions:
            lines.append(str(instr))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Geração de temporários e rótulos
    # ------------------------------------------------------------------
    def _new_temp(self) -> str:
        self._temp_count += 1
        return f"t{self._temp_count}"

    def _new_label(self) -> str:
        self._label_count += 1
        return f"L{self._label_count}"

    def _emit(self, instr: TACInstr):
        self._instructions.append(instr)

    # ------------------------------------------------------------------
    # Atalhos de emissão
    # ------------------------------------------------------------------
    def _emit_label(self, label: str):
        self._emit(TACInstr(op="label", result=label))

    def _emit_assign(self, dst: str, src: str):
        self._emit(TACInstr(op="assign", result=dst, arg1=src))

    def _emit_binop(self, dst: str, left: str, op: str, right: str):
        self._emit(TACInstr(op="assign", result=dst,
                            arg1=f"{left} {op} {right}"))

    def _emit_unop(self, dst: str, op: str, src: str):
        self._emit(TACInstr(op="assign", result=dst, arg1=f"{op} {src}"))

    def _emit_goto(self, label: str):
        self._emit(TACInstr(op="goto", result=label))

    def _emit_if_false(self, cond: str, label: str):
        self._emit(TACInstr(op="ifFalse", result=label, arg1=cond))

    def _emit_if_true(self, cond: str, label: str):
        self._emit(TACInstr(op="if", result=label, arg1=cond))

    # ------------------------------------------------------------------
    # Visitores estruturais
    # ------------------------------------------------------------------
    def visit_Program(self, node: Program):
        # Emite declarações de procedimentos primeiro
        for proc in node.declarations.procedures:
            proc.accept(self)
        # Corpo principal
        self._emit(TACInstr(op="begin_proc", result="__main__"))
        node.block.accept(self)
        self._emit(TACInstr(op="end_proc", result="__main__"))

    def visit_Header(self, node): pass

    def visit_Declarations(self, node: Declarations):
        # Variáveis são apenas anotações; não geram instrução TAC aqui.
        # Procedimentos visitados do visit_Program.
        pass

    def visit_VariableDeclaration(self, node): pass

    def visit_ProcedureDeclaration(self, node: ProcedureDeclaration):
        self._emit(TACInstr(op="begin_proc", result=node.name.lower()))
        # Variáveis locais do procedimento — apenas comentário implícito
        node.block.accept(self)
        self._emit(TACInstr(op="end_proc", result=node.name.lower()))

    def visit_Block(self, node: Block):
        for stmt in node.statements:
            stmt.accept(self)

    # ------------------------------------------------------------------
    # Visitores de statements
    # ------------------------------------------------------------------
    def visit_AssignStmt(self, node: AssignStmt) -> None:
        src = self._visit_expr(node.expression)
        self._emit_assign(node.target.lower(), src)

    def visit_ProcCallStmt(self, node: ProcCallStmt) -> None:
        self._emit(TACInstr(op="call", result=node.name.lower(), arg1="0"))

    def visit_IfStmt(self, node: IfStmt) -> None:
        """
        if cond then S1 else S2

        TAC:
            cond → t
            ifFalse t goto L_else
            < then branch >
            goto L_end
          L_else:
            < else branch >
          L_end:
        """
        cond_tmp  = self._visit_expr(node.condition)
        l_else    = self._new_label()
        l_end     = self._new_label()

        self._emit_if_false(cond_tmp, l_else)
        node.then_branch.accept(self)
        self._emit_goto(l_end)
        self._emit_label(l_else)
        if node.else_branch:
            node.else_branch.accept(self)
        self._emit_label(l_end)

    def visit_WhileStmt(self, node: WhileStmt) -> None:
        """
        while cond do S

        TAC:
          L_begin:
            cond → t
            ifFalse t goto L_end
            < body >
            goto L_begin
          L_end:
        """
        l_begin = self._new_label()
        l_end   = self._new_label()

        self._emit_label(l_begin)
        cond_tmp = self._visit_expr(node.condition)
        self._emit_if_false(cond_tmp, l_end)
        node.body.accept(self)
        self._emit_goto(l_begin)
        self._emit_label(l_end)

    def visit_EmptyStmt(self, node): pass

    # ------------------------------------------------------------------
    # Visitores de expressões — retornam o nome do temporário resultante
    # ------------------------------------------------------------------
    def _visit_expr(self, node: ASTNode) -> str:
        """Visita uma expressão e retorna o temporário com o resultado."""
        return node.accept(self)

    def visit_BinaryOp(self, node: BinaryOp) -> str:
        left  = self._visit_expr(node.left)
        right = self._visit_expr(node.right)
        tmp   = self._new_temp()
        self._emit_binop(tmp, left, node.operator, right)
        return tmp

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        operand = self._visit_expr(node.operand)
        tmp     = self._new_temp()
        self._emit_unop(tmp, node.operator, operand)
        return tmp

    def visit_Identifier(self, node: Identifier) -> str:
        return node.name.lower()

    def visit_Number(self, node: Number) -> str:
        # Número literal — copia para temporário para uniformidade
        tmp = self._new_temp()
        self._emit_assign(tmp, str(node.value))
        return tmp
