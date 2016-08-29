import logging
import operator

import math

import numpy
import six
import time
from ply import lex, yacc
from rasterio.dtypes import is_ndarray

logger = logging.getLogger(__name__)


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

    functions = {
        'abs', 'get_mask', 'min', 'mask', 'max', 'median', 'mean', 'std', 'var', 'floor', 'ceil', 'int', 'int8',
        'int16', 'int32', 'int64', 'float', 'float16', 'float32', 'float64'
    }

    tokens = [
        'COMMA', 'STR', 'ID', 'INT', 'FLOAT', 'ADD', 'SUB', 'POW', 'MUL', 'DIV', 'MOD', 'AND', 'OR', 'EQ', 'LTE', 'GTE',
        'LT', 'GT', 'LPAREN', 'RPAREN', 'LBRACK', 'RBRACK', 'TRUE', 'FALSE', 'FUNC'
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
    t_LBRACK = r'\['
    t_RBRACK = r'\]'
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

    def t_FLOAT(self, t):
        r"""(\d+\.\d*([eE]-?\d+)?)|(\d*\.\d+([eE]-?\d+)?)"""

        t.value = float(t.value)
        return t

    def t_INT(self, t):
        r"""\d+"""

        t.value = int(t.value)
        return t

    def t_error(self, t):
        raise SyntaxError("Illegal character {0} at position {1}".format(t.value[0], t.lexpos))

    def __init__(self):
        self.lexer = lex.lex(module=self)

    def get_names(self, expr):
        self.lexer.input(expr)
        return set(t.value for t in self.lexer if t.type == 'ID')


def op_and(x, y):
    if is_ndarray(x) and is_ndarray(y):
        return x & y
    return x and y


def op_or(x, y):
    if is_ndarray(x) and is_ndarray(y):
        return x | y
    return x or y


class Parser(object):
    tokens = Lexer.tokens

    binary_operators = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '**': operator.pow,
        '%': operator.mod,
        '&&': op_and,
        '||': op_or,
        'and': op_and,
        'or': op_or,
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

        p[0] = Instruction("op(left, right)", context={'op': self.binary_operators[p[2]], 'left': p[1], 'right': p[3]})

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
        term : SUB factor
             | ADD factor
        """

        p[0] = p[2]
        if p[1] == '-':
            p[0] = Instruction('-x', context={'x': p[0]})

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

        def resolve_id(key, context):
            try:
                return context[key]
            except KeyError:
                raise NameError("name '{}' is not defined".format(key))

        p[0] = Instruction('resolve_id(key, context)', context={
            'resolve_id': resolve_id,
            'key': p[1],
            'context': self.context
        })

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
        p[0] = Instruction('fn(*[x.execute() if isinstance(x, Instruction) else x for x in args])', context={
            'fn': fn,
            'args': p[3],
            'Instruction': Instruction
        })

    def p_arguments(self, p):
        """
        arguments : conditional COMMA arguments
        """

        p[0] = [p[1]] + p[3]

    def p_arguments_conditional(self, p):
        """
        arguments : conditional
        """

        p[0] = [p[1]]

    def p_factor_item(self, p):
        """
        factor : factor LBRACK conditional RBRACK
        """

        def resolve_item(obj, index):
            if is_ndarray(obj) or isinstance(obj, (list, tuple)):
                if not isinstance(index, int):
                    raise TypeError("Not a valid array index: '{}'".format(index))

            elif isinstance(obj, dict):
                if not isinstance(index, (six.string_types, int)):
                    raise TypeError("Not a valid dictionary index: '{}'".format(index))

            else:
                raise TypeError("Object does not support indexing: '{}'".format(type(obj)))

            return obj[index]

        p[0] = Instruction('resolve_item(obj, index)', context={
            'resolve_item': resolve_item,
            'obj': p[1],
            'index': p[3]
        })

    def _to_ndarray(self, a):
        """Casts Python lists and tuples to a numpy array or raises an AssertionError."""

        if isinstance(a, (list, tuple)):
            a = numpy.array(a)

        if not is_ndarray(a):
            raise TypeError("Expected an ndarray but got object of type '{}' instead".format(type(a)))

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

    def fn_get_mask(self, value):
        """
        Return an array mask.

        :param value: The array.
        :return: The array mask.
        """

        value = self._to_ndarray(value)

        if numpy.ma.is_masked(value):
            return value.mask
        else:
            return numpy.zeros(value.shape).astype(bool)

    def fn_min(self, a, axis=None):
        """
        Return the minimum of an array, ignoring any NaNs.

        :param a: The array.
        :return: The minimum value of the array.
        """

        return numpy.nanmin(self._to_ndarray(a), axis=axis)

    def fn_mask(self, a, mask):
        """
        Return a masked version of an array.

        :param a: The array.
        :param mask: The mask.
        :return: A masked array.
        """

        return numpy.ma.masked_where(mask, a)

    def fn_max(self, a, axis=None):
        """
        Return the maximum of an array, ignoring any NaNs.

        :param a: The array.
        :return: The maximum value of the array
        """

        return numpy.nanmax(self._to_ndarray(a), axis=axis)

    def fn_median(self, a, axis=None):
        """
        Compute the median of an array, ignoring NaNs.

        :param a: The array.
        :return: The median value of the array.
        """

        return numpy.nanmedian(self._to_ndarray(a), axis=axis)

    def fn_mean(self, a, axis=None):
        """
        Compute the arithmetic mean of an array, ignoring NaNs.

        :param a: The array.
        :return: The arithmetic mean of the array.
        """

        return numpy.nanmean(self._to_ndarray(a), axis=axis)

    def fn_std(self, a, axis=None):
        """
        Compute the standard deviation of an array, ignoring NaNs.

        :param a: The array.
        :return: The standard deviation of the array.
        """

        return numpy.nanstd(self._to_ndarray(a), axis=axis)

    def fn_var(self, a, axis=None):
        """
        Compute the variance of an array, ignoring NaNs.

        :param a: The array.
        :return: The variance of the array.
        """

        return numpy.nanvar(self._to_ndarray(a), axis=axis)

    def fn_floor(self, value):
        """
        Return the floor of a number. For negative numbers, floor returns a lower value. E.g., `floor(-2.5) == -3`

        :param value: The number.
        :return: The floor of the number.
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return numpy.floor(self._to_ndarray(value))
        else:
            return math.floor(value)

    def fn_ceil(self, value):
        """
        Return the ceiling of a number.

        :param value: The number.
        :return: The ceiling of the number.
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return numpy.ceil(self._to_ndarray(value))
        else:
            return math.ceil(value)

    def fn_int(self, value):
        """
        Return the value cast to an int.

        :param value: The number.
        :return: The number as an int.
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return self._to_ndarray(value).astype('int')
        else:
            return int(value)

    def fn_int8(self, value):
        """
        Return the value cast to an 8-bit signed integer (numpy array) or a Python int (single value)

        :param value: The number or array
        :return: The number or array as int/int8
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return self._to_ndarray(value).astype(numpy.int8)
        else:
            return int(value)

    def fn_int16(self, value):
        """
        Return the value cast to an 16-bit signed integer (numpy array) or a Python int (single value)

        :param value: The number or array
        :return: The number or array as int/int8
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return self._to_ndarray(value).astype(numpy.int16)
        else:
            return int(value)

    def fn_int32(self, value):
        """
        Return the value cast to an 32-bit signed integer (numpy array) or a Python int (single value)

        :param value: The number or array
        :return: The number or array as int/int8
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return self._to_ndarray(value).astype(numpy.int32)
        else:
            return int(value)

    def fn_int32(self, value):
        """
        Return the value cast to an 64-bit signed integer (numpy array) or a Python int (single value)

        :param value: The number or array
        :return: The number or array as int/int8
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return self._to_ndarray(value).astype(numpy.int64)
        else:
            return int(value)

    def fn_float(self, value):
        """
        Return the value cast to a float.

        :param value: The number.
        :return: The number as a float.
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return self._to_ndarray(value).astype('float')
        else:
            return float(value)

    def fn_float16(self, value):
        """
        Return the value cast to a 16-bit float (numpy array) or a Python float (single value).

        :param value: The number.
        :return: The number as a float.
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return self._to_ndarray(value).astype('float16')
        else:
            return float(value)

    def fn_float32(self, value):
        """
        Return the value cast to a 32-bit float (numpy array) or a Python float (single value).

        :param value: The number.
        :return: The number as a float.
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return self._to_ndarray(value).astype('float32')
        else:
            return float(value)

    def fn_float64(self, value):
        """
        Return the value cast to a 64-bit float (numpy array) or a Python float (single value).

        :param value: The number.
        :return: The number as a float.
        """

        if is_ndarray(value) or isinstance(value, (list, tuple)):
            return self._to_ndarray(value).astype('float64')
        else:
            return float(value)

    def p_error(self, p):
        if p:
            raise SyntaxError("Syntax error '{0}' at position {1}".format(p.value, p.lexpos))
        else:
            raise SyntaxError("Invalid syntax at end of statement")

    def __init__(self):
        self.context = {}
        self.parser = yacc.yacc(module=self)
        self.lexer = Lexer().lexer

    def evaluate(self, expr, context={}):
        start = time.time()
        try:
            self.context = context
            result = self.parser.parse(expr, lexer=self.lexer)

            return result.execute() if isinstance(result, Instruction) else result
        finally:
            logger.info('Executed expression in {:.3f} seconds: {}'.format(time.time()-start, expr))
            self.context = {}
            self.parser.parse('1', lexer=self.lexer)  # Clear out references to potentially large objects


class Instruction(object):
    """A compiled statement to be executed by `exec()`"""

    def __init__(self, statement, context={}):
        self.statement = statement
        self.compiled = compile(statement, '<string>', 'eval')
        self.locals = context

    def execute(self):
        context = {k: v.execute() if isinstance(v, Instruction) else v for k, v in six.iteritems(self.locals)}

        try:
            return eval(self.compiled, None, context)
        finally:
            context = None
