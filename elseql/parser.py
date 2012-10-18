#!/usr/bin/env python

from __future__ import print_function
from pyparsing import *

class Operator(object):
    name = '<UnknownOperator>'

    def __repr__(self):
        return "(%s %s)" % (self.name, self.operands)

    def __init__(self, operands):
        self.operands = operands

    def op(self, i):
        return self.val(self.operands[i])

    def val(self, x):
        if isinstance(x, basestring):
            return x  # escape Lucene characters?
        elif isinstance(x, bool):
            return "true" if x else "false"
        else:
            return str(x)

class BinaryOperator(Operator):
    def __init__(self, operands):
        self.name = operands[1]
        self.operands = [ operands[0], operands[2] ]

    def __str__(self):
        if self.name == '=':
            return "%s:%s" % (self.operands[0], self.op(1))
        elif self.name in ['<=', 'LTE', 'LE']:
            return "%s:[* TO %s]" % (self.operands[0], self.op(1))
        elif self.name in ['>=', 'GTE', 'GE']:
            return "%s:[%s TO *]" % (self.operands[0], self.op(1))
        elif self.name in ['<', 'LT']:
            return "%s:{* TO %s}" % (self.operands[0], self.op(1))
        elif self.name in ['>', 'GT']:
            return "%s:{%s TO *}" % (self.operands[0], self.op(1))
        else:
            return "%s %s %s" % (self.operands[0], self.name, self.op(1))

class LikeOperator(Operator):
    name = 'LIKE'
    
    def __str__(self):
        return "%s:%s" % (self.operands[0], self.operands[1].replace('*','\*').replace('%','*'))

class BetweenOperator(Operator):
    name = 'BETWEEN'

    def __str__(self):
        return "%s:[%s TO %s]" % (self.operands[0], self.op(1), self.op(2))

class InOperator(Operator):
    name = 'IN'
    
    def __init__(self, operands):
        self.operands = [operands[0], operands[1:]]

    def __str__(self):
        return "%s:(%s)" % (self.operands[0], ' OR '.join([self.val(x) for x in self.operands[1]]))

class AndOperator(Operator):
    def __init__(self, operands=None):
        self.name = 'AND'
        self.operands = [x for x in operands[0] if not isinstance(x, basestring)]

    def __str__(self):
        return ' AND '.join([self.val(x) for x in self.operands])

class OrOperator(Operator):
    def __init__(self, operands=None):
        self.name = 'OR'
        self.operands = [x for x in operands[0] if not isinstance(x, basestring)]

    def __str__(self):
        return ' OR '.join([self.val(x) for x in self.operands])

class NotOperator(Operator):
    def __init__(self, operands=None):
        self.name = 'NOT'
        self.operands = [operands[0][1]]

    def __str__(self):
        return "NOT %s" % self.operands[0]

class QueryFilter(Operator):
    def __init__(self, operands=None):
        self.name = "query"
        self.operands = [ operands[0] ]

    def __str__(self):
        return self.operands[0]

class ExistFilter(Operator):
    def __init__(self, operands=None):
        self.name = "exists"
        self.operands = [ operands[0] ]

    def __str__(self):
        return self.operands[0]

class MissingFilter(Operator):
    def __init__(self, operands=None):
        self.name = "missing"
        self.operands = [ operands[0] ]

    def __str__(self):
        return self.operands[0]

def makeGroupObject(cls):
    def groupAction(s,loc,tokens):
        #print("GROUPACTION %s" % tokens)
        return cls(tokens)
    return groupAction

def invalidSyntax(s, loc, token):
    raise ParseFatalException(s, loc, "Invalid Syntax")

def intValue(t):
    return int(t)

def floatValue(t):
    return float(t)

def boolValue(t):
    return t.lower() == 'true'

def makeAtomObject(fn):
    def atomAction(s, loc, tokens):
        try:
            return fn(tokens[0])
        except:
            return fn(tokens)
    return atomAction

class ElseParserException(ParseBaseException):
    pass

