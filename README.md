# Compilador para Subconjunto de Pascal

Implementação completa de todas as fases pedidas no projeto final.

---

## Estrutura do Projeto

```
pascal-compiler/
├── src/
│   ├── lexer.py          # Fase 1 — Analisador Léxico (Scanner)
│   ├── symbol_table.py   # Tabela de Símbolos com escopos aninhados
│   ├── ast_nodes.py      # Nós da AST + Visitor Pattern + ASTPrinter
│   ├── parser.py         # Fase 2 — Analisador Sintático (Parser LL)
│   ├── type_checker.py   # Fase 3 — Verificador de Tipos
│   ├── codegen.py        # Fase 4 — Gerador de Código Intermediário (TAC)
│   └── compiler.py       # Orquestrador principal + CLI
├── examples/
│   ├── exemplo.pas       # Programa do exemplo_pas
│   ├── teste_tipos.pas   # Testa promoção de tipos integer → real
│   └── escopos.pas       # Testa escopos aninhados e múltiplos procedimentos
└── tests/
    └── test_compiler.py  # Suite de 44 testes unitários e de integração
```

---

## Fases Implementadas

### Fase 1 — Analisador Léxico (`lexer.py`)

Lê o código-fonte caractere a caractere e produz uma lista de **Tokens**.

**Reconhece:**
| Categoria        | Exemplos                                  |
|-----------------|-------------------------------------------|
| Palavras-chave   | `program var procedure begin end if then else while do integer real not` |
| Identificadores  | `x`, `hello`, `world123`                 |
| Números inteiros | `0`, `42`, `1234`                         |
| Números reais    | `3.14`, `2.0`, `1E5`, `1.5e-3`           |
| Operadores       | `:=`, `=`, `<`, `>`, `<=`, `>=`, `<>`   |
| Addops           | `+`, `-`, `or`                            |
| Mulops           | `*`, `/`, `div`, `mod`, `and`            |
| Delimitadores    | `;`, `,`, `:`, `(`, `)`, `.`             |
| Comentários      | `{ ... }` — ignorados                    |

**Case-insensitive:** `BEGIN = begin = Begin`

---

### Tabela de Símbolos (`symbol_table.py`)

Estrutura de **pilha de escopos** (escopo mais interno = topo).

**Operações:**
- `enter_scope(nome)` — abre novo escopo
- `exit_scope()` — fecha escopo corrente
- `define(symbol)` — insere símbolo; erro se já existe no mesmo escopo
- `lookup(nome)` — busca do escopo mais interno ao mais externo
- `require(nome)` — como lookup, mas lança `SemanticError` se não encontrado

**Símbolos suportados:**
- `SymbolKind.VARIABLE` — com `DataType.INTEGER` ou `DataType.REAL`
- `SymbolKind.PROCEDURE` — com `DataType.NONE`

---

### Fase 2 — Analisador Sintático (`parser.py`)

Parser **descendente recursivo LL** que constrói a AST.

**Gramática implementada:**
```
Program                → Header Declarations Block .
Header                 → program id ;
Declarations           → VariableDeclarationSection ProcedureDeclarations*
VariableDeclarationSection → VAR VariableDeclarations | ε
VariableDeclarations   → VariableDeclaration+
VariableDeclaration    → IdentifierList : Type ;
IdentifierList         → id (, id)*
Type                   → integer | real
ProcedureDeclarations  → (procedure id ; Declarations Block ;)*
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
```

---

### Fase 3 — Verificador de Tipos (`type_checker.py`)

Percorre a AST com o **Visitor Pattern** e:

1. **Popula a tabela de símbolos** com variáveis e procedimentos
2. **Detecta erros semânticos:**
   - Variável não declarada
   - Redeclaração no mesmo escopo
   - Atribuição incompatível (`real → integer` é erro)
   - Chamada de variável como procedimento e vice-versa
3. **Infere tipos nas expressões:**
   - `integer op integer → integer`
   - `real op qualquer → real` (promoção implícita)
   - `relop → integer` (booleano representado como inteiro)
4. **Preenche `inferred_type`** em cada nó de expressão da AST

---

### Fase 4 — Gerador de Código Intermediário (`codegen.py`)

