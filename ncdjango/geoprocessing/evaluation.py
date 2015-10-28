import operator
import numpy
from ply import lex, yacc
from rasterio.dtypes import is_ndarray


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

    functions = {'abs', 'min', 'max', 'median', 'mean', 'std', 'var'}

    tokens = [
        'COMMA', 'STR', 'ID', 'INT', 'FLOAT', 'ADD', 'SUB', 'POW', 'MUL', 'DIV', 'MOD', 'AND', 'OR', 'EQ', 'LTE', 'GTE', 'LT',
        'GT', 'LPAREN', 'RPAREN', 'TRUE', 'FALSE', 'FUNC'
    ]

    t_ignore = ' \t\n'

    t_COMMA = r','
    t_ADD = r'\+'
    t_SUB = r'-'
    t_POW = r'\*\*'
    t_MUL = r'\*'
    t_DIV = r'/'
    t_MOD = r'%'
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
        r"""(\'.*?\')|(".*?")"""

        t.value = t.value[1:-1]
        return t

    def t_ID(self, t):
        r"""[a-zA-Z_][a-zA-Z_0-9]*"""

        # If the value is a reserved name, give it the appropriate type (not ID)
        if t.value in self.reserved:
            t.type = self.reserved[t.value]

        # If it's a function, give it the FUNC type
        elif t.value in self.functions:
            t.type = 'FUNC'

        return t

    def t_INT(self, t):
        r"""\d+"""

        t.value = int(t.value)
        return t

    def t_FLOAT(self, t):
        r"""\d+\.?\d*([eE]-?\d+)?"""

        t.value = float(t.value)
        return t

    def t_error(self, t):
        raise SyntaxError("Illegal character {0} at position {1}".format(t.value[0], t.lexpos))

    def __init__(self):
        self.lexer = lex.lex(module=self)

    def get_names(self, expr):
        self.lexer.input(expr)
        return set(t.value for t in self.lexer if t.type == 'ID')


class Parser(object):
    tokens = Lexer.tokens

    binary_operators = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '**': operator.pow,
        '%': operator.mod,
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
                    | term MOD factor
        """

        p[0] = self.binary_operators[p[2]](p[1], p[3])

    def p_conditional_condition(self, p):
        """
        conditional : condition
        """

        p[0] = p[1]

    def p_condition_expression(self, p):
        """
        condition : expression
        """

        p[0] = p[1]

    def p_expression_term(self, p):
        """
        expression : term
        """

        p[0] = p[1]

    def p_term_factor(self, p):
        """
        term : factor
        """

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
        """
        factor : number
        """

        p[0] = p[1]

    def p_factor_string(self, p):
        """
        factor : STR
        """

        p[0] = p[1]

    def p_factor_bool(self, p):
        """
        factor : TRUE
               | FALSE
        """

        p[0] = True if p[1].lower() == 'true' else False

    def p_factor_conditional(self, p):
        """
        factor : LPAREN conditional RPAREN
        """

        p[0] = p[2]

    def p_number_int(self, p):
        """
        number : INT
        """

        p[0] = p[1]

    def p_number_float(self, p):
        """
        number : FLOAT
        """

        p[0] = p[1]

    def p_factor_id(self, p):
        """
        factor : ID
        """

        try:
            p[0] = self.context[p[1]]
        except KeyError:
            raise NameError("name '{}' is not defined".format(p[1]))

    def p_factor_fn(self, p):
        """
        factor : fn
        """

        p[0] = p[1]

    def p_fn(self, p):
        """
        fn : FUNC LPAREN arguments RPAREN
        """

        fn = getattr(self, 'fn_{0}'.format(p[1]))
        p[0] = fn(*p[3])

    def p_arguments(self, p):
        """
        arguments : conditional COMMA arguments
        """

        p[0] = p[3] + p[1]

    def p_arguments_conditional(self, p):
        """
        arguments : conditional
        """

        p[0] = [p[1]]

    def _to_ndarray(self, a):
        """Casts Python lists and tuples to a numpy array or raises an AssertionError."""

        if isinstance(a, (list, tuple)):
            a = numpy.array(a)

        if not is_ndarray(a):
            raise ValueError("Expected an ndarray but got object of type '{}' instead".format(type(a)))

        return a

    def fn_abs(self, value):
        """
        Return the absolute value of a number.

        :param value: The number.
        :return: The absolute value of the number.
        """

        if is_ndarray(value):
            return numpy.absolute(value)
        else:
            return abs(value)

    def fn_min(self, a):
        """
        Return the minimum of an array, ignoring any NaNs.

        :param a: The array.
        :return: The minimum value of the array.
        """

        return numpy.nanmin(self._to_ndarray(a))

    def fn_max(self, a):
        """
        Return the maximum of an array, ignoring any NaNs.

        :param a: The array.
        :return: The maximum value of the array
        """

        return numpy.nanmax(self._to_ndarray(a))

    def fn_median(self, a):
        """
        Compute the median of an array, ignoring NaNs.

        :param a: The array.
        :return: The median value of the array.
        """

        return numpy.nanmedian(self._to_ndarray(a))

    def fn_mean(self, a):
        """
        Compute the arithmetic mean of an array, ignoring NaNs.

        :param a: The array.
        :return: The arithmetic mean of the array.
        """

        return numpy.nanmean(self._to_ndarray(a))

    def fn_std(self, a):
        """
        Compute the standard deviation of an array, ignoring NaNs.

        :param a: The array.
        :return: The standard deviation of the array.
        """

        return numpy.nanstd(self._to_ndarray(a))

    def fn_var(self, a):
        """
        Compute the variance of an array, ignoring NaNs.

        :param a: The array.
        :return: The variance of the array.
        """

        return numpy.nanvar(self._to_ndarray(a))

    def p_error(self, p):
        if p:
            raise SyntaxError("Syntax error '{0}' at position {1}".format(p.value, p.lexpos))
        else:
            raise SyntaxError("Invalid syntax at end of statement")

    def __init__(self):
        self.context = {}
        self.lexer = Lexer().lexer
        self.parser = yacc.yacc(module=self)

    def evaluate(self, expr, context={}):
        self.context = context
        return self.parser.parse(expr, lexer=self.lexer)
