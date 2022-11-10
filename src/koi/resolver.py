from collections import deque
from typing import Deque, Dict

from src.koi.interpreter import Interpreter

from .token import Token
from .expr import Assign, Binary, Call, Expr, ExprVisitor, Get, Grouping, Literal, Logical, Set, Super, This, Unary, Variable
from .stmt import Block, Class, Function, If, Print, Return, Stmt, StmtVisitor, Expression, Var, While
from .function_type import FunctionType
from .class_type import ClassType


class Resolver(ExprVisitor, StmtVisitor):
    def __init__(self, interpreter: Interpreter, on_error=None) -> None:
        self.interpreter = interpreter
        self.scopes: Deque[Dict] = deque()
        self.on_error = on_error
        self.current_function = FunctionType.NONE
        self.current_class = ClassType.NONE

    def visit_block_stmt(self, stmt: Block):
        self._begin_scope()
        self.resolve(stmt.statements)
        self._end_scope()
        return None

    def resolve(self, stmts):
        self._resolve_stmts(stmts)

    def _resolve_stmts(self, stmts):
        for stmt in stmts:
            self._resolve_stmt(stmt)

    def _resolve_stmt(self, stmt: Stmt):
        stmt.accept(self)

    def _resolve_expression(self, expr: Expression):
        return expr.accept(self)

    def _resolve_local(self, expr: Expr, name: Token):
        for idx, scope in enumerate(reversed(self.scopes)):
            if name.lexeme in scope:
                self.interpreter.resolve(expr, idx)
                return
        # Not found, assume it's global
    def _begin_scope(self):
        self.scopes.append({})

    def _end_scope(self):
        self.scopes.pop()

    def visit_var_stmt(self, stmt: Var):
        self._declare(stmt.name)
        if stmt.initializer is not None:
            self._resolve_expression(stmt.initializer)
        self._define(stmt.name)
        return None

    def _declare(self, name: Token):
        if len(self.scopes) == 0:
            return
        scope = self.scopes[-1]
        if name.lexeme in scope:
            self.on_error(name, f"Variabled with name {name} already exists in this scope")
        scope[name.lexeme] = False
    
    def _define(self, name: Token):
        if len(self.scopes) == 0:
            return
        scope = self.scopes[-1]
        scope[name.lexeme] = True

    def _resolve_function(self, function: Function, type:  FunctionType):
        enclosing = self.current_function
        self.current_function = type

        self._begin_scope()
        for param in function.params:
            self._declare(param)
            self._define(param)
        self._resolve_stmts(function.body)
        self._end_scope()
        self.current_function = enclosing

    def visit_variable_expr(self, expr: Variable):
        if (len(self.scopes) != 0) and self.scopes[-1].get(expr.name.lexeme) is False:
            self.on_error(expr.name, "Cannot read variable in it's own initializer")
        self._resolve_local(expr, expr.name)

    def visit_assign_expr(self, expr: Assign):
        self._resolve_expression(expr.value)
        self._resolve_local(expr, expr.name)

    def visit_function_stmt(self, stmt: Function):
        self._declare(stmt.name)
        self._define(stmt.name)

        self._resolve_function(stmt)

    def visit_expression_stmt(self, stmt: Expression):
        self._resolve_expression(stmt.expression)

    def visit_if_stmt(self, stmt: If):
        self._resolve_expression(stmt.condition)
        self._resolve_stmt(stmt.then_branch)
        if stmt.else_branch:
            self.resolve(stmt.else_branch)
        
    def visit_print_stmt(self, stmt: Print):
        self._resolve_expression(stmt.expression)

    def visit_return_stmt(self, stmt: Return):
        if self.current_function == FunctionType.NONE:
            self.on_error(stmt.keyword, "Cannot return outside a function")
        if stmt.value:
            if self.current_function == FunctionType.INITIALIZER:
                self.on_error(stmt.keyword, "Cannot return a value from an initializer")
            self._resolve_expression(stmt.value)

    def visit_while_stmt(self, stmt: While):
        self._resolve_expression(stmt.condition)
        self._resolve_stmt(stmt.body)

    def visit_binary_expr(self, expr: Binary):
        self._resolve_expression(expr.left)
        self._resolve_expression(expr.right)

    def visit_call_expr(self, expr: Call):
        self._resolve_expression(expr.callee)
        for arg in expr.arguments:
            self._resolve_expression(arg)

    def visit_grouping_expr(self, expr: Grouping):
        self._resolve_expression(expr.expression)
    
    def visit_literal_expr(self, expr: Literal):
        return None

    def visit_logical_expr(self, expr: Logical):
        self._resolve_expression(expr.left)
        self._resolve_expression(expr.right)


    def visit_unary_expr(self, expr: Unary):
        self._resolve_expression(expr.right)

    def visit_set_expr(self, expr: Set):
        return super().visit_set_expr(expr)

    def visit_this_expr(self, expr: This):
        return super().visit_this_expr(expr)

    def visit_super_expr(self, expr: Super):
        return super().visit_super_expr(expr)

    def visit_class_stmt(self, stmt: Class):
        return super().visit_class_stmt(stmt)

    def visit_get_expr(self, expr: Get):
        return super().visit_get_expr(expr)