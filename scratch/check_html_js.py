import re

def check_file(path):
    print(f"Checking {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract all <script> blocks
    scripts = re.findall(r'<script(?:\s+[^>]*)?>(.*?)</script>', content, flags=re.DOTALL)
    print(f"Found {len(scripts)} script blocks.")

    for idx, script in enumerate(scripts):
        # Ignore external script src tags with empty body
        if not script.strip():
            continue
        
        # Check brace balance
        stack = []
        in_string = False
        string_char = None
        in_single_line_comment = False
        in_multi_line_comment = False
        in_template_literal = False
        escape = False

        lines = script.split('\n')
        for line_no, line in enumerate(lines, 1):
            i = 0
            while i < len(line):
                ch = line[i]
                
                # Check for comment ends
                if in_multi_line_comment:
                    if ch == '*' and i + 1 < len(line) and line[i+1] == '/':
                        in_multi_line_comment = False
                        i += 2
                        continue
                    i += 1
                    continue
                
                if in_single_line_comment:
                    break
                
                # String literals
                if in_string:
                    if escape:
                        escape = False
                    elif ch == '\\':
                        escape = True
                    elif ch == string_char:
                        in_string = False
                    i += 1
                    continue

                if in_template_literal:
                    if escape:
                        escape = False
                    elif ch == '\\':
                        escape = True
                    elif ch == '`':
                        in_template_literal = False
                    elif ch == '$' and i + 1 < len(line) and line[i+1] == '{':
                        stack.append(('${', line_no, i))
                        i += 2
                        continue
                    i += 1
                    continue

                # Comments start
                if ch == '/' and i + 1 < len(line):
                    if line[i+1] == '/':
                        in_single_line_comment = True
                        break
                    elif line[i+1] == '*':
                        in_multi_line_comment = True
                        i += 2
                        continue

                # Quotes start
                if ch in ('"', "'"):
                    in_string = True
                    string_char = ch
                    escape = False
                    i += 1
                    continue
                elif ch == '`':
                    in_template_literal = True
                    escape = False
                    i += 1
                    continue

                # Braces
                if ch in '({[':
                    stack.append((ch, line_no, i))
                elif ch in ')}]':
                    if not stack:
                        print(f"ERROR: Unmatched closing '{ch}' at line {line_no}:{i} in script {idx}!")
                        print(f"Line content: {line}")
                        return False
                    top, start_line, start_col = stack.pop()
                    expected = {'(': ')', '{': '}', '[': ']', '${': '}'}[top]
                    if ch != expected:
                        print(f"ERROR: Mismatched brace at line {line_no}:{i}! Expected '{expected}' for '{top}' from line {start_line}, got '{ch}'")
                        print(f"Line content: {line}")
                        return False
                i += 1
            in_single_line_comment = False

        if stack:
            print(f"ERROR: Unclosed delimiters at end of script {idx}: {stack[:5]}")
            return False

    print(f"SUCCESS: {path} has perfectly balanced JavaScript braces and strings!")
    return True

if __name__ == '__main__':
    check_file('index.html')
