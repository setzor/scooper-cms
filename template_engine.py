"""
Scooper CMS Template Engine

A lexer/parser-based template engine that replaces the regex-based approach.
Provides better security through auto-escaping and proper parsing.

Features:
- Auto-escaping of HTML to prevent XSS vulnerabilities
- Proper lexer/parser architecture (no regex string manipulation)
- Support for: {{ variables }}, {# comments #}, {% include %}, {% for %}, {% if %}
- SafeString support for trusted HTML content
"""

import os
import re
from enum import Enum, auto
from typing import List, Dict, Any, Optional


class SafeString(str):
    """
    A string subclass that indicates the content is safe HTML.
    Values of this type will NOT be escaped by the template engine.
    """
    pass


def escape_html(value):
    """Escape HTML special characters in a string."""
    if value is None:
        return ''
    value = str(value)
    return (value.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))


class TokenType(Enum):
    TEXT = auto()
    VAR_START = auto()    # {{
    VAR_END = auto()      # }}
    TAG_START = auto()    # {%
    TAG_END = auto()      # %}
    COMMENT_START = auto()  # {#
    COMMENT_END = auto()    # #}
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()
    DOT = auto()
    EQUALS = auto()
    NOT_EQUALS = auto()
    GREATER = auto()
    LESS = auto()
    GREATER_EQUAL = auto()
    LESS_EQUAL = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    IN = auto()
    EOF = auto()


class Token:
    __slots__ = ('type', 'value', 'line', 'col')
    def __init__(self, type_: TokenType, value: str, line: int, col: int):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col