class ElseParser(object):
    # define SQL tokens
    selectStmt   = Forward()
    selectToken  = CaselessKeyword("SELECT")
    facetToken   = CaselessKeyword("FACETS")
    scriptToken  = CaselessKeyword("SCRIPT")
    fromToken    = CaselessKeyword("FROM")
    whereToken   = CaselessKeyword("WHERE")
    orderbyToken = CaselessKeyword("ORDER BY")
    limitToken   = CaselessKeyword("LIMIT")
    between      = CaselessKeyword("BETWEEN")
    likeop       = CaselessKeyword("LIKE")
    in_          = CaselessKeyword("IN")
    and_         = CaselessKeyword("AND")
    or_          = CaselessKeyword("OR")
    not_         = CaselessKeyword("NOT")

    filterToken  = CaselessKeyword("FILTER")
    queryToken   = CaselessKeyword("QUERY")
    existToken   = CaselessKeyword("EXIST")
    missingToken = CaselessKeyword("MISSING")

    ident          = Word( alphas + "_", alphanums + "_$" ).setName("identifier")
    columnName     = delimitedList( ident, ".", combine=True )
    columnNameList = Group( delimitedList( columnName ) )
    indexName      = delimitedList( ident, ".", combine=True )

    #likeExpression fore SQL LIKE expressions
    likeExpr       = quotedString.setParseAction( removeQuotes )

    E      = CaselessLiteral("E")
    binop  = oneOf("= >= <= < > <> != LT LTE LE GT GTE GE", caseless=True)
    lpar   = Suppress("(")
    rpar   = Suppress(")")
    comma  = Suppress(",")

    arithSign = Word("+-",exact=1)

    realNum = Combine( 
        Optional(arithSign) +
        ( Word( nums ) + "." + Optional( Word(nums) ) | ( "." + Word(nums) ) ) +
        Optional( E + Optional(arithSign) + Word(nums) ) ) \
            .setParseAction(makeAtomObject(floatValue))

    intNum = Combine( Optional(arithSign) + Word( nums ) + 
        Optional( E + Optional("+") + Word(nums) ) ) \
            .setParseAction(makeAtomObject(intValue))

    boolean = oneOf("true false", caseless=True) \
        .setParseAction(makeAtomObject(boolValue))

    columnRval = realNum | intNum | boolean | quotedString.setParseAction( removeQuotes )

    whereCondition = ( columnName + binop + columnRval ) \
            .setParseAction(makeGroupObject(BinaryOperator)) \
       | ( columnName + in_.suppress() + lpar + delimitedList( columnRval ) + rpar ).setParseAction(makeGroupObject(InOperator)) \
       | ( columnName + between.suppress() + columnRval + and_.suppress() + columnRval ).setParseAction(makeGroupObject(BetweenOperator)) \
       | ( columnName + likeop.suppress() + likeExpr  ).setParseAction(makeGroupObject(LikeOperator)) \
       | Empty().setParseAction(invalidSyntax)

    boolOperand = whereCondition | boolean

    whereExpression = quotedString.setParseAction( removeQuotes ) \
        | operatorPrecedence( boolOperand,
            [
                (not_, 1, opAssoc.RIGHT, NotOperator),
                (or_,  2, opAssoc.LEFT,  OrOperator),
                (and_, 2, opAssoc.LEFT,  AndOperator),
            ])

    filterExpression = (queryToken.suppress() + whereExpression.setResultsName("query")).setParseAction(makeGroupObject(QueryFilter)) \
        | (existToken.suppress() + columnName).setParseAction(makeGroupObject(ExistFilter)) \
        | (missingToken.suppress() + columnName).setParseAction(makeGroupObject(MissingFilter))

    orderseq  = oneOf("asc desc", caseless=True)
    orderList = delimitedList( 
        Group( columnName + Optional(orderseq, default="asc") ) )

    limitoffset = intNum
    limitcount  = intNum

    #selectExpr  = ( 'count(*)' | columnNameList | '*' )
    selectExpr  = ( columnNameList | '*' )
    facetExpr = columnNameList
    scriptExpr = columnName + Suppress("=") + quotedString.setParseAction( removeQuotes )

    # define the grammar
    selectStmt << ( selectToken + 
        selectExpr.setResultsName( "fields" ) + 
        Optional(facetToken + facetExpr.setResultsName( "facets" )) +
        Optional(scriptToken + scriptExpr.setResultsName( "script" )) +
        fromToken + indexName.setResultsName( "index" ) +
        Optional(whereToken + whereExpression.setResultsName("query")) +
        Optional(filterToken + filterExpression.setResultsName("filter")) +
        Optional(orderbyToken + orderList.setResultsName("order")) + 
        Optional(limitToken +Group( Optional(limitoffset + comma) + limitcount ).setResultsName("limit"))
       )

    grammar_parser = selectStmt

    @staticmethod
    def parse(stmt, debug=False):
        ElseParser.grammar_parser.setDebug(debug)

        try:
            return ElseParser.grammar_parser.parseString(stmt, parseAll=True)
        except (ParseException, ParseFatalException) as err:
            raise ElseParserException(err.pstr, err.loc, err.msg, err.parserElement)

    @staticmethod
    def test(stmt):
        print("STATEMENT: ", stmt)
        print()

        try:
            response = ElseParser.parse(stmt)
            print("index  = ", response.index)
            print("fields = ", response.fields)
            print("query  = ", response.query)
            print("script = ", response.script)
            print("filter = ", response.filter)
            print("order  = ", response.order)
            print("limit  = ", response.limit)
            print("facets = ", response.facets)

        except ElseParserException as err:
            print(err.pstr)
            print(" "*err.loc + "^\n" + err.msg)
            print("ERROR:", err)

        print()

if __name__ == '__main__':
    import sys

    stmt = " ".join(sys.argv[1:])
    ElseParser.test(stmt)
