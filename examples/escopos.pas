{ ============================================================
  escopos.pas — Testa escopos aninhados e procedimentos
  ============================================================ }
program escopos;
var
  n : integer;

procedure calcula;
var
  temp : integer;
begin
  temp := n * 2;
  if temp > 10 then
    n := temp
  else
    n := 0
end;

procedure dobra;
var
  aux : integer;
begin
  aux := n + n;
  n   := aux
end;

begin
  n := 5;
  calcula();
  dobra();
  while n > 0 do
  begin
    n := n - 1
  end
end.