class Lexer:
    """Tokenizes template source into tokens."""
    
    def __init__(self, source: str):
        self.source = source
        self.position = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []
        self.state = 'TEXT'  # TEXT, VAR, TAG, COMMENT

    def advance(self, n: int = 1):
        """Advance position by n characters, tracking line/col."""
        for _ in range(n):
            if self.position < len(self.source):
                if self.source[self.position] == '\n':
                    self.line += 1
                    self.col = 1
                else:
                    self.col += 1
                self.position += 1

    def tokenize(self) -> List[Token]:
        """Convert source string into list of tokens."""
        while self.position < len(self.source):
            char = self.source[self.position]
            
            # Check for state transitions
            if self.state == 'TEXT':
                if char == '{' and self.position + 1 < len(self.source):
                    next_char = self.source[self.position + 1]
                    if next_char == '{':
                        self.tokens.append(Token(TokenType.VAR_START, '{{', self.line, self.col))
                        self.state = 'VAR'
                        self.advance(2)
                        continue
                    elif next_char == '%':
                        self.tokens.append(Token(TokenType.TAG_START, '{%', self.line, self.col))
                        self.state = 'TAG'
                        self.advance(2)
                        continue
                    elif next_char == '#':
                        self.tokens.append(Token(TokenType.COMMENT_START, '{#', self.line, self.col))
                        self.state = 'COMMENT'
                        self.advance(2)
                        continue
            
            if self.state in ('VAR', 'TAG', 'COMMENT'):
                # Check for closing delimiters: }}, %}, #}
                if self.position + 1 < len(self.source):
                    next_char = self.source[self.position + 1]
                    # Check for }}
                    if char == '}' and next_char == '}':
                        if self.state == 'VAR':
                            self.tokens.append(Token(TokenType.VAR_END, '}}', self.line, self.col))
                            self.state = 'TEXT'
                            self.advance(2)
                            continue
                    # Check for %}
                    elif char == '%' and next_char == '}':
                        if self.state == 'TAG':
                            self.tokens.append(Token(TokenType.TAG_END, '%}', self.line, self.col))
                            self.state = 'TEXT'
                            self.advance(2)
                            continue
                    # Check for #}
                    elif char == '#' and next_char == '}':
                        if self.state == 'COMMENT':
                            self.tokens.append(Token(TokenType.COMMENT_END, '#}', self.line, self.col))
                            self.state = 'TEXT'
                            self.advance(2)
                            continue
            
            # Process based on state
            if self.state == 'TEXT':
                self._tokenize_text()
            elif self.state == 'VAR':
                self._tokenize_var_content()
            elif self.state == 'TAG':
                self._tokenize_tag_content()
            elif self.state == 'COMMENT':
                self._tokenize_comment_content()
        
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.col))
        return self.tokens
    
    def _tokenize_text(self):
        """Accumulate all characters until we hit a template delimiter."""
        start_line, start_col = self.line, self.col
        value = ''
        while self.position < len(self.source):
            char = self.source[self.position]
            # Check if we're at the start of a template delimiter
            if char == '{' and self.position + 1 < len(self.source):
                next_char = self.source[self.position + 1]
                if next_char in ('{', '%', '#'):
                    break
            # Accumulate the character
            value += char
            if char == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.advance()
        if value:
            self.tokens.append(Token(TokenType.TEXT, value, start_line, start_col))
    
    def _tokenize_var_content(self):
        """Tokenize content inside {{ }} - variable expressions."""
        # In VAR state, we expect identifiers and dots for nested access
        # Skip whitespace
        while self.position < len(self.source) and self.source[self.position] in ' \t':
            self.advance()
        
        if self.position >= len(self.source):
            return
        
        char = self.source[self.position]
        
        # Check if we're at a closing delimiter - if so, return to let main loop handle it
        if char == '}' or char == '{':
            return
        
        if char.isalpha() or char == '_':
            self._tokenize_identifier()
        elif char == '.':
            self.tokens.append(Token(TokenType.DOT, '.', self.line, self.col))
            self.advance()
        else:
            # Skip unexpected characters
            self.advance()
    
    def _tokenize_tag_content(self):
        """Tokenize content inside {% %} - tag syntax."""
        # Skip whitespace
        while self.position < len(self.source) and self.source[self.position] in ' \t':
            self.advance()
        
        if self.position >= len(self.source):
            return
        
        char = self.source[self.position]
        
        # Check if we're at a closing delimiter - if so, return to let main loop handle it
        if char == '}' or char == '{' or char == '%':
            return
        
        if char.isalpha() or char == '_':
            self._tokenize_identifier()
        elif char in ('"', "'"):
            self._tokenize_string()
        elif char.isdigit():
            self._tokenize_number()
        elif char == '.':
            self.tokens.append(Token(TokenType.DOT, '.', self.line, self.col))
            self.advance()
        elif char in ('=', '!', '<', '>'):
            self._tokenize_comparison(char)
        else:
            # Skip unexpected characters (including whitespace newlines)
            if char == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.advance()
    
    def _tokenize_comment_content(self):
        """Skip content inside {# #} comments."""
        while self.position < len(self.source):
            char = self.source[self.position]
            if char == '{' and self.position + 1 < len(self.source):
                next_char = self.source[self.position + 1]
                if next_char == '#':
                    # Nested comment - skip
                    self.advance(2)
                    continue
            if char == '#' and self.position + 1 < len(self.source):
                next_char = self.source[self.position + 1]
                if next_char == '}':
                    # End of comment - will be handled by state transition
                    break
            if char == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.advance()
        # After breaking from loop, we need to return so main loop can handle the delimiter
        return
    
    def _tokenize_identifier(self):
        """Tokenize an identifier or keyword."""
        start_line, start_col = self.line, self.col
        value = ''
        while self.position < len(self.source):
            char = self.source[self.position]
            if char.isalnum() or char == '_':
                value += char
                self.advance()
            else:
                break
        self.tokens.append(Token(TokenType.IDENTIFIER, value, start_line, start_col))
    
    def _tokenize_string(self):
        """Tokenize a string literal."""
        quote_char = self.source[self.position]
        start_line, start_col = self.line, self.col
        self.advance()  # Skip opening quote
        value = ''
        while self.position < len(self.source):
            char = self.source[self.position]
            if char == quote_char:
                self.advance()  # Skip closing quote
                self.tokens.append(Token(TokenType.STRING, value, start_line, start_col))
                return
            if char == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            value += char
            self.advance()
        # Unclosed string
        self.tokens.append(Token(TokenType.STRING, value, start_line, start_col))
    
    def _tokenize_number(self):
        """Tokenize a number."""
        start_line, start_col = self.line, self.col
        value = ''
        while self.position < len(self.source):
            char = self.source[self.position]
            if char.isdigit() or char == '.':
                value += char
                self.advance()
            else:
                break
        self.tokens.append(Token(TokenType.NUMBER, value, start_line, start_col))
    
    def _tokenize_comparison(self, first_char: str):
        """Tokenize comparison operators."""
        start_line, start_col = self.line, self.col
        if self.position + 1 < len(self.source):
            second_char = self.source[self.position + 1]
            combined = first_char + second_char
            token_map = {
                '==': TokenType.EQUALS,
                '!=': TokenType.NOT_EQUALS,
                '>=': TokenType.GREATER_EQUAL,
                '<=': TokenType.LESS_EQUAL,
            }
            if combined in token_map:
                self.tokens.append(Token(token_map[combined], combined, start_line, start_col))
                self.advance(2)
                return
        token_map2 = {
            '=': TokenType.EQUALS,
            '>': TokenType.GREATER,
            '<': TokenType.LESS,
            '!': TokenType.NOT,
        }
        self.tokens.append(Token(token_map2.get(first_char, TokenType.TEXT), first_char, start_line, start_col))
        self.advance()


