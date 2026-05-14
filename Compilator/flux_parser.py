# flux_parser.py
from flux_lexer import Lexer, TokenType, Token
from flux_ast import *
from typing import List, Optional

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        
    def parse(self) -> Program:
        declaratii = []
        while not self._check(TokenType.SFARSIT_FISIER):
            decl = self._declaratie()
            if decl:
                declaratii.append(decl)
        return Program(declaratii)
    
    def _declaratie(self) -> Optional[Node]:
        if self._check(TokenType.INTENTIE):
            return self._parse_intentie()
        elif self._check(TokenType.FLUX):
            return self._parse_flux()
        elif self._check(TokenType.STRUCTURA):
            return self._parse_structura()
        elif self._check(TokenType.MOZAIC):
            return self._parse_mozaic()
        elif self._check(TokenType.FUNCTIE):
            return self._parse_functie()
        else:
            raise SyntaxError(f"Declarație neașteptată: {self._peek().valoare} la linia {self._peek().linie}")
    
    def _parse_intentie(self) -> IntentieDecl:
        self._consume(TokenType.INTENTIE)
        nume = self._consume(TokenType.IDENTIFICATOR).valoare
        declansare = None
        prioritate = None
        conditie = None
        
        self._consume(TokenType.ACOLADA_STANGA)
        while not self._check(TokenType.ACOLADA_DREAPTA):
            if self._check(TokenType.IDENTIFICATOR):
                kw = self._peek().valoare
                if kw == "declansare":
                    self._advance()
                    self._consume(TokenType.DOI_PUNCTI)
                    declansare = self._expresie()
                elif kw == "prioritate":
                    self._advance()
                    self._consume(TokenType.DOI_PUNCTI)
                    prioritate = self._expresie().valoare
                elif kw == "conditie":
                    self._advance()
                    self._consume(TokenType.DOI_PUNCTI)
                    conditie = self._expresie()
                elif kw == "executa":
                    self._advance()
                    self._consume(TokenType.DOI_PUNCTI)
                    corp = self._bloc()
                    break
                else:
                    raise SyntaxError(f"Cuvânt cheie necunoscut în intentie: {kw}")
            else:
                self._advance()
        self._consume(TokenType.ACOLADA_DREAPTA)
        return IntentieDecl(nume, declansare, prioritate, conditie, corp, linie=self._peek().linie)
    
    def _parse_flux(self) -> FluxDecl:
        self._consume(TokenType.FLUX)
        nume = self._consume(TokenType.IDENTIFICATOR).valoare
        self._consume(TokenType.PARANTEZA_STANGA)
        parametri = []
        while not self._check(TokenType.PARANTEZA_DREAPTA):
            parametri.append(self._consume(TokenType.IDENTIFICATOR).valoare)
            if self._check(TokenType.VIRGULA):
                self._advance()
        self._consume(TokenType.PARANTEZA_DREAPTA)
        self._consume(TokenType.ACOLADA_STANGA)
        corp = self._bloc()
        self._consume(TokenType.ACOLADA_DREAPTA)
        return FluxDecl(nume, parametri, corp)
    
    def _parse_structura(self) -> StructuraDecl:
        self._consume(TokenType.STRUCTURA)
        nume = self._consume(TokenType.IDENTIFICATOR).valoare
        self._consume(TokenType.ACOLADA_STANGA)
        campuri = {}
        while not self._check(TokenType.ACOLADA_DREAPTA):
            camp = self._consume(TokenType.IDENTIFICATOR).valoare
            self._consume(TokenType.DOI_PUNCTI)
            tip = self._expresie()  # simplificat
            campuri[camp] = tip
            if self._check(TokenType.PUNCT_VIRGULA):
                self._advance()
        self._consume(TokenType.ACOLADA_DREAPTA)
        return StructuraDecl(nume, campuri)
    
    def _parse_mozaic(self) -> MozaicCauzal:
        self._consume(TokenType.MOZAIC)
        nume = self._consume(TokenType.IDENTIFICATOR).valoare
        self._consume(TokenType.EGAL)
        comp = self._expresie()
        return MozaicCauzal(nume, comp)
    
    def _parse_functie(self) -> FunctieDecl:
        self._consume(TokenType.FUNCTIE)
        nume = self._consume(TokenType.IDENTIFICATOR).valoare
        self._consume(TokenType.PARANTEZA_STANGA)
        parametri = []
        while not self._check(TokenType.PARANTEZA_DREAPTA):
            nume_param = self._consume(TokenType.IDENTIFICATOR).valoare
            self._consume(TokenType.DOI_PUNCTI)
            tip = self._consume(TokenType.IDENTIFICATOR).valoare
            parametri.append((nume_param, tip))
            if self._check(TokenType.VIRGULA):
                self._advance()
        self._consume(TokenType.PARANTEZA_DREAPTA)
        tip_retur = None
        if self._check(TokenType.SARPENTE_DREAPTA):
            self._advance()
            tip_retur = self._consume(TokenType.IDENTIFICATOR).valoare
        self._consume(TokenType.ACOLADA_STANGA)
        corp = self._bloc()
        self._consume(TokenType.ACOLADA_DREAPTA)
        return FunctieDecl(nume, parametri, tip_retur, corp)
    
    def _bloc(self) -> List[Node]:
        stmts = []
        while not self._check(TokenType.ACOLADA_DREAPTA) and not self._check(TokenType.SFARSIT_FISIER):
            stmt = self._statement()
            if stmt:
                stmts.append(stmt)
        return stmts
    
    def _statement(self) -> Optional[Node]:
        if self._check(TokenType.TRIMITE):
            return self._parse_trimite()
        elif self._check(TokenType.ASCULTA):
            return self._parse_asculta()
        elif self._check(TokenType.COLAPSEAZA):
            return self._parse_colapseaza()
        elif self._check(TokenType.DACA):
            return self._parse_if()
        elif self._check(TokenType.PENTRU):
            return self._parse_for()
        elif self._check(TokenType.RETUR):
            return self._parse_return()
        elif self._check(TokenType.LANSARE):
            return self._parse_lansare()
        else:
            expr = self._expresie()
            self._consume(TokenType.PUNCT_VIRGULA)
            return expr
    
    def _parse_trimite(self) -> TrimiteSenzatie:
        self._consume(TokenType.TRIMITE)
        self._consume(TokenType.PARANTEZA_STANGA)
        tip = self._consume(TokenType.IDENTIFICATOR).valoare
        self._consume(TokenType.VIRGULA)
        continut = self._expresie()
        durata = None
        if self._check(TokenType.VIRGULA):
            self._advance()
            durata = self._expresie()
        self._consume(TokenType.PARANTEZA_DREAPTA)
        self._consume(TokenType.PUNCT_VIRGULA)
        return TrimiteSenzatie(tip, continut, durata)
    
    def _parse_asculta(self) -> AscultaIntentie:
        self._consume(TokenType.ASCULTA)
        self._consume(TokenType.PARANTEZA_STANGA)
        sursa = self._consume(TokenType.IDENTIFICATOR).valoare
        self._consume(TokenType.VIRGULA)
        timeout = self._expresie() if self._check(TokenType.NUMAR) else None
        fallback = None
        if self._check(TokenType.VIRGULA):
            self._advance()
            fallback = self._expresie()
        self._consume(TokenType.PARANTEZA_DREAPTA)
        self._consume(TokenType.PUNCT_VIRGULA)
        return AscultaIntentie(sursa, timeout, fallback)
    
    def _parse_colapseaza(self) -> Colapseaza:
        self._consume(TokenType.COLAPSEAZA)
        self._consume(TokenType.PARANTEZA_STANGA)
        expr = self._expresie()
        self._consume(TokenType.VIRGULA)
        metoda = self._consume(TokenType.IDENTIFICATOR).valoare
        self._consume(TokenType.PARANTEZA_DREAPTA)
        self._consume(TokenType.PUNCT_VIRGULA)
        return Colapseaza(expr, metoda)
    
    def _parse_if(self) -> IfNode:
        self._consume(TokenType.DACA)
        cond = self._expresie()
        self._consume(TokenType.DOI_PUNCTI)
        self._consume(TokenType.ACOLADA_STANGA)
        atunci = self._bloc()
        self._consume(TokenType.ACOLADA_DREAPTA)
        altfel = []
        if self._check(TokenType.ALTFEL):
            self._advance()
            self._consume(TokenType.DOI_PUNCTI)
            self._consume(TokenType.ACOLADA_STANGA)
            altfel = self._bloc()
            self._consume(TokenType.ACOLADA_DREAPTA)
        return IfNode(cond, atunci, altfel)
    
    def _parse_for(self) -> ForNode:
        self._consume(TokenType.PENTRU)
        var = self._consume(TokenType.IDENTIFICATOR).valoare
        self._consume(TokenType.IN)
        iterable = self._expresie()
        self._consume(TokenType.DOI_PUNCTI)
        self._consume(TokenType.ACOLADA_STANGA)
        corp = self._bloc()
        self._consume(TokenType.ACOLADA_DREAPTA)
        return ForNode(var, iterable, corp)
    
    def _parse_return(self) -> ReturnNode:
        self._consume(TokenType.RETUR)
        val = self._expresie() if not self._check(TokenType.PUNCT_VIRGULA) else None
        self._consume(TokenType.PUNCT_VIRGULA)
        return ReturnNode(val)
    
    def _parse_lansare(self) -> Call:
        self._consume(TokenType.LANSARE)
        self._consume(TokenType.PARANTEZA_STANGA)
        nume = self._consume(TokenType.IDENTIFICATOR).valoare
        args = []
        while not self._check(TokenType.PARANTEZA_DREAPTA):
            args.append(self._expresie())
            if self._check(TokenType.VIRGULA):
                self._advance()
        self._consume(TokenType.PARANTEZA_DREAPTA)
        self._consume(TokenType.PUNCT_VIRGULA)
        return Call(nume, args)
    
    def _expresie(self) -> Node:
        return self._expresie_binara()
    
    def _expresie_binara(self, prec=0) -> Node:
        stanga = self._primar()
        while True:
            op = self._peek()
            if op.tip in (TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH) and self._get_prec(op.tip) >= prec:
                self._advance()
                dreapta = self._expresie_binara(self._get_prec(op.tip) + 1)
                stanga = BinOp(stanga, op.valoare, dreapta)
            else:
                break
        return stanga
    
    def _primar(self) -> Node:
        tok = self._peek()
        if tok.tip == TokenType.NUMAR:
            self._advance()
            return NumberLiteral(tok.valoare)
        elif tok.tip == TokenType.PROB_FLOAT:
            self._advance()
            return Probabilitate(tok.valoare)
        elif tok.tip == TokenType.SIR:
            self._advance()
            return StringLiteral(tok.valoare)
        elif tok.tip == TokenType.IDENTIFICATOR:
            self._advance()
            if self._check(TokenType.PARANTEZA_STANGA):
                # apel funcție
                self._advance()
                args = []
                while not self._check(TokenType.PARANTEZA_DREAPTA):
                    args.append(self._expresie())
                    if self._check(TokenType.VIRGULA):
                        self._advance()
                self._consume(TokenType.PARANTEZA_DREAPTA)
                return Call(tok.valoare, args)
            return Ident(tok.valoare)
        elif tok.tip == TokenType.PARANTEZA_STANGA:
            self._advance()
            expr = self._expresie()
            self._consume(TokenType.PARANTEZA_DREAPTA)
            return expr
        else:
            raise SyntaxError(f"Expresie neașteptată: {tok}")
    
    def _get_prec(self, tip: TokenType) -> int:
        return {TokenType.PLUS: 1, TokenType.MINUS: 1, TokenType.STAR: 2, TokenType.SLASH: 2}.get(tip, 0)
    
    def _check(self, tip: TokenType) -> bool:
        return self.pos < len(self.tokens) and self.tokens[self.pos].tip == tip
    
    def _peek(self) -> Token:
        return self.tokens[self.pos]
    
    def _advance(self):
        self.pos += 1
    
    def _consume(self, tip: TokenType) -> Token:
        if self._check(tip):
            tok = self._peek()
            self._advance()
            return tok
        else:
            raise SyntaxError(f"Așteptat {tip}, găsit {self._peek().tip} la linia {self._peek().linie}")