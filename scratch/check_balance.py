import re

with open('index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Find the main script tag
start = c.find('<script>')
end = c.rfind('</script>')
script_body = c[start+8:end]

# Remove single line comments
s = re.sub(r'//.*', '', script_body)
# Remove multi line comments
s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
# Remove template literals
s = re.sub(r'`(?:[^`\\]|\\.)*`', '""', s, flags=re.DOTALL)
# Remove double quoted strings
s = re.sub(r'"(?:[^"\\]|\\.)*"', '""', s)
# Remove single quoted strings
s = re.sub(r"'(?:[^'\\]|\\.)*'", "''", s)

open_b = s.count('{')
close_b = s.count('}')
open_p = s.count('(')
close_p = s.count(')')
open_sq = s.count('[')
close_sq = s.count(']')

print(f'Curly braces: open={open_b}, close={close_b}, diff={open_b - close_b}')
print(f'Parentheses: open={open_p}, close={close_p}, diff={open_p - close_p}')
print(f'Square brackets: open={open_sq}, close={close_sq}, diff={open_sq - close_sq}')

assert open_b == close_b, f'Mismatched braces: {open_b} != {close_b}'
assert open_p == close_p, f'Mismatched parentheses: {open_p} != {close_p}'
assert open_sq == close_sq, f'Mismatched brackets: {open_sq} != {close_sq}'
print('BRACES, PARENTHESES, AND BRACKETS ARE 100% PERFECTLY BALANCED!')
