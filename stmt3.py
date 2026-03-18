# Kaevin Barta
#

# CS358 Fall'25 Assignment 4 (Part 2)

# Stmt3 - an imperative language with functions
#
#   stmt -> "var" ID "=" expr
#         | ID "=" expr 
#         | "if" "(" expr ")" stmt ["else" stmt]
#         | "while" "(" expr ")" stmt
#         | "print" "(" expr ")"
#         | "{" stmt (";" stmt)* "}" 
#         | "def" ID "(" ID ")" ":" body    
#         | ID "(" expr ")"
#
#   body -> "{" (stmt ";")* "return" expr "}"
#         | "return" expr
#
#   expr -> aexpr "<"  aexpr
#         | aexpr "==" aexpr
#         | aexpr 
#
#   aexpr -> aexpr "+" term
#          | aexpr "-" term
#          | term         
#
#   term -> term "*" atom
#         | term "/" atom
#         | atom
#
#   atom: "(" expr ")"
#         | ID "(" expr ")"
#         | ID
#         | NUM
#
from unicodedata import name

from lark import Lark, v_args
from lark.visitors import Interpreter

grammar = """
  ?start: stmt+

   stmt: "var" ID "=" expr            -> decl
       | ID "=" expr                  -> assign
       | "if" "(" expr ")" stmt ["else" stmt] -> ifstmt
       | "while" "(" expr ")" stmt    -> whstmt
       | "print" "(" expr ")"         -> prstmt
       | "{" stmt (";" stmt)* "}"     -> block      
       | "def" ID "(" ID ")" ":" body -> fdef
       | ID "(" expr ")"              -> call

   body: "{" (stmt ";")* "return" expr "}" -> body
       | "return" expr                -> sbody

  ?expr: aexpr "<"  aexpr  -> less
       | aexpr "==" aexpr  -> equal
       | aexpr 

  ?aexpr: aexpr "+" term  -> add
       |  aexpr "-" term  -> sub
       |  term         

  ?term: term "*" atom  -> mul
       | term "/" atom  -> div
       | atom

  ?atom: "(" expr ")"
       | ID "(" expr ")"  -> call
       | ID               -> var
       | NUM              -> num

  COMMENT: "#" /[^\\n]*/ "\\n"
  %import common.WORD   -> ID
  %import common.INT    -> NUM
  %import common.WS
  %ignore COMMENT
  %ignore WS
"""

parser = Lark(grammar, parser='lalr')

# Variable environment
#
class Env(dict):
    prev = []

    def openScope(self):
        Env.prev.append(self)
        return Env()

    def closeScope(self):
        if not Env.prev:
            raise Exception("No scope to close")
        return Env.prev.pop()

    def extend(self, x, v):
        if x in self:
            raise Exception(f"Variable '{x}' already defined")
        self[x] = v

    def lookup(self, x):
        if x in self:
            return self[x]
        for outer in reversed(Env.prev):
            if x in outer:
                return outer[x]
        raise Exception(f"Variable '{x}' not defined")

    def update(self, x, v):
        if x in self:
            self[x] = v
            return
        for outer in reversed(Env.prev):
            if x in outer:
                outer[x] = v
                return
        raise Exception(f"Variable '{x}' not defined")
  

env = Env()

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

# Closure
#
class Closure():
    def __init__(self,id,body,env):
        self.id = id
        self.body = body
        self.env = env

# Interpreter
#
@v_args(inline=True)
class Eval(Interpreter):
    def num(self, val):  return int(val)

    def var(self, name):
        return env.lookup(str(name))

    def add(self, x, y):
        return self.visit(x) + self.visit(y)

    def sub(self, x, y):
        return self.visit(x) - self.visit(y)

    def mul(self, x, y):
        return self.visit(x) * self.visit(y)

    def div(self, x, y):
        return self.visit(x) // self.visit(y)
    
    def less(self, x, y):
        return 1 if self.visit(x) < self.visit(y) else 0

    def equal(self, x, y):
        return 1 if self.visit(x) == self.visit(y) else 0
    
    def assign(self, name, expr):
        value = self.visit(expr)
        env.update(str(name), value)

    def decl(self, name, expr):
        value = self.visit(expr)
        env.extend(str(name), value)

    def block(self, first, *rest):
        global env
        env = env.openScope()
        try:
            self.visit(first)
            for stmt in rest:
                self.visit(stmt)
        finally:
            env = env.closeScope()
    
    def ifstmt(self, cond, then_stmt, else_stmt=None):
        if self.visit(cond):
            self.visit(then_stmt)
        elif else_stmt:
            self.visit(else_stmt)

    def whstmt(self, cond, body):
        while self.visit(cond):
            self.visit(body)

    def fdef(self, name, param, body):
        closure = Closure(str(param), body, env)
        env.extend(str(name), closure)
    
    def call(self, name, arg):
        global env

        closure = env.lookup(str(name))
        if not isinstance(closure, Closure):
            raise Exception(str(name) + " is not a function")
        
        argval = self.visit(arg)
        
        old_env = env
        env = closure.env.openScope()
        env.extend(closure.id, argval)
        try:
            self.visit(closure.body)
        except ReturnException as e:
            env = env.closeScope()
            env = old_env
            return e.value
        
        env = env.closeScope()
        env = old_env
        return None
    
    def prstmt(self, expr):
        val = self.visit(expr)
        print(val)
    
    def body(self, *parts):
        for stmt in parts[:-1]:
            self.visit(stmt)
        val = self.visit(parts[-1])
        raise ReturnException(val)
    
    def sbody(self, expr):
        val = self.visit(expr)
        raise ReturnException(val)

import sys
def main():
    try:
        prog = sys.stdin.read()
        tree = parser.parse(prog)
        print(prog)
        Eval().visit(tree)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()