class ASTNode:
    """Base class for all AST nodes."""
    def __init__(self, line: int, col: int):
        self.line = line
        self.col = col
    
    def render(self, context: Dict[str, Any], engine: 'TemplateEngine') -> str:
        raise NotImplementedError


class TextNode(ASTNode):
    """Represents plain text in the template."""
    def __init__(self, text: str, line: int, col: int):
        super().__init__(line, col)
        self.text = text
    
    def render(self, context: Dict[str, Any], engine: 'TemplateEngine') -> str:
        return self.text


class VariableNode(ASTNode):
    """Represents a variable reference like {{ variable }} or {{ obj.property }}."""
    def __init__(self, name: str, line: int, col: int):
        super().__init__(line, col)
        self.name = name
    
    def render(self, context: Dict[str, Any], engine: 'TemplateEngine') -> str:
        value = engine.get_context_value(self.name, context)
        # Auto-escape unless it's a SafeString
        if isinstance(value, SafeString):
            return str(value)
        return escape_html(str(value))


class CommentNode(ASTNode):
    """Represents a comment like {# comment #}."""
    def __init__(self, text: str, line: int, col: int):
        super().__init__(line, col)
        self.text = text
    
    def render(self, context: Dict[str, Any], engine: 'TemplateEngine') -> str:
        return ''


class IncludeNode(ASTNode):
    """Represents an include directive like {% include template %}."""
    def __init__(self, template_name: str, line: int, col: int):
        super().__init__(line, col)
        self.template_name = template_name
    
    def render(self, context: Dict[str, Any], engine: 'TemplateEngine') -> str:
        return engine.render_template(self.template_name, context)


class ForLoopNode(ASTNode):
    """Represents a for loop like {% for item in list %}...{% endfor %}."""
    def __init__(self, loop_var: str, iterable: str, body: List[ASTNode], 
                 line: int, col: int, else_body: Optional[List[ASTNode]] = None):
        super().__init__(line, col)
        self.loop_var = loop_var
        self.iterable = iterable
        self.body = body
        self.else_body = else_body or []
    
    def render(self, context: Dict[str, Any], engine: 'TemplateEngine') -> str:
        items = engine.get_context_value(self.iterable, context)
        if not items or not isinstance(items, (list, tuple)):
            # Render else body if it exists
            result = []
            for node in self.else_body:
                result.append(node.render(context, engine))
            return ''.join(result)
        
        output = []
        for idx, item in enumerate(items):
            loop_ctx = context.copy()
            loop_ctx[self.loop_var] = item
            loop_ctx['loop'] = {
                'index': idx + 1,
                'index0': idx,
                'first': idx == 0,
                'last': idx == len(items) - 1,
            }
            for node in self.body:
                output.append(node.render(loop_ctx, engine))
        return ''.join(output)


