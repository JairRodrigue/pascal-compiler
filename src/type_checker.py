"""
=============================================================================
VERIFICADOR DE TIPOS (TYPE CHECKER) — Pascal Subset Compiler
=============================================================================
Percorre a AST produzida pelo parser e realiza:

  1. População da tabela de símbolos com todas as declarações
     (variáveis e procedimentos), detectando redeclarações.
  2. Verificação de uso de identificadores — garante que toda variável
     referenciada foi previamente declarada.
  3. Inferência de tipos nas expressões:
       - integer op integer → integer
       - real    op real    → real
       - integer op real    → real  (promoção implícita)
       - relop              → boolean (representado como "integer" nesta
                             implementação simplificada)
       - NOT                → mesmo tipo do operando
  4. Verificação de compatibilidade de tipos em atribuições:
       - integer → integer  OK
       - real    → real     OK
       - integer → real     OK  (promoção)
       - real    → integer  ERRO
  5. Verificação de chamadas de procedimento (id declarado como procedure).

Ao final, o type checker retorna a tabela de símbolos preenchida e a AST
com os campos inferred_type preenchidos.
=============================================================================
"""

from ast_nodes import (
    ASTVisitor, ASTNode,
    Program, Header, Declarations, VariableDeclaration,
    ProcedureDeclaration, Block, AssignStmt, ProcCallStmt,
    IfStmt, WhileStmt, EmptyStmt, BinaryOp, UnaryOp,
    Identifier, Number
)
from symbol_table import SymbolTable, Symbol, SymbolKind, DataType, SemanticError


# ---------------------------------------------------------------------------
# Regras de tipo
# ---------------------------------------------------------------------------
def _result_type(t1: str, t2: str) -> str:
    """Promoção implícita: se um dos tipos for real, o resultado é real."""
    if t1 == DataType.REAL or t2 == DataType.REAL:
        return DataType.REAL
    return DataType.INTEGER


def _compatible_assign(src: str, dst: str) -> bool:
    """
    Compatibilidade de atribuição:
      integer → integer  ✓
      integer → real     ✓  (promoção)
      real    → real     ✓
      real    → integer  ✗
    """
    if src == dst:
        return True
    if src == DataType.INTEGER and dst == DataType.REAL:
        return True
    return False


