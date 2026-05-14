# flux_lexer.py
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

class TokenType(Enum):
    # Cuvinte cheie
    INTENTIE = auto()
    MOZAIC = auto()
    TIMELINE = auto()
    PROBABILITATE = auto()
    COLAPSEAZA = auto()
    VID_CAUZAL = auto()
    PARADOX = auto()
    INCHEGARE = auto()
    FLUX = auto()
    STRUCTURA = auto()
    FUNCTIE = auto()
    DACA = auto()
    ALTFEL = auto()
    PENTRU = auto()
    IN_TIMP_CE = auto()
    RETUR = auto()
    LANSARE = auto()
    ASCULTA = auto()
    TRIMITE = auto()
    
    # Operatori și delimitatori
    EGAL = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PUNCT = auto()
    VIRGULA = auto()
    DOI_PUNCTI = auto()
    PUNCT_VIRGULA = auto()
    PARANTEZA_DREAPTA = auto()
    PARANTEZA_STANGA = auto()
    ACOLADA_DREAPTA = auto()
    ACOLADA_STANGA = auto()
    COLTI_DREAPTA = auto()
    COLTI_STANGA = auto()
    SARPENTE_DREAPTA = auto()
    SARPENTE_STANGA = auto()
    
    # Altele
    IDENTIFICATOR = auto()
    NUMAR = auto()
    SIR = auto()
    PROB_FLOAT = auto()    # gen 0.85
    INTERVAL = auto()      # [1s, 2s]
    COMENTARIU = auto()
    SFARSIT_FISIER = auto()

@dataclass
class Token:
    tip: TokenType
    valoare: any
    linie: int
    coloana: int

class Lexer:
    def __init__(self, sursa: str):
        self.sursa = sursa
        self.pos = 0
        self.linie = 1
        self.coloana = 1
        self.tokens = []
        
        # Pattern-uri
        self.keywords = {
            "intentie": TokenType.INTENTIE,
            "mozaic_cauzal": TokenType.MOZAIC,
            "timeline": TokenType.TIMELINE,
            "probabilitate": TokenType.PROBABILITATE,
            "colapseaza": TokenType.COLAPSEAZA,
            "vid_cauzal": TokenType.VID_CAUZAL,
            "paradox": TokenType.PARADOX,
            "inchegare": TokenType.INCHEGARE,
            "flux": TokenType.FLUX,
            "structura": TokenType.STRUCTURA,
            "functie": TokenType.FUNCTIE,
            "daca": TokenType.DACA,
            "altfel": TokenType.ALTFEL,
            "pentru": TokenType.PENTRU,
            "in_timp_ce": TokenType.IN_TIMP_CE,
            "retur": TokenType.RETUR,
            "lanseaza": TokenType.LANSARE,
            "asculta": TokenType.ASCULTA,
            "trimite": TokenType.TRIMITE,
        }
        
    def tokenize(self) -> List[Token]:
        while self.pos < len(self.sursa):
            ch = self.sursa[self.pos]
            
            if ch.isspace():
                self._advance()
                continue
                
            if ch == '#':
                self._comentariu()
                continue
                
            if ch.isalpha() or ch == '_':
                self._identificator_sau_cuvant()
                continue
                
            if ch.isdigit() or (ch == '.' and self._peek().isdigit()):
                self._numar()
                continue
                
            if ch == '"':
                self._sir()
                continue
                
            # Operatori și delimitatori
            if ch == '=':
                self._add_token(TokenType.EGAL, '=')
                self._advance()
            elif ch == '+':
                self._add_token(TokenType.PLUS, '+')
                self._advance()
            elif ch == '-':
                self._add_token(TokenType.MINUS, '-')
                self._advance()
            elif ch == '*':
                self._add_token(TokenType.STAR, '*')
                self._advance()
            elif ch == '/':
                self._add_token(TokenType.SLASH, '/')
                self._advance()
            elif ch == ',':
                self._add_token(TokenType.VIRGULA, ',')
                self._advance()
            elif ch == ':':
                self._add_token(TokenType.DOI_PUNCTI, ':')
                self._advance()
            elif ch == ';':
                self._add_token(TokenType.PUNCT_VIRGULA, ';')
                self._advance()
            elif ch == '(':
                self._add_token(TokenType.PARANTEZA_STANGA, '(')
                self._advance()
            elif ch == ')':
                self._add_token(TokenType.PARANTEZA_DREAPTA, ')')
                self._advance()
            elif ch == '{':
                self._add_token(TokenType.ACOLADA_STANGA, '{')
                self._advance()
            elif ch == '}':
                self._add_token(TokenType.ACOLADA_DREAPTA, '}')
                self._advance()
            elif ch == '[':
                self._add_token(TokenType.COLTI_STANGA, '[')
                self._advance()
            elif ch == ']':
                self._add_token(TokenType.COLTI_DREAPTA, ']')
                self._advance()
            elif ch == '<':
                self._add_token(TokenType.SARPENTE_STANGA, '<')
                self._advance()
            elif ch == '>':
                self._add_token(TokenType.SARPENTE_DREAPTA, '>')
                self._advance()
            else:
                raise SyntaxError(f"Caracter necunoscut '{ch}' la linia {self.linie}, coloana {self.coloana}")
                
        self._add_token(TokenType.SFARSIT_FISIER, None)
        return self.tokens
    
    def _advance(self):
        if self.sursa[self.pos] == '\n':
            self.linie += 1
            self.coloana = 1
        else:
            self.coloana += 1
        self.pos += 1
        
    def _peek(self, offset=1) -> str:
        if self.pos + offset < len(self.sursa):
            return self.sursa[self.pos + offset]
        return '\0'
    
    def _add_token(self, tip: TokenType, valoare: any):
        self.tokens.append(Token(tip, valoare, self.linie, self.coloana))
        
    def _comentariu(self):
        start_linie = self.linie
        while self.pos < len(self.sursa) and self.sursa[self.pos] != '\n':
            self._advance()
        # nu adăugăm token de comentariu în AST, doar ignorăm
        # dar păstrăm linia corectă
        self._add_token(TokenType.COMENTARIU, None)
        
    def _identificator_sau_cuvant(self):
        start = self.pos
        while self.pos < len(self.sursa) and (self.sursa[self.pos].isalnum() or self.sursa[self.pos] == '_'):
            self._advance()
        text = self.sursa[start:self.pos]
        tip = self.keywords.get(text, TokenType.IDENTIFICATOR)
        self._add_token(tip, text)
        
    def _numar(self):
        start = self.pos
        puncte = 0
        while self.pos < len(self.sursa) and (self.sursa[self.pos].isdigit() or self.sursa[self.pos] == '.'):
            if self.sursa[self.pos] == '.':
                puncte += 1
                if puncte > 1:
                    break
            self._advance()
        numar_str = self.sursa[start:self.pos]
        if '.' in numar_str:
            valoare = float(numar_str)
            self._add_token(TokenType.PROB_FLOAT if 'prob' in self.sursa[max(0,start-5):start] else TokenType.NUMAR, valoare)
        else:
            self._add_token(TokenType.NUMAR, int(numar_str))
            
    def _sir(self):
        self._advance()  # skip "
        start = self.pos
        while self.pos < len(self.sursa) and self.sursa[self.pos] != '"':
            if self.sursa[self.pos] == '\\':
                self._advance()  # escape char
            self._advance()
        if self.pos >= len(self.sursa):
            raise SyntaxError("String neterminat")
        valoare = self.sursa[start:self.pos]
        self._advance()  # skip closing "
        self._add_token(TokenType.SIR, valoare)