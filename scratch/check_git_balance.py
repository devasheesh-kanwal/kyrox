import re
import subprocess

c = subprocess.check_output(['git', 'show', '3bf84c0:index.html'], text=True, encoding='utf-8')

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

print(f'3bf84c0: Curly braces: open={open_b}, close={close_b}, diff={open_b - close_b}')
print(f'3bf84c0: Parentheses: open={open_p}, close={close_p}, diff={open_p - close_p}')
print(f'3bf84c0: Square brackets: open={open_sq}, close={close_sq}, diff={open_sq - close_sq}')