class IfNode(ASTNode):
    """Represents an if statement like {% if condition %}...{% endif %}."""
    def __init__(self, condition: 'ConditionNode', body: List[ASTNode],
                 line: int, col: int, elif_branches: Optional[List] = None,
                 else_body: Optional[List[ASTNode]] = None):
        super().__init__(line, col)
        self.condition = condition
        self.body = body
        self.elif_branches = elif_branches or []
        self.else_body = else_body or []
    
    def render(self, context: Dict[str, Any], engine: 'TemplateEngine') -> str:
        if self.condition.evaluate(context, engine):
            return ''.join(node.render(context, engine) for node in self.body)
        
        for condition, elif_body in self.elif_branches:
            if condition.evaluate(context, engine):
                return ''.join(node.render(context, engine) for node in elif_body)
        
        return ''.join(node.render(context, engine) for node in self.else_body)


class ConditionNode(ASTNode):
    """Represents a condition in an if statement."""
    def __init__(self, left: ASTNode, operator: TokenType, right: Optional[ASTNode] = None,
                 line: int = 0, col: int = 0):
        super().__init__(line, col)
        self.left = left
        self.operator = operator
        self.right = right
    
    def _compare_values(self, left: Any, right: Any, comparator) -> bool:
        """Compare two values with type conversion."""
        # Try numeric comparison first
        try:
            left_num = float(left) if left is not None else 0
            right_num = float(right) if right is not None else 0
            return comparator(left_num, right_num)
        except (ValueError, TypeError):
            # Fall back to string comparison
            return comparator(str(left), str(right))
    
    def evaluate(self, context: Dict[str, Any], engine: 'TemplateEngine') -> bool:
        left_val = self._get_value(self.left, context, engine)
        
        if self.operator == TokenType.NOT:
            return not bool(left_val)
        
        if self.right is None:
            return bool(left_val)
        
        right_val = self._get_value(self.right, context, engine)
        
        if self.operator == TokenType.EQUALS:
            return str(left_val) == str(right_val)
        elif self.operator == TokenType.NOT_EQUALS:
            return str(left_val) != str(right_val)
        elif self.operator == TokenType.GREATER:
            return self._compare_values(left_val, right_val, lambda a, b: a > b)
        elif self.operator == TokenType.LESS:
            return self._compare_values(left_val, right_val, lambda a, b: a < b)
        elif self.operator == TokenType.GREATER_EQUAL:
            return self._compare_values(left_val, right_val, lambda a, b: a >= b)
        elif self.operator == TokenType.LESS_EQUAL:
            return self._compare_values(left_val, right_val, lambda a, b: a <= b)
        elif self.operator == TokenType.IN:
            if isinstance(right_val, (list, tuple)):
                return left_val in right_val
            return str(left_val) in str(right_val)
        
        return bool(left_val)
    
    def _get_value(self, node: ASTNode, context: Dict[str, Any], engine: 'TemplateEngine') -> Any:
        if isinstance(node, VariableNode):
            return engine.get_context_value(node.name, context)
        if isinstance(node, TextNode):
            val = node.text
            if val.isdigit():
                return int(val)
            if val.replace('.', '', 1).isdigit():
                return float(val)
            if val.lower() == 'true':
                return True
            if val.lower() == 'false':
                return False
            return val
        return None


