"""
=============================================================================
NÓS DA AST (Árvore Sintática Abstrata) — Pascal Subset Compiler
=============================================================================
"""

from __future__ import annotations
from typing import Optional, List


class ASTNode:
    line: int = 0

    def accept(self, visitor):
        method_name = "visit_" + type(self).__name__
        method = getattr(visitor, method_name, visitor.generic_visit)
        return method(self)


class Program(ASTNode):
    def __init__(self, header, declarations, block, line=0):
        self.header = header; self.declarations = declarations
        self.block = block;   self.line = line


class Header(ASTNode):
    def __init__(self, name: str, line: int = 0):
        self.name = name; self.line = line


class Declarations(ASTNode):
    def __init__(self, var_section=None, procedures=None, line: int = 0):
        self.var_section = var_section or []; self.procedures = procedures or []
        self.line = line


class VariableDeclaration(ASTNode):
    def __init__(self, identifiers: List[str], var_type: str, line: int = 0):
        self.identifiers = identifiers; self.var_type = var_type; self.line = line


class ProcedureDeclaration(ASTNode):
    def __init__(self, name: str, declarations, block, line: int = 0):
        self.name = name; self.declarations = declarations
        self.block = block; self.line = line


class Block(ASTNode):
    def __init__(self, statements=None, line: int = 0):
        self.statements = statements or []; self.line = line


class AssignStmt(ASTNode):
    def __init__(self, target: str, expression, line: int = 0):
        self.target = target; self.expression = expression; self.line = line


class ProcCallStmt(ASTNode):
    def __init__(self, name: str, line: int = 0):
        self.name = name; self.line = line


class IfStmt(ASTNode):
    def __init__(self, condition, then_branch, else_branch=None, line: int = 0):
        self.condition = condition; self.then_branch = then_branch
        self.else_branch = else_branch; self.line = line


class WhileStmt(ASTNode):
    def __init__(self, condition, body, line: int = 0):
        self.condition = condition; self.body = body; self.line = line


class EmptyStmt(ASTNode):
    def __init__(self, line: int = 0):
        self.line = line


class BinaryOp(ASTNode):
    def __init__(self, left, operator: str, right, line: int = 0):
        self.left = left; self.operator = operator; self.right = right
        self.line = line; self.inferred_type = ""


class UnaryOp(ASTNode):
    def __init__(self, operator: str, operand, line: int = 0):
        self.operator = operator; self.operand = operand
        self.line = line; self.inferred_type = ""


class Identifier(ASTNode):
    def __init__(self, name: str, line: int = 0):
        self.name = name; self.line = line; self.inferred_type = ""


class Number(ASTNode):
    def __init__(self, value, line: int = 0):
        self.value = value; self.line = line
        self.inferred_type = "real" if isinstance(value, float) else "integer"


class ASTVisitor:
    def generic_visit(self, node):
        raise NotImplementedError(f"Visitor não implementa visit_{type(node).__name__}")

    def visit_Program(self, node): pass
    def visit_Header(self, node): pass
    def visit_Declarations(self, node): pass
    def visit_VariableDeclaration(self, node): pass
    def visit_ProcedureDeclaration(self, node): pass
    def visit_Block(self, node): pass
    def visit_AssignStmt(self, node): pass
    def visit_ProcCallStmt(self, node): pass
    def visit_IfStmt(self, node): pass
    def visit_WhileStmt(self, node): pass
    def visit_EmptyStmt(self, node): pass
    def visit_BinaryOp(self, node): pass
    def visit_UnaryOp(self, node): pass
    def visit_Identifier(self, node): pass
    def visit_Number(self, node): pass


class ASTPrinter(ASTVisitor):
    def __init__(self):
        self._indent = 0; self._lines = []

    def _w(self, text):
        self._lines.append("  " * self._indent + text)

    def result(self):
        return "\n".join(self._lines)

    def visit_Program(self, node):
        self._w(f"Program (linha {node.line})")
        self._indent += 1
        node.header.accept(self); node.declarations.accept(self); node.block.accept(self)
        self._indent -= 1

    def visit_Header(self, node):
        self._w(f"Header: {node.name}")

    def visit_Declarations(self, node):
        self._w("Declarations")
        self._indent += 1
        for v in node.var_section: v.accept(self)
        for p in node.procedures:  p.accept(self)
        self._indent -= 1

    def visit_VariableDeclaration(self, node):
        self._w(f"VarDecl: {', '.join(node.identifiers)} : {node.var_type}")

    def visit_ProcedureDeclaration(self, node):
        self._w(f"Procedure: {node.name}")
        self._indent += 1
        node.declarations.accept(self); node.block.accept(self)
        self._indent -= 1

    def visit_Block(self, node):
        self._w("Block")
        self._indent += 1
        for s in node.statements: s.accept(self)
        self._indent -= 1

    def visit_AssignStmt(self, node):
        self._w(f"Assign: {node.target} :=")
        self._indent += 1; node.expression.accept(self); self._indent -= 1

    def visit_ProcCallStmt(self, node):
        self._w(f"ProcCall: {node.name}()")

    def visit_IfStmt(self, node):
        self._w("If")
        self._indent += 1
        self._w("Condition:"); self._indent += 1; node.condition.accept(self); self._indent -= 1
        self._w("Then:");     self._indent += 1; node.then_branch.accept(self); self._indent -= 1
        if node.else_branch:
            self._w("Else:"); self._indent += 1; node.else_branch.accept(self); self._indent -= 1
        self._indent -= 1

    def visit_WhileStmt(self, node):
        self._w("While")
        self._indent += 1
        self._w("Condition:"); self._indent += 1; node.condition.accept(self); self._indent -= 1
        self._w("Body:");      self._indent += 1; node.body.accept(self);      self._indent -= 1
        self._indent -= 1

    def visit_EmptyStmt(self, node): self._w("EmptyStmt")

    def visit_BinaryOp(self, node):
        self._w(f"BinaryOp: '{node.operator}'")
        self._indent += 1; node.left.accept(self); node.right.accept(self); self._indent -= 1

    def visit_UnaryOp(self, node):
        self._w(f"UnaryOp: '{node.operator}'")
        self._indent += 1; node.operand.accept(self); self._indent -= 1

    def visit_Identifier(self, node):
        self._w(f"Id: {node.name}  [{node.inferred_type or '?'}]")

    def visit_Number(self, node):
        self._w(f"Num: {node.value}  [{node.inferred_type}]")
