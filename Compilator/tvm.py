# tvm.py - Executor pentru bytecode-ul Flux
import random
from typing import List, Dict, Any

class TemporalVM:
    def __init__(self):
        self.stack = []
        self.intentii_active = {}
        self.timeline_curent = "principal"
        self.prob_state = 1.0  # probabilitatea curentă a timeline-ului
        
    def run(self, bytecode: List[str]):
        ip = 0
        while ip < len(bytecode):
            instr = bytecode[ip].strip()
            if not instr:
                ip += 1
                continue
                
            parts = instr.split(maxsplit=1)
            op = parts[0]
            arg = parts[1] if len(parts) > 1 else ""
            
            if op == "INTENTIE":
                nume = arg
                self.intentii_active[nume] = {"stare": "definită", "prioritate": 1.0}
                print(f"[TVM] Intentie definita: {nume}")
            elif op == "PRIORITATE":
                prior = float(arg)
                # stocare în ultima intentie
                pass
            elif op == "DECLANȘARE":
                # următoarele linii definesc expresia de declanșare
                pass
            elif op == "TRIMITE_SENZAȚIE":
                tip_senzatie = arg
                # următoarea linie conține conținutul
                ip += 1
                continut = bytecode[ip].strip()
                print(f"[TVM] Senzație trimisă ({tip_senzatie}): {continut}")
            elif op == "ASCULTĂ_INTENȚIE":
                sursa = arg
                # simulăm un răspuns aleator
                raspuns = random.choice(["salut", "nimic", "tăcere"])
                self.stack.append(raspuns)
                print(f"[TVM] Ascultat de la {sursa}: {raspuns}")
            elif op == "COLAPSEAZĂ":
                metoda = arg
                expr = self.stack.pop() if self.stack else None
                if metoda == "pondere_maximă":
                    rezultat = expr if expr else 0.0
                else:
                    rezultat = random.random()
                self.stack.append(rezultat)
                print(f"[TVM] Colapsat cu metoda {metoda} -> {rezultat}")
            elif op == "DACĂ":
                cond = self.stack.pop()
                if cond:
                    # sare peste secțiunea ALTFEL (simplificat)
                    pass
            elif op == "OPERATOR":
                b = self.stack.pop()
                a = self.stack.pop()
                if arg == '+':
                    self.stack.append(a + b)
                elif arg == '-':
                    self.stack.append(a - b)
                elif arg == '*':
                    self.stack.append(a * b)
                elif arg == '/':
                    self.stack.append(a / b if b != 0 else 0)
            elif op == "NUMĂR":
                self.stack.append(float(arg))
            elif op == "STRING":
                self.stack.append(arg.strip('"'))
            elif op == "IDENT":
                # Într-un sistem real, am căuta în context
                self.stack.append(arg)
            elif op == "APEL":
                # Apel de funcție internă
                if arg == "trimite_senzatie":
                    # tratat mai sus, dar pentru consistență
                    pass
                else:
                    print(f"[TVM] Apel funcție nativă: {arg}")
            elif op == "RETURNEAZĂ":
                val = self.stack.pop() if self.stack else None
                print(f"[TVM] Return {val}")
                return val
            elif op == "SFÂRȘIT_INTENTIE":
                print("[TVM] Intentie terminată")
            elif op == "SFÂRȘIT_FLUX":
                print("[TVM] Flux terminat")
            else:
                print(f"[TVM] Instrucțiune necunoscută: {op}")
            ip += 1