class Parser:
    """Parses tokens into an AST."""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.current_token: Optional[Token] = None
        self.advance()

    def advance(self):
        """Move to next token."""
        if self.position < len(self.tokens):
            self.current_token = self.tokens[self.position]
            self.position += 1
        else:
            self.current_token = Token(TokenType.EOF, '', 0, 0)

    def parse(self) -> List[ASTNode]:
        """Parse all tokens into a list of AST nodes."""
        nodes: List[ASTNode] = []
        while self.current_token.type != TokenType.EOF:
            node = self.parse_statement()
            if node:
                nodes.append(node)
        return nodes

    def parse_statement(self) -> Optional[ASTNode]:
        """Parse a single statement (text, variable, comment, or tag)."""
        token = self.current_token
        
        if token.type == TokenType.TEXT:
            start_token = token
            text = token.value
            self.advance()
            # Accumulate consecutive text tokens
            while self.current_token.type == TokenType.TEXT:
                text += self.current_token.value
                self.advance()
            return TextNode(text, start_token.line, start_token.col)
        
        if token.type == TokenType.VAR_START:
            return self.parse_variable()
        
        if token.type == TokenType.COMMENT_START:
            return self.parse_comment()
        
        if token.type == TokenType.TAG_START:
            return self.parse_tag()
        
        self.advance()
        return None

    def parse_variable(self) -> VariableNode:
        """Parse {{ variable }}."""
        start_token = self.current_token
        self.advance()  # Skip VAR_START
        
        # Collect identifier parts separated by dots
        name_parts = []
        while self.current_token.type not in (TokenType.VAR_END, TokenType.EOF):
            if self.current_token.type == TokenType.IDENTIFIER:
                name_parts.append(self.current_token.value)
                self.advance()
            elif self.current_token.type == TokenType.DOT:
                name_parts.append('.')
                self.advance()
            else:
                # Unexpected token in variable - skip it
                self.advance()
        
        name = ''.join(name_parts)
        
        if self.current_token.type == TokenType.VAR_END:
            self.advance()  # Skip VAR_END
        
        return VariableNode(name, start_token.line, start_token.col)

    def parse_comment(self) -> CommentNode:
        """Parse {# comment #}."""
        start_token = self.current_token
        self.advance()  # Skip COMMENT_START
        
        text_parts = []
        while self.current_token.type not in (TokenType.COMMENT_END, TokenType.EOF):
            text_parts.append(self.current_token.value)
            self.advance()
        
        text = ''.join(text_parts)
        
        if self.current_token.type == TokenType.COMMENT_END:
            self.advance()  # Skip COMMENT_END
        
        return CommentNode(text, start_token.line, start_token.col)

    def parse_tag(self) -> ASTNode:
        """Parse {% ... %} tags."""
        start_token = self.current_token
        self.advance()  # Skip TAG_START
        
        # Skip whitespace
        while self.current_token.type == TokenType.TEXT and self.current_token.value.isspace():
            self.advance()
        
        if self.current_token.type == TokenType.EOF:
            return TextNode('', start_token.line, start_token.col)
        
        # Check what kind of tag
        if self.current_token.type == TokenType.IDENTIFIER:
            tag_name = self.current_token.value
            self.advance()
            
            if tag_name == 'include':
                return self.parse_include_tag(start_token)
            elif tag_name == 'for':
                return self.parse_for_tag(start_token)
            elif tag_name == 'if':
                return self.parse_if_tag(start_token)
            elif tag_name == 'endif':
                # Skip to end
                while self.current_token.type != TokenType.TAG_END:
                    self.advance()
                if self.current_token.type == TokenType.TAG_END:
                    self.advance()
                return TextNode('', start_token.line, start_token.col)
            elif tag_name == 'endfor':
                while self.current_token.type != TokenType.TAG_END:
                    self.advance()
                if self.current_token.type == TokenType.TAG_END:
                    self.advance()
                return TextNode('', start_token.line, start_token.col)
            elif tag_name == 'else':
                while self.current_token.type != TokenType.TAG_END:
                    self.advance()
                if self.current_token.type == TokenType.TAG_END:
                    self.advance()
                return TextNode('', start_token.line, start_token.col)
            elif tag_name == 'elif':
                while self.current_token.type != TokenType.TAG_END:
                    self.advance()
                if self.current_token.type == TokenType.TAG_END:
                    self.advance()
                return TextNode('', start_token.line, start_token.col)
        
        # Skip until tag end
        while self.current_token.type not in (TokenType.TAG_END, TokenType.EOF):
            self.advance()
        
        if self.current_token.type == TokenType.TAG_END:
            self.advance()
        
        return TextNode('', start_token.line, start_token.col)

    def parse_include_tag(self, start_token: Token) -> IncludeNode:
        """Parse {% include template_name %}."""
        # Skip whitespace
        while self.current_token.type == TokenType.TEXT and self.current_token.value.isspace():
            self.advance()
        
        template_name = ''
        if self.current_token.type in (TokenType.IDENTIFIER, TokenType.STRING):
            template_name = self.current_token.value
            self.advance()
        
        # Skip until tag end
        while self.current_token.type not in (TokenType.TAG_END, TokenType.EOF):
            self.advance()
        
        if self.current_token.type == TokenType.TAG_END:
            self.advance()
        
        return IncludeNode(template_name, start_token.line, start_token.col)

    def parse_for_tag(self, start_token: Token) -> ForLoopNode:
        """Parse {% for item in list %}...{% endfor %}."""
        # Parse: for <var> in <iterable>
        loop_var = ''
        iterable = ''
        
        # Skip whitespace
        while self.current_token.type == TokenType.TEXT and self.current_token.value.isspace():
            self.advance()
        
        if self.current_token.type == TokenType.IDENTIFIER:
            loop_var = self.current_token.value
            self.advance()
        
        # Skip 'in'
        while self.current_token.type == TokenType.TEXT and self.current_token.value.isspace():
            self.advance()
        
        if self.current_token.type == TokenType.IDENTIFIER and self.current_token.value == 'in':
            self.advance()
        
        # Skip whitespace
        while self.current_token.type == TokenType.TEXT and self.current_token.value.isspace():
            self.advance()
        
        if self.current_token.type == TokenType.IDENTIFIER:
            iterable = self.current_token.value
            self.advance()
        
        # Skip until tag end
        while self.current_token.type != TokenType.TAG_END:
            self.advance()
        
        if self.current_token.type == TokenType.TAG_END:
            self.advance()
        
        # Parse body until {% endfor %}
        body: List[ASTNode] = []
        else_body: List[ASTNode] = []
        in_else = False
        
        while self.current_token.type != TokenType.EOF:
            if self.current_token.type == TokenType.TAG_START:
                self.advance()
                if self.current_token.type == TokenType.IDENTIFIER:
                    tag = self.current_token.value
                    self.advance()
                    # Skip to tag end
                    while self.current_token.type != TokenType.TAG_END:
                        self.advance()
                    if self.current_token.type == TokenType.TAG_END:
                        self.advance()
                    
                    if tag == 'endfor':
                        break
                    elif tag == 'else':
                        in_else = True
                        continue
                continue
            
            node = self.parse_statement()
            if node:
                if in_else:
                    else_body.append(node)
                else:
                    body.append(node)
        
        return ForLoopNode(loop_var, iterable, body, start_token.line, start_token.col, else_body)

    def parse_if_tag(self, start_token: Token) -> IfNode:
        """Parse {% if condition %}...{% endif %}."""
        condition = self.parse_condition()
        
        # Skip to tag end
        while self.current_token.type != TokenType.TAG_END:
            self.advance()
        
        if self.current_token.type == TokenType.TAG_END:
            self.advance()
        
        # Parse body
        body: List[ASTNode] = []
        elif_branches: List = []
        else_body: List[ASTNode] = []
        in_elif = False
        in_else = False
        
        while self.current_token.type != TokenType.EOF:
            if self.current_token.type == TokenType.TAG_START:
                self.advance()
                if self.current_token.type == TokenType.IDENTIFIER:
                    tag = self.current_token.value
                    self.advance()
                    # Skip to tag end
                    while self.current_token.type != TokenType.TAG_END:
                        self.advance()
                    if self.current_token.type == TokenType.TAG_END:
                        self.advance()
                    
                    if tag == 'endif':
                        break
                    elif tag == 'elif':
                        in_elif = True
                        elif_condition = self.parse_condition()
                        # Skip to tag end
                        while self.current_token.type != TokenType.TAG_END:
                            self.advance()
                        if self.current_token.type == TokenType.TAG_END:
                            self.advance()
                        elif_body_nodes: List[ASTNode] = []
                        # Parse elif body
                        while self.current_token.type != TokenType.EOF:
                            if self.current_token.type == TokenType.TAG_START:
                                self.advance()
                                if self.current_token.type == TokenType.IDENTIFIER:
                                    next_tag = self.current_token.value
                                    self.advance()
                                    while self.current_token.type != TokenType.TAG_END:
                                        self.advance()
                                    if self.current_token.type == TokenType.TAG_END:
                                        self.advance()
                                    if next_tag in ('elif', 'else', 'endif'):
                                        break
                                continue
                            node = self.parse_statement()
                            if node:
                                elif_body_nodes.append(node)
                        elif_branches.append((elif_condition, elif_body_nodes))
                        continue
                    elif tag == 'else':
                        in_else = True
                        continue
                continue
            
            node = self.parse_statement()
            if node:
                if in_else:
                    else_body.append(node)
                elif in_elif:
                    pass
                else:
                    body.append(node)
        
        return IfNode(condition, body, start_token.line, start_token.col, elif_branches, else_body)

    def parse_condition(self) -> ConditionNode:
        """Parse a condition expression."""
        left = self.parse_primary()
        
        # Check for unary not
        if self.current_token.type == TokenType.IDENTIFIER and self.current_token.value == 'not':
            self.advance()
            right = self.parse_primary()
            return ConditionNode(left, TokenType.NOT, right, self.current_token.line, self.current_token.col)
        
        # Check for binary operators
        if self.current_token.type in (TokenType.EQUALS, TokenType.NOT_EQUALS, TokenType.GREATER,
                                        TokenType.LESS, TokenType.GREATER_EQUAL, TokenType.LESS_EQUAL,
                                        TokenType.IN):
            operator = self.current_token.type
            self.advance()
            right = self.parse_primary()
            return ConditionNode(left, operator, right, self.current_token.line, self.current_token.col)
        
        # Single value condition
        return ConditionNode(left, TokenType.IDENTIFIER, None, self.current_token.line, self.current_token.col)

    def parse_primary(self) -> ASTNode:
        """Parse a primary expression (variable, string, number, boolean)."""
        token = self.current_token
        
        if token.type == TokenType.IDENTIFIER:
            self.advance()
            # Check for dotted access
            name_parts = [token.value]
            while self.current_token.type == TokenType.DOT:
                name_parts.append('.')
                self.advance()
                if self.current_token.type == TokenType.IDENTIFIER:
                    name_parts.append(self.current_token.value)
                    self.advance()
                else:
                    break
            return VariableNode(''.join(name_parts), token.line, token.col)
        
        if token.type == TokenType.STRING:
            self.advance()
            return TextNode(token.value, token.line, token.col)
        
        if token.type == TokenType.NUMBER:
            self.advance()
            return TextNode(token.value, token.line, token.col)
        
        if token.type == TokenType.TEXT:
            # This could be a literal value
            # Preserve newlines after <script> and <style> tags
            val = token.value
            self.advance()
            return TextNode(val, token.line, token.col)
        
        self.advance()
        return TextNode('', token.line, token.col)