Produz **código de três endereços (TAC — Three-Address Code)**.

**Instruções geradas:**
```
t1 := <valor>            # atribuição / cópia
t1 := t2 op t3           # operação binária
t1 := op t2              # operação unária
goto Ln                  # salto incondicional
ifFalse t goto Ln        # salto se falso
if t goto Ln             # salto se verdadeiro
call proc, n             # chamada de procedimento
Ln:                      # rótulo
[proc nome]              # início de procedimento
[end proc nome]          # fim de procedimento
```

**Estratégias de geração:**
- `if-then-else`: `ifFalse cond goto L_else` → then → `goto L_end` → `L_else:` → else → `L_end:`
- `while`: `L_begin:` → `ifFalse cond goto L_end` → corpo → `goto L_begin` → `L_end:`

---

## Como Usar

### Pré-requisito
Python 3.10 ou superior (sem dependências externas).

### Compilar o exemplo
```bash
cd src
python compiler.py --example -v
```

### Compilar um arquivo `.pas`
```bash
python compiler.py ../examples/exemplo.pas -v
```

### Mostrar apenas tokens
```bash
python compiler.py --tokens ../examples/exemplo.pas
```

### Mostrar apenas a AST
```bash
python compiler.py --ast ../examples/exemplo.pas
```

### Mostrar apenas a tabela de símbolos
```bash
python compiler.py --symbols ../examples/exemplo.pas
```

### Mostrar apenas o código intermediário (TAC)
```bash
python compiler.py --tac ../examples/exemplo.pas
```

### Todas as flags disponíveis
```
python compiler.py --help
```

---

## Executar os Testes

```bash
cd pascal-compiler
python tests/test_compiler.py
```

Saída esperada: **44 testes, 0 erros, 0 falhas.**

Com pytest:
```bash
pytest tests/test_compiler.py -v
```

### O que é testado
| Módulo       | Testes                                                          |
|-------------|------------------------------------------------------------------|
| Lexer        | Identificadores, palavras-chave, inteiros, reais, operadores, comentários, erros léxicos, rastreamento de linha |
| Parser       | Programa mínimo, declarações, procedimentos, `if-else`, `while`, expressões aninhadas, chamadas de proc, erros sintáticos |
| TypeChecker  | Variáveis/proc na tabela, uso de não-declarado, redeclaração, compatibilidade de tipos, promoção `int→real` |
| CodeGen      | Instruções `assign`, rótulos para `if`, `goto` para `while`, marcadores de proc, `call` |
| Integração   | Exemplo, múltiplos procedimentos, `if` aninhado em `while`, comentários, operador `not` |

---

## Exemplo de Saída

**Entrada** (`exemplo.pas`):
```pascal
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
```

**TAC gerado:**
```
[proc teste]
    t1 := 10
    a := t1
    t2 := 5
    t3 := a > t2
    ifFalse t3 goto L1
    x := a
    goto L2
L1:
    t4 := 0
    x := t4
L2:
[end proc teste]

[proc __main__]
    t5 := 1
    x := t5
    t6 := 2
    y := t6
    t7 := 3.5
    z := t7
    call teste, 0
L3:
    t8 := x < y
    ifFalse t8 goto L4
    t9 := 1
    t10 := x + t9
    x := t10
    goto L3
L4:
[end proc __main__]
```

---

## Arquitetura — Decisões de Projeto

### Visitor Pattern
O TypeChecker e o CodeGenerator implementam o **Visitor Pattern** sobre a AST. Isso separa a lógica de análise da estrutura dos nós, permitindo adicionar novas fases (otimizador, gerador de código objeto) sem modificar as classes existentes.

### Parser LL Descendente Recursivo
Cada não-terminal da gramática corresponde a um método Python (`_parse_X`). Isso torna a relação gramática↔código direta e fácil de auditar.

### Tabela de Símbolos como Pilha de Escopos
Cada chamada a `enter_scope()` empilha um novo dicionário. A busca percorre a pilha de trás para frente (escopo mais interno primeiro), implementando o sombreamento léxico correto.

### Erros com Localização
Todos os erros (`LexerError`, `ParseError`, `SemanticError`) carregam o número de linha para facilitar diagnóstico.