# ---------------------------------------------------------------------------
# Verificador de tipos
# ---------------------------------------------------------------------------
class TypeChecker(ASTVisitor):
    """
    Uso:
        checker = TypeChecker()
        checker.check(ast)         # lança SemanticError em caso de problema
        table   = checker.table    # tabela de símbolos preenchida
    """

    def __init__(self):
        self.table = SymbolTable()
        self._errors: list[str] = []

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------
    def check(self, node: Program) -> SymbolTable:
        """
        Ponto de entrada. Lança SemanticError no primeiro erro encontrado.
        Retorna a tabela de símbolos preenchida.
        """
        node.accept(self)
        return self.table

    def _error(self, msg: str, line: int = 0):
        raise SemanticError(msg, line)

    # ------------------------------------------------------------------
    # Visitas estruturais
    # ------------------------------------------------------------------
    def visit_Program(self, node: Program):
        self.table.enter_scope("global")
        node.declarations.accept(self)
        node.block.accept(self)
        # não fecha o escopo global para permitir inspeção após o check

    def visit_Header(self, node: Header):
        pass  # nada a verificar

    def visit_Declarations(self, node: Declarations):
        for var_decl in node.var_section:
            var_decl.accept(self)
        for proc_decl in node.procedures:
            proc_decl.accept(self)

    def visit_VariableDeclaration(self, node: VariableDeclaration):
        for name in node.identifiers:
            sym = Symbol(
                name=name.lower(),
                kind=SymbolKind.VARIABLE,
                data_type=node.var_type,
                scope=self.table.current_scope_name,
                line=node.line
            )
            self.table.define(sym)   # lança SemanticError se redeclarado

    def visit_ProcedureDeclaration(self, node: ProcedureDeclaration):
        # Registra o procedimento no escopo corrente (antes de entrar no escopo dele)
        sym = Symbol(
            name=node.name.lower(),
            kind=SymbolKind.PROCEDURE,
            data_type=DataType.NONE,
            scope=self.table.current_scope_name,
            line=node.line
        )
        self.table.define(sym)

        # Abre escopo local do procedimento
        self.table.enter_scope(node.name.lower())
        node.declarations.accept(self)
        node.block.accept(self)
        self.table.exit_scope()

    def visit_Block(self, node: Block):
        for stmt in node.statements:
            stmt.accept(self)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------
    def visit_AssignStmt(self, node: AssignStmt):
        # Verifica que a variável existe e é do tipo variable
        sym = self.table.require(node.target, node.line)
        if sym.kind != SymbolKind.VARIABLE:
            self._error(
                f"'{node.target}' é um procedimento e não pode receber atribuição.",
                node.line
            )

        expr_type = self._expr_type(node.expression)

        if not _compatible_assign(expr_type, sym.data_type):
            self._error(
                f"Incompatibilidade de tipos na atribuição a '{node.target}': "
                f"tipo da expressão é '{expr_type}', variável é '{sym.data_type}'.",
                node.line
            )

    def visit_ProcCallStmt(self, node: ProcCallStmt):
        sym = self.table.require(node.name, node.line)
        if sym.kind != SymbolKind.PROCEDURE:
            self._error(
                f"'{node.name}' não é um procedimento.", node.line
            )

    def visit_IfStmt(self, node: IfStmt):
        self._expr_type(node.condition)   # apenas verifica
        node.then_branch.accept(self)
        if node.else_branch:
            node.else_branch.accept(self)

    def visit_WhileStmt(self, node: WhileStmt):
        self._expr_type(node.condition)
        node.body.accept(self)

    def visit_EmptyStmt(self, node: EmptyStmt):
        pass

    # ------------------------------------------------------------------
    # Expressões — retornam o tipo inferido e preenchem inferred_type
    # ------------------------------------------------------------------
    def _expr_type(self, node: ASTNode) -> str:
        """Resolve o tipo de uma expressão e preenche inferred_type."""
        return node.accept(self) or DataType.UNKNOWN

    def visit_BinaryOp(self, node: BinaryOp) -> str:
        left_type  = self._expr_type(node.left)
        right_type = self._expr_type(node.right)

        # Operadores relacionais produzem "boolean" (integer nesta implementação)
        relops = {'=', '<', '>', '<=', '>=', '<>'}
        if node.operator in relops:
            node.inferred_type = DataType.INTEGER  # boolean
        else:
            node.inferred_type = _result_type(left_type, right_type)

        return node.inferred_type

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        operand_type = self._expr_type(node.operand)
        node.inferred_type = operand_type
        return operand_type

    def visit_Identifier(self, node: Identifier) -> str:
        sym = self.table.require(node.name, node.line)
        node.inferred_type = sym.data_type
        return sym.data_type

    def visit_Number(self, node: Number) -> str:
        # inferred_type já definido em __post_init__
        return node.inferred_type

    # ------------------------------------------------------------------
    # Nós que não produzem tipo (estruturais usados via accept)
    # ------------------------------------------------------------------
    def visit_Program(self, node: Program):
        self.table.enter_scope("global")
        node.declarations.accept(self)
        node.block.accept(self)

    def visit_Header(self, node): pass
    def visit_Declarations(self, node: Declarations):
        for v in node.var_section:
            v.accept(self)
        for p in node.procedures:
            p.accept(self)
    def visit_VariableDeclaration(self, node: VariableDeclaration):
        for name in node.identifiers:
            sym = Symbol(name=name.lower(), kind=SymbolKind.VARIABLE,
                         data_type=node.var_type,
                         scope=self.table.current_scope_name, line=node.line)
            self.table.define(sym)
    def visit_ProcedureDeclaration(self, node: ProcedureDeclaration):
        sym = Symbol(name=node.name.lower(), kind=SymbolKind.PROCEDURE,
                     data_type=DataType.NONE,
                     scope=self.table.current_scope_name, line=node.line)
        self.table.define(sym)
        self.table.enter_scope(node.name.lower())
        node.declarations.accept(self)
        node.block.accept(self)
        self.table.exit_scope()
    def visit_Block(self, node: Block):
        for s in node.statements: s.accept(self)
    def visit_AssignStmt(self, node: AssignStmt):
        sym = self.table.require(node.target, node.line)
        if sym.kind != SymbolKind.VARIABLE:
            self._error(f"'{node.target}' é um procedimento, não uma variável.", node.line)
        expr_type = self._expr_type(node.expression)
        if not _compatible_assign(expr_type, sym.data_type):
            self._error(
                f"Incompatibilidade de tipos: '{expr_type}' → '{sym.data_type}' "
                f"(variável '{node.target}')", node.line)
    def visit_ProcCallStmt(self, node: ProcCallStmt):
        sym = self.table.require(node.name, node.line)
        if sym.kind != SymbolKind.PROCEDURE:
            self._error(f"'{node.name}' não é um procedimento.", node.line)
    def visit_IfStmt(self, node: IfStmt):
        self._expr_type(node.condition)
        node.then_branch.accept(self)
        if node.else_branch: node.else_branch.accept(self)
    def visit_WhileStmt(self, node: WhileStmt):
        self._expr_type(node.condition)
        node.body.accept(self)
    def visit_EmptyStmt(self, node): pass