class TemplateEngine:
    """Main template engine with caching and rendering."""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = templates_dir
        self.template_cache: Dict[str, List[ASTNode]] = {}

    def _load_template(self, name: str) -> str:
        """Load a template file."""
        template_path = os.path.join(self.templates_dir, name)
        if not os.path.exists(template_path):
            return f"Template not found: {name}"
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _parse_template(self, name: str, source: str) -> List[ASTNode]:
        """Parse a template source into AST."""
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        return parser.parse()

    def get_context_value(self, path: str, context: Dict[str, Any]) -> Any:
        """Get a nested value from context using dot notation."""
        parts = path.split('.')
        current = context
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return ''
        return current if current is not None else ''

    def render_template(self, name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Render a template with the given context."""
        if context is None:
            context = {}
        
        # Load template
        source = self._load_template(name)
        
        # Parse if not cached
        if name not in self.template_cache:
            self.template_cache[name] = self._parse_template(name, source)
        
        ast = self.template_cache[name]
        
        # Render
        result = []
        for node in ast:
            result.append(node.render(context, self))
        
        return ''.join(result)


def get_engine(templates_dir: str = "templates") -> TemplateEngine:
    """Get or create a template engine for the given directory."""
    return TemplateEngine(templates_dir)


def render_template(template_path: str, context: Optional[Dict[str, Any]] = None,
                    templates_dir: str = "templates") -> str:
    """Convenience function to render a template."""
    engine = get_engine(templates_dir)
    return engine.render_template(template_path, context)
