import operator
from ply import lex, yacc


class Lexer(object):
    reserved = {
        'and': 'AND',
        'or': 'OR',
        'true': "TRUE",
        'True': "TRUE",
        'TRUE': "TRUE",
        'false': "FALSE",
        'False': "FALSE",
        'FALSE': "FALSE"
    }

    tokens = [
        'STR', 'ID', 'INT', 'FLOAT', 'ADD', 'SUB', 'POW', 'MUL', 'DIV', 'AND', 'OR', 'EQ', 'LTE', 'GTE', 'LT', 'GT',
        'LPAREN', 'RPAREN', 'TRUE', 'FALSE'
    ]

    literals = ['.']

    t_ignore = ' \t\n'

    t_ADD = r'\+'
    t_SUB = r'-'
    t_POW = r'\*\*'
    t_MUL = r'\*'
    t_DIV = r'/'
    t_AND = r'&&'
    t_OR = r'\|\|'
    t_EQ = r'=='
    t_LTE = r'<='
    t_GTE = r'>='
    t_LT = r'<'
    t_GT = r'>'
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_TRUE = r'(true)|(True)|(TRUE)'
    t_FALSE = r'(false)|(False)|(FALSE)'

    def t_STR(self, t):
        r'(\'.*?\')|(".*?")'

        t.value = t.value[1:-1]
        return t

    def t_ID(self, t):
        r'[a-zA-Z_][a-zA-Z_0-9]*'

        # Reserved name?
        if t.value in self.reserved:
            t.type = self.reserved[t.value]
        else:
            self.names.add(t.value)

        return t

    def t_INT(self, t):
        r'\d+'

        t.value = int(t.value)
        return t

    def t_FLOAT(self, t):
        r'\d+\.?\d*([eE]-?\d+)?'

        t.value = float(t.value)
        return t

    def __init__(self):
        self.names = set()
        self.lexer = lex.lex(module=self)

    def get_names(self, expr):
        self.names = set()
        self.lexer.input(expr)
        list(self.lexer)

        return self.names


class Parser(object):
    tokens = Lexer.tokens

    binary_operators = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '**': operator.pow,
        '&&': lambda x, y: x and y,
        '||': lambda x, y: x or y,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        '==': operator.eq,
        '<=': operator.le,
        '>=': operator.ge,
        '<': operator.lt,
        '>': operator.gt
    }

    def p_binary_operators(self, p):
        """
        conditional : conditional AND condition
                    | conditional OR condition
        condition   : condition LTE expression
                    | condition GTE expression
                    | condition LT expression
                    | condition GT expression
                    | condition EQ expression
        expression  : expression ADD term
                    | expression SUB term
        term        : term MUL factor
                    | term DIV factor
                    | term POW factor
        """

        p[0] = self.binary_operators[p[2]](p[1], p[3])

    def p_conditional_condition(self, p):
        'conditional : condition'

        p[0] = p[1]

    def p_condition_expression(self, p):
        'condition : expression'

        p[0] = p[1]

    def p_expression_term(self, p):
        'expression : term'

        p[0] = p[1]

    def p_term_factor(self, p):
        'term : factor'

        p[0] = p[1]

    def p_factor_unary_operators(self, p):
        """
        factor : SUB factor
               | ADD factor
        """

        p[0] = p[2]
        if p[1] == '-':
            p[0] *= -1

    def p_factor_number(self, p):
        'factor : number'

        p[0] = p[1]

    def p_factor_string(self, p):
        'factor : STR'

        p[0] = p[1]

    def p_factor_bool(self, p):
        """
        factor : TRUE
               | FALSE
        """

        p[0] = True if p[1].lower() == 'true' else False

    def p_factor_conditional(self, p):
        'factor : LPAREN conditional RPAREN'

        p[0] = p[2]

    def p_number_int(self, p):
        'number : INT'

        p[0] = p[1]

    def p_number_float(self, p):
        'number : FLOAT'

        p[0] = p[1]

    def p_factor_id(self, p):
        'factor : ID'

        p[0] = self.context[p[1]]

    def __init__(self):
        self.context = {}
        self.lexer = Lexer().lexer
        self.parser = yacc.yacc(module=self)

    def evaluate(self, expr, context={}):
        self.context = context
        return self.parser.parse(expr, lexer=self.lexer)
