"""
=============================================================================
TABELA DE SÍMBOLOS — Pascal Subset Compiler
=============================================================================
Implementa uma tabela de símbolos com escopos aninhados (pilha de escopos).
Cada escopo é um dicionário nome → Symbol.

Suporte a:
  - Variáveis (integer / real)
  - Procedimentos
  - Escopo global e escopos locais de procedimentos
=============================================================================
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Tipos de símbolo e de dado
# ---------------------------------------------------------------------------
class SymbolKind:
    VARIABLE  = "variable"
    PROCEDURE = "procedure"

class DataType:
    INTEGER = "integer"
    REAL    = "real"
    NONE    = "none"     # para procedimentos (sem retorno)
    UNKNOWN = "unknown"  # antes de inferência de tipo


@dataclass
class Symbol:
    """
    Representa uma entrada na tabela de símbolos.

    Atributos:
      name      : nome do identificador (já em minúsculas para case-insensitive)
      kind      : SymbolKind.VARIABLE ou SymbolKind.PROCEDURE
      data_type : DataType.INTEGER / REAL / NONE
      scope     : nome do escopo onde foi declarado
      line      : linha de declaração (para mensagens de erro)
    """
    name:      str
    kind:      str
    data_type: str
    scope:     str
    line:      int = 0


# ---------------------------------------------------------------------------
# Erro semântico
# ---------------------------------------------------------------------------
class SemanticError(Exception):
    def __init__(self, message: str, line: int = 0):
        super().__init__(f"[Semântico] {message}" +
                         (f" (linha {line})" if line else ""))
        self.line = line


# ---------------------------------------------------------------------------
# Tabela de símbolos com escopos aninhados
# ---------------------------------------------------------------------------
class SymbolTable:
    """
    Pilha de escopos.  O escopo mais interno é o topo da pilha.

    Uso típico:
        table = SymbolTable()
        table.enter_scope("global")
        table.define(Symbol("x", SymbolKind.VARIABLE, DataType.INTEGER, "global"))
        sym = table.lookup("x")      # busca em todos os escopos
        table.exit_scope()
    """

    def __init__(self):
        # Cada item: (scope_name, dict[str, Symbol])
        self._scopes: list[tuple[str, dict]] = []
        self._scope_counter = 0

    # ------------------------------------------------------------------
    # Gerência de escopos
    # ------------------------------------------------------------------
    def enter_scope(self, name: str = ""):
        scope_name = name or f"scope_{self._scope_counter}"
        self._scope_counter += 1
        self._scopes.append((scope_name, {}))

    def exit_scope(self):
        if not self._scopes:
            raise RuntimeError("Nenhum escopo para fechar.")
        return self._scopes.pop()

    @property
    def current_scope_name(self) -> str:
        return self._scopes[-1][0] if self._scopes else "<none>"

    @property
    def depth(self) -> int:
        return len(self._scopes)

    # ------------------------------------------------------------------
    # Inserção e busca
    # ------------------------------------------------------------------
    def define(self, symbol: Symbol) -> Symbol:
        """
        Insere símbolo no escopo corrente.
        Lança SemanticError se o nome já existe no mesmo escopo.
        """
        if not self._scopes:
            raise RuntimeError("Nenhum escopo aberto.")
        _, current = self._scopes[-1]
        key = symbol.name.lower()
        if key in current:
            existing = current[key]
            raise SemanticError(
                f"Identificador '{symbol.name}' já declarado "
                f"no escopo '{self.current_scope_name}' "
                f"(declaração anterior na linha {existing.line})",
                symbol.line
            )
        current[key] = symbol
        return symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        """
        Busca um símbolo do escopo mais interno para o mais externo.
        Retorna None se não encontrado.
        """
        key = name.lower()
        for _, scope_dict in reversed(self._scopes):
            if key in scope_dict:
                return scope_dict[key]
        return None

    def lookup_current_scope(self, name: str) -> Optional[Symbol]:
        """Busca apenas no escopo corrente."""
        if not self._scopes:
            return None
        _, current = self._scopes[-1]
        return current.get(name.lower())

    def require(self, name: str, line: int = 0) -> Symbol:
        """
        Como lookup, mas lança SemanticError se não encontrado.
        """
        sym = self.lookup(name)
        if sym is None:
            raise SemanticError(
                f"Identificador '{name}' não declarado.", line
            )
        return sym

    # ------------------------------------------------------------------
    # Utilidades de exibição
    # ------------------------------------------------------------------
    def dump(self) -> str:
        """Retorna uma representação textual de todos os escopos."""
        lines = ["=== Tabela de Símbolos ==="]
        for scope_name, scope_dict in self._scopes:
            lines.append(f"\n  Escopo: [{scope_name}]")
            if not scope_dict:
                lines.append("    (vazio)")
            for sym in scope_dict.values():
                lines.append(
                    f"    {sym.name:20s}  kind={sym.kind:10s}  "
                    f"type={sym.data_type:8s}  line={sym.line}"
                )
        return "\n".join(lines)

    def all_symbols(self) -> list[Symbol]:
        """Retorna todos os símbolos de todos os escopos (para debug)."""
        result = []
        for _, scope_dict in self._scopes:
            result.extend(scope_dict.values())
        return result
