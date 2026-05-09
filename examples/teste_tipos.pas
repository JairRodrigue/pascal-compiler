{ ============================================================
  teste_tipos.pas — Testa promoção de tipos integer → real
  ============================================================ }
program teste_tipos;
var
  i : integer;
  r : real;
begin
  i := 42;
  r := 3.14;
  r := i + r;          { integer + real → real: OK }
  i := i + 1;          { integer + integer → integer: OK }
  if i <> 0 then
    r := r + 1.0
  else
    r := 0.0
end.
