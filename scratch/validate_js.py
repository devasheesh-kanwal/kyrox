def parse_js(code):
    i = 0
    n = len(code)
    stack = []
    
    # States: 'CODE', 'STR_SINGLE', 'STR_DOUBLE', 'TEMPLATE', 'COMMENT_LINE', 'COMMENT_BLOCK', 'REGEX'
    # When entering ${ in TEMPLATE, we push ('TEMPLATE_EXPR', ...) onto a state stack
    state_stack = ['CODE']
    
    line = 1
    col = 1
    
    while i < n:
        ch = code[i]
        nxt = code[i+1] if i + 1 < n else ''
        curr_state = state_stack[-1]
        
        if ch == '\n':
            line += 1
            col = 1
        else:
            col += 1
            
        if curr_state == 'COMMENT_LINE':
            if ch == '\n':
                state_stack.pop()
            i += 1
            continue
            
        if curr_state == 'COMMENT_BLOCK':
            if ch == '*' and nxt == '/':
                state_stack.pop()
                i += 2
                col += 1
                continue
            i += 1
            continue
            
        if curr_state == 'STR_SINGLE':
            if ch == '\\':
                i += 2
                col += 1
                continue
            elif ch == "'":
                state_stack.pop()
            i += 1
            continue
            
        if curr_state == 'STR_DOUBLE':
            if ch == '\\':
                i += 2
                col += 1
                continue
            elif ch == '"':
                state_stack.pop()
                if stack and stack[-1][0] == '"':
                    stack.pop()
            i += 1
            continue
            
        if curr_state == 'TEMPLATE':
            if ch == '\\':
                i += 2
                col += 1
                continue
            elif ch == '`':
                state_stack.pop()
                i += 1
                continue
            elif ch == '$' and nxt == '{':
                state_stack.append('CODE')
                stack.append(('${', line, col))
                i += 2
                col += 1
                continue
            i += 1
            continue
            
        # curr_state == 'CODE'
        if ch == '/' and nxt == '/':
            state_stack.append('COMMENT_LINE')
            i += 2
            col += 1
            continue
        elif ch == '/' and nxt == '*':
            state_stack.append('COMMENT_BLOCK')
            i += 2
            col += 1
            continue
        elif ch == '/':
            # Check if this is a regex literal
            # Look backwards for preceding non-whitespace character
            j = i - 1
            while j >= 0 and code[j] in ' \t\r\n':
                j -= 1
            prev_char = code[j] if j >= 0 else ''
            if prev_char in '(=:[,!&|?~;{}' or (j >= 5 and code[j-5:j+1] == 'return'):
                # It's a regex! Scan to closing /
                i += 1
                col += 1
                while i < n:
                    if code[i] == '\\':
                        i += 2
                        col += 2
                        continue
                    if code[i] == '/':
                        # End of regex, skip any flags [gimsuy]
                        i += 1
                        col += 1
                        while i < n and code[i] in 'gimsuy':
                            i += 1
                            col += 1
                        break
                    i += 1
                    col += 1
                continue
        elif ch == "'":
            state_stack.append('STR_SINGLE')
            i += 1
            continue
        elif ch == '"':
            state_stack.append('STR_DOUBLE')
            stack.append(('"', line, col))
            i += 1
            continue
        elif ch == '`':
            state_stack.append('TEMPLATE')
            i += 1
            continue
            
        # Handle delimiters
        if ch in '({[':
            stack.append((ch, line, col))
        elif ch in ')}]':
            if not stack:
                raise SyntaxError(f"Unexpected closing delimiter '{ch}' at line {line}, col {col}")
            top, s_line, s_col = stack.pop()
            expected = {'(': ')', '{': '}', '[': ']', '${': '}'}[top]
            if ch != expected:
                raise SyntaxError(f"Mismatched delimiter: expected '{expected}' to match '{top}' from line {s_line}:{s_col}, got '{ch}' at line {line}:{col}")
            if top == '${':
                # Returned from template expr
                if state_stack[-1] == 'CODE' and len(state_stack) > 1:
                    state_stack.pop()
                    
        i += 1
        
    if len(state_stack) > 1:
        raise SyntaxError(f"Unclosed state at EOF: {state_stack[-1]}, opened at: {stack[-1] if stack else 'unknown'}")
    if stack:
        raise SyntaxError(f"Unclosed delimiter at EOF: {stack[-1]}")
    return True

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start = html.find('<script>')
end = html.rfind('</script>')
script_code = html[start+8:end]

try:
    parse_js(script_code)
    print("SUCCESS: index.html JavaScript parsed with 0 syntax errors!")
except SyntaxError as e:
    print("SYNTAX ERROR:", e)
