# flux_parser.py - Recursive descent parser with Pratt-style expression parsing
from typing import List, Optional, Callable, Dict
from flux_lexer import Token, TokenType
from flux_ast import *


from flux_diagnostics import Span, FluxDiagnosticError


class ParseError(FluxDiagnosticError):
    pass


def _human_token(tok) -> str:
    """Render a token in the form a user would type, for error messages."""
    if tok.type == TokenType.EOF:
        return "end of file"
    if tok.type == TokenType.STRING:
        return f'string literal "{tok.value}"'
    if tok.type == TokenType.INTEGER:
        return f"integer {tok.value}"
    if tok.type == TokenType.FLOAT:
        return f"number {tok.value}"
    if tok.type == TokenType.DURATION:
        return f"duration {tok.value[1]}"
    return f"{tok.value!r}"


# Human-readable names for token types, used in "expected X" messages.
_TOKEN_NAMES = {
    TokenType.SEMICOLON: "';'",
    TokenType.COMMA:     "','",
    TokenType.COLON:     "':'",
    TokenType.LPAREN:    "'('",
    TokenType.RPAREN:    "')'",
    TokenType.LBRACE:    "'{'",
    TokenType.RBRACE:    "'}'",
    TokenType.LBRACKET:  "'['",
    TokenType.RBRACKET:  "']'",
    TokenType.ASSIGN:    "'='",
    TokenType.ARROW:     "'->'",
    TokenType.IDENT:     "an identifier",
    TokenType.INTEGER:   "an integer",
    TokenType.FLOAT:     "a number",
    TokenType.STRING:    "a string literal",
    TokenType.DURATION:  "a duration literal",
    TokenType.IN:        "'in'",
}


def _token_name(t: TokenType) -> str:
    return _TOKEN_NAMES.get(t, t.name.lower())


# precedence levels (higher = tighter binding)
PREC_NONE       = 0
PREC_OR         = 1     # ||
PREC_AND        = 2     # &&
PREC_EQUALITY   = 3     # == !=
PREC_COMPARISON = 4     # < > <= >=
PREC_CONCAT     = 5     # ++
PREC_TERM       = 6     # + -
PREC_FACTOR     = 7     # * / %
PREC_UNARY      = 8     # ! -
PREC_CALL       = 9     # . ( )


_BINARY_PREC: Dict[TokenType, int] = {
    TokenType.OR:      PREC_OR,
    TokenType.AND:     PREC_AND,
    TokenType.EQ:      PREC_EQUALITY,
    TokenType.NEQ:     PREC_EQUALITY,
    TokenType.LT:      PREC_COMPARISON,
    TokenType.GT:      PREC_COMPARISON,
    TokenType.LE:      PREC_COMPARISON,
    TokenType.GE:      PREC_COMPARISON,
    TokenType.CONCAT:  PREC_CONCAT,
    TokenType.PLUS:    PREC_TERM,
    TokenType.MINUS:   PREC_TERM,
    TokenType.STAR:    PREC_FACTOR,
    TokenType.SLASH:   PREC_FACTOR,
    TokenType.PERCENT: PREC_FACTOR,
}


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    # ---------- main entry ----------

    def parse(self) -> Program:
        decls: List[Node] = []
        while not self._check(TokenType.EOF):
            decls.append(self._declaration())
        return Program(decls)

    def _declaration(self) -> Node:
        t = self._peek().type
        if t == TokenType.INTENTION:    return self._parse_intention()
        if t == TokenType.FLOW:         return self._parse_flow()
        if t == TokenType.FUNCTION:     return self._parse_function()
        if t == TokenType.STRUCT:       return self._parse_struct()
        if t == TokenType.CAUSAL_MOSAIC: return self._parse_causal_mosaic()
        tok = self._peek()
        raise ParseError(
            f"expected a top-level declaration, found {_human_token(tok)}",
            span=tok.span(),
            hint="expected 'intention', 'function', 'flow', 'struct', "
                 "or 'causal_mosaic'",
        )

    # ---------- top-level declarations ----------

    def _parse_intention(self) -> IntentionDecl:
        start = self._consume(TokenType.INTENTION)
        name = self._consume(TokenType.IDENT).value
        self._consume(TokenType.LBRACE)
        trigger: Optional[Node] = None
        priority: Optional[float] = None
        condition: Optional[Node] = None
        body: List[Node] = []
        while not self._check(TokenType.RBRACE):
            t = self._peek().type
            if t == TokenType.TRIGGER:
                self._advance(); self._consume(TokenType.COLON)
                trigger = self._expression()
            elif t == TokenType.PRIORITY:
                prio_tok = self._advance()
                self._consume(TokenType.COLON)
                expr = self._expression()
                if isinstance(expr, NumberLiteral):
                    priority = float(expr.value)
                elif isinstance(expr, Probability):
                    priority = float(expr.value)
                elif (isinstance(expr, UnaryOp) and expr.op == "-"
                      and isinstance(expr.operand, NumberLiteral)):
                    priority = -float(expr.operand.value)
                else:
                    raise ParseError(
                        "priority must be a numeric literal",
                        span=prio_tok.span(),
                        hint="write a number like 0.9 or -0.1",
                    )
            elif t == TokenType.CONDITION:
                self._advance(); self._consume(TokenType.COLON)
                condition = self._expression()
            elif t == TokenType.EXECUTE:
                self._advance(); self._consume(TokenType.COLON)
                body = self._block()
            else:
                tok = self._peek()
                raise ParseError(
                    f"unexpected {_human_token(tok)} in intention body",
                    span=tok.span(),
                    hint="expected 'trigger', 'priority', 'condition', "
                         "'execute', or '}'",
                )
        self._consume(TokenType.RBRACE)
        return IntentionDecl(name, trigger, priority, condition, body, line=start.line)

    def _parse_flow(self) -> FlowDecl:
        self._consume(TokenType.FLOW)
        name = self._consume(TokenType.IDENT).value
        self._consume(TokenType.LPAREN)
        params: List[str] = []
        if not self._check(TokenType.RPAREN):
            params.append(self._consume(TokenType.IDENT).value)
            while self._match(TokenType.COMMA):
                params.append(self._consume(TokenType.IDENT).value)
        self._consume(TokenType.RPAREN)
        body = self._block()
        return FlowDecl(name, params, body)

    def _parse_function(self) -> FunctionDecl:
        self._consume(TokenType.FUNCTION)
        name = self._consume(TokenType.IDENT).value
        self._consume(TokenType.LPAREN)
        params: List = []
        if not self._check(TokenType.RPAREN):
            params.append(self._parse_typed_param())
            while self._match(TokenType.COMMA):
                params.append(self._parse_typed_param())
        self._consume(TokenType.RPAREN)
        return_type: Optional[str] = None
        if self._match(TokenType.ARROW):
            return_type = self._consume(TokenType.IDENT).value
        body = self._block()
        return FunctionDecl(name, params, return_type, body)

    def _parse_typed_param(self):
        name = self._consume(TokenType.IDENT).value
        self._consume(TokenType.COLON)
        type_name = self._consume(TokenType.IDENT).value
        return (name, type_name)

    def _parse_struct(self) -> StructDecl:
        self._consume(TokenType.STRUCT)
        name = self._consume(TokenType.IDENT).value
        self._consume(TokenType.LBRACE)
        fields: Dict[str, Node] = {}
        while not self._check(TokenType.RBRACE):
            field_name = self._consume(TokenType.IDENT).value
            self._consume(TokenType.COLON)
            field_type = self._consume(TokenType.IDENT).value
            fields[field_name] = Identifier(field_type)
            if self._check(TokenType.SEMICOLON) or self._check(TokenType.COMMA):
                self._advance()
        self._consume(TokenType.RBRACE)
        return StructDecl(name, fields)

    def _parse_causal_mosaic(self) -> CausalMosaicDecl:
        self._consume(TokenType.CAUSAL_MOSAIC)
        name = self._consume(TokenType.IDENT).value
        self._consume(TokenType.ASSIGN)
        comp = self._expression()
        self._match(TokenType.SEMICOLON)
        return CausalMosaicDecl(name, comp)

    # ---------- blocks / statements ----------

    def _block(self) -> List[Node]:
        self._consume(TokenType.LBRACE)
        stmts: List[Node] = []
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            stmts.append(self._statement())
        self._consume(TokenType.RBRACE)
        return stmts

    def _statement(self) -> Node:
        t = self._peek().type
        if t == TokenType.LET:       return self._parse_let()
        if t == TokenType.IF:        return self._parse_if()
        if t == TokenType.FOR:       return self._parse_for()
        if t == TokenType.WHILE:     return self._parse_while()
        if t == TokenType.RETURN:    return self._parse_return()
        if t == TokenType.LAUNCH:    return self._parse_launch()
        if t == TokenType.SEND:      return self._parse_send()
        if t == TokenType.COLLAPSE:  return self._parse_collapse()
        # assignment or expression statement
        return self._parse_assign_or_expr()

    def _parse_let(self) -> Let:
        self._consume(TokenType.LET)
        name = self._consume(TokenType.IDENT).value
        self._consume(TokenType.ASSIGN)
        value = self._expression()
        self._consume(TokenType.SEMICOLON)
        return Let(name, value)

    def _parse_if(self) -> IfNode:
        self._consume(TokenType.IF)
        cond = self._expression()
        then_branch = self._block()
        else_branch: List[Node] = []
        if self._match(TokenType.ELSE):
            if self._check(TokenType.IF):
                # else if -> wrap as single-statement else branch
                else_branch = [self._parse_if()]
            else:
                else_branch = self._block()
        return IfNode(cond, then_branch, else_branch)

    def _parse_for(self) -> ForNode:
        self._consume(TokenType.FOR)
        var = self._consume(TokenType.IDENT).value
        self._consume(TokenType.IN)
        source = self._expression()
        body = self._block()
        return ForNode(var, source, body)

    def _parse_while(self) -> WhileNode:
        self._consume(TokenType.WHILE)
        cond = self._expression()
        body = self._block()
        return WhileNode(cond, body)

    def _parse_return(self) -> ReturnNode:
        self._consume(TokenType.RETURN)
        value: Optional[Node] = None
        if not self._check(TokenType.SEMICOLON):
            value = self._expression()
        self._consume(TokenType.SEMICOLON)
        return ReturnNode(value)

    def _parse_launch(self) -> Launch:
        self._consume(TokenType.LAUNCH)
        self._consume(TokenType.LPAREN)
        name = self._consume(TokenType.IDENT).value
        args: List[Node] = []
        while self._match(TokenType.COMMA):
            args.append(self._expression())
        self._consume(TokenType.RPAREN)
        self._consume(TokenType.SEMICOLON)
        return Launch(name, args)

    def _parse_send(self) -> SendSensation:
        self._consume(TokenType.SEND)
        self._consume(TokenType.LPAREN)
        kind = self._expression()
        self._consume(TokenType.COMMA)
        content = self._expression()
        duration: Optional[Node] = None
        if self._match(TokenType.COMMA):
            duration = self._expression()
        self._consume(TokenType.RPAREN)
        self._consume(TokenType.SEMICOLON)
        return SendSensation(kind, content, duration)

    def _parse_collapse(self) -> Node:
        # Statement form: `collapse(expr, method);`
        node = self._parse_collapse_core()
        self._consume(TokenType.SEMICOLON)
        # As a statement, the result is discarded by codegen (Collapse stmt).
        return node

    def _parse_collapse_core(self) -> Collapse:
        self._consume(TokenType.COLLAPSE)
        self._consume(TokenType.LPAREN)
        expr = self._expression()
        self._consume(TokenType.COMMA)
        if self._check(TokenType.IDENT):
            method = self._consume(TokenType.IDENT).value
        elif self._check(TokenType.STRING):
            method = self._consume(TokenType.STRING).value
        else:
            tok = self._peek()
            raise ParseError(
                f"expected collapse method name, found {_human_token(tok)}",
                span=tok.span(),
                hint="use one of: max_weight, mean, weighted_random, "
                     "random, first",
            )
        self._consume(TokenType.RPAREN)
        return Collapse(expr, method)

    def _parse_assign_or_expr(self) -> Node:
        # Look ahead: IDENT ASSIGN ... is an assignment;
        # otherwise it's an expression statement.
        if self._check(TokenType.IDENT) and self._peek_at(1).type == TokenType.ASSIGN:
            name = self._consume(TokenType.IDENT).value
            self._consume(TokenType.ASSIGN)
            value = self._expression()
            self._consume(TokenType.SEMICOLON)
            return Assign(name, value)
        expr = self._expression()
        self._consume(TokenType.SEMICOLON)
        return ExpressionStmt(expr)

    # ---------- expressions (Pratt) ----------

    def _expression(self) -> Node:
        return self._parse_precedence(PREC_OR)

    def _parse_precedence(self, min_prec: int) -> Node:
        left = self._unary()
        while True:
            tok = self._peek()
            prec = _BINARY_PREC.get(tok.type, PREC_NONE)
            if prec < min_prec:
                break
            self._advance()
            # left-associative: right side parsed at prec + 1
            right = self._parse_precedence(prec + 1)
            left = BinOp(left, tok.value, right)
        return left

    def _unary(self) -> Node:
        if self._check(TokenType.MINUS) or self._check(TokenType.NOT):
            op = self._advance().value
            operand = self._unary()
            return UnaryOp(op, operand)
        return self._postfix()

    def _postfix(self) -> Node:
        expr = self._primary()
        while True:
            if self._match(TokenType.DOT):
                member = self._consume(TokenType.IDENT).value
                if self._check(TokenType.LPAREN):
                    args = self._parse_args()
                    expr = MethodCall(expr, member, args)
                else:
                    expr = FieldAccess(expr, member)
            elif self._check(TokenType.LPAREN) and isinstance(expr, Identifier):
                # transform Identifier(name) followed by ( into a Call
                args = self._parse_args()
                expr = Call(expr.name, args)
            else:
                break
        return expr

    def _parse_args(self) -> List[Node]:
        self._consume(TokenType.LPAREN)
        args: List[Node] = []
        if not self._check(TokenType.RPAREN):
            args.append(self._expression())
            while self._match(TokenType.COMMA):
                args.append(self._expression())
        self._consume(TokenType.RPAREN)
        return args

    def _primary(self) -> Node:
        tok = self._peek()
        if tok.type == TokenType.INTEGER:
            self._advance()
            return NumberLiteral(float(tok.value))
        if tok.type == TokenType.FLOAT:
            self._advance()
            # treat 0.0..=1.0 as probability hint, but keep semantics the same
            return NumberLiteral(float(tok.value))
        if tok.type == TokenType.DURATION:
            self._advance()
            nanos, original = tok.value
            return DurationLiteral(nanos, original)
        if tok.type == TokenType.STRING:
            self._advance()
            return StringLiteral(tok.value)
        if tok.type == TokenType.TRUE:
            self._advance(); return BoolLiteral(True)
        if tok.type == TokenType.FALSE:
            self._advance(); return BoolLiteral(False)
        if tok.type == TokenType.LISTEN:
            return self._parse_listen_expr()
        if tok.type == TokenType.COLLAPSE:
            return self._parse_collapse_core()
        if tok.type == TokenType.DIST:
            return self._parse_dist_literal()
        if tok.type == TokenType.IDENT:
            self._advance()
            return Identifier(tok.value)
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._expression()
            self._consume(TokenType.RPAREN)
            return expr
        if tok.type == TokenType.LBRACKET:
            return self._parse_list_literal()
        raise ParseError(
            f"unexpected {_human_token(tok)} where an expression was expected",
            span=tok.span(),
            hint="expected a value, identifier, or '('",
        )

    def _parse_dist_literal(self) -> "DistLiteral":
        # dist { value_expr : weight_expr, ... }  -- trailing comma allowed.
        # Empty dist is rejected at parse time; if you really want a
        # degenerate distribution use `dist { nil: 1 }` (once nil is a value).
        self._consume(TokenType.DIST)
        self._consume(TokenType.LBRACE)
        if self._check(TokenType.RBRACE):
            tok = self._peek()
            raise ParseError(
                "empty dist literal",
                span=tok.span(),
                hint="a distribution needs at least one value:weight pair",
            )
        entries = [self._parse_dist_entry()]
        while self._match(TokenType.COMMA):
            if self._check(TokenType.RBRACE):
                break
            entries.append(self._parse_dist_entry())
        self._consume(TokenType.RBRACE)
        return DistLiteral(entries)

    def _parse_dist_entry(self):
        value = self._expression()
        self._consume(TokenType.COLON)
        weight = self._expression()
        return (value, weight)

    def _parse_list_literal(self) -> "ListLiteral":
        self._consume(TokenType.LBRACKET)
        items: List[Node] = []
        if not self._check(TokenType.RBRACKET):
            items.append(self._expression())
            while self._match(TokenType.COMMA):
                if self._check(TokenType.RBRACKET):
                    break
                items.append(self._expression())
        self._consume(TokenType.RBRACKET)
        return ListLiteral(items)

    def _parse_listen_expr(self) -> ListenIntention:
        self._consume(TokenType.LISTEN)
        self._consume(TokenType.LPAREN)
        source = self._consume(TokenType.IDENT).value
        timeout: Optional[Node] = None
        fallback: Optional[Node] = None
        if self._match(TokenType.COMMA):
            timeout = self._expression()
            if self._match(TokenType.COMMA):
                fallback = self._expression()
        self._consume(TokenType.RPAREN)
        return ListenIntention(source, timeout, fallback)

    # ---------- token utilities ----------

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _peek_at(self, offset: int) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _check(self, t: TokenType) -> bool:
        return self._peek().type == t

    def _match(self, t: TokenType) -> bool:
        if self._check(t):
            self._advance()
            return True
        return False

    def _consume(self, t: TokenType) -> Token:
        if self._check(t):
            return self._advance()
        cur = self._peek()
        expected = _token_name(t)
        # If we expected ';' and the previous token was on a different line,
        # point the caret at the end of the previous token instead of the
        # next one - that's where the user forgot it.
        if t == TokenType.SEMICOLON and self.pos > 0:
            prev = self.tokens[self.pos - 1]
            if prev.line != cur.line:
                span = Span(prev.line,
                            prev.end_col or (prev.column + 1),
                            prev.line,
                            (prev.end_col or (prev.column + 1)) + 1)
                raise ParseError(
                    f"expected {expected}",
                    span=span,
                    hint=f"add {expected} at the end of this line",
                )
        raise ParseError(
            f"expected {expected}, found {_human_token(cur)}",
            span=cur.span(),
            hint=f"add {expected} here",
        )
