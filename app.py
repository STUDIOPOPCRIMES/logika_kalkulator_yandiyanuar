from flask import Flask, render_template, request
import itertools
import re

app = Flask(__name__)

# Mapping operator ke python lambda
LOGIC_OPS = {
    '∧': lambda a, b: a and b, '&': lambda a, b: a and b, 'and': lambda a, b: a and b, 
    '∨': lambda a, b: a or b, '|': lambda a, b: a or b, 'or': lambda a, b: a or b, 
    '⊕': lambda a, b: a != b, '^': lambda a, b: a != b, 'xor': lambda a, b: a != b, 
    '↑': lambda a, b: not(a and b), 'nand': lambda a, b: not(a and b),
    '↓': lambda a, b: not(a or b), 'nor': lambda a, b: not(a or b),
    '→': lambda a, b: (not a) or b, '->': lambda a, b: (not a) or b, '=>': lambda a, b: (not a) or b, 'implies': lambda a, b: (not a) or b,
    '↔': lambda a, b: a == b, '<->': lambda a, b: a == b, '<=>': lambda a, b: a == b, 'iff': lambda a, b: a == b,
}

OP_PRIOR = [
    ('~', '¬', '!'), # NOT
    ('∧', '&', 'and'),
    ('∨', '|', 'or'),
    ('⊕', '^', 'xor'),
    ('↑', 'nand'),
    ('↓', 'nor'),
    ('→', '->', '=>', 'implies'),
    ('↔', '<->', '<=>', 'iff')
]

# Regex satuan
RE_VAR     = r'[A-Z]'
RE_NOT     = r'(~|¬|!)\s*([A-Z]|\([^\)]+\))'
RE_PAREN   = r'\([^()]*\)'
RE_BINARY  = r'([A-Z01]|~[A-Z]|\([^\)]+\))\s*({})\s*([A-Z01]|~[A-Z]|\([^\)]+\))'

def format_bool(val):
    return "B" if val else "S"

def find_variables(expr):
    return sorted(set(re.findall(RE_VAR, expr)))

def to_python_tokens(expr, values):
    # Ganti variabel dengan True/False
    for k, v in values.items():
        expr = re.sub(rf'\b{k}\b', str(v), expr)
    # Ganti True/False string singkat
    expr = re.sub(r'\bTrue\b', '1', expr)
    expr = re.sub(r'\bFalse\b', '0', expr)
    return expr

def eval_logic(expr, values):
    """
    Evaluasi satu ekspresi tanpa subekspresi, sudah diganti variabel.
    Mendukung kurung, binary op, NOT lintas operator, penanganan error.
    """
    s = expr
    # Normalisasi spasi
    s = re.sub(r'\s+', '', s)

    # Mapping: variabel ke nilai
    for k, v in values.items():
        s = re.sub(rf'\b{k}\b', "True" if v else "False", s)

    # Proses NOT (~, ¬, !) __prioritas__
    def do_not(x):  # x dalam bentuk string "True" / "False"
        return 'False' if x == "True" else 'True'

    # Loop kurung bagian terdalam
    max_iter = 100
    for _ in range(max_iter):
        prev = s

        # Substitusi Notasi NOT di depan variabel, kurung, True/False
        s = re.sub(r'(?:~|¬|!)(True|False)', lambda m: do_not(m.group(1)), s)

        # Substitusi operator biner per prioritas tertinggi yang ketemu
        changed = False
        for ops in OP_PRIOR[::-1]:  # prioritas tinggi ke rendah
            re_ops = '|'.join([re.escape(op) for op in ops])
            pattern = rf'(True|False)({re_ops})(True|False)'
            def repl(m):
                a, op, b = m.group(1), m.group(2), m.group(3)
                aval, bval = (a == 'True'), (b == 'True')
                try:
                    res = LOGIC_OPS[op](aval, bval)
                except:
                    return m.group(0) # kalau gagal, lewat
                changed = True
                return "True" if res else "False"
            s_new = re.sub(pattern, repl, s)
            if s_new != s:
                changed = True
                s = s_new

        # Bersihkan sisa NOT
        s = re.sub(r'(?:~|¬|!)(True|False)', lambda m: do_not(m.group(1)), s)

        # Sederhanakan kurung ((True)), ((False))
        s = re.sub(r'\((True|False)\)', r'\1', s)

        # Sudah final?
        if s in ['True', 'False']:
            return s == 'True'
        if s == prev:
            break
    # Terakhir, return eval jika bisa
    try:
        return eval(s)
    except:
        return False

def extract_all_subexpressions(expr):
    """
    Mengembalikan subekspresi logika (dari atomik ke gabungan) untuk tabel kebenaran (termasuk intermediate step).
    """
    expr = expr.replace(" ","")
    result = []
    # Cari dan daftarkan subekspresi NOT satuan
    for m in re.finditer(r'(?:~|¬|!)[A-Z]', expr):
        token = m.group(0)
        if token not in result:
            result.append(token)
    # Cari kurung ekspresi dalam
    def extract_paren(s):
        out = []
        stack = []
        start = None
        for i, ch in enumerate(s):
            if ch == '(':
                if len(stack)==0: start = i
                stack.append(ch)
            elif ch == ')':
                if stack:
                    stack.pop()
                    if not stack and start is not None:
                        sub = s[start+1:i]
                        # Tambahan: subekspresi dalam kurung
                        if sub not in out:
                            out += extract_paren(sub)
                            out.append(sub)
        return out
    for se in extract_paren(expr):
        if se not in result:
            result.append(se)
    # Cari subekspresi biner tak terkurung
    for ops in OP_PRIOR:
        for op in ops:
            idx = expr.find(op)
            if idx>0:
                # dekat kiri-kanan variabel/expr/NOT
                lft = expr[:idx]
                rgt = expr[idx+len(op):]
                if lft and rgt:
                    # ambil kiri penuh
                    left = re.sub(r'^[~¬!]*','',lft)
                    left = lft[-1] if lft[-1].isalpha() else lft
                    right = re.sub(r'^[~¬!]*','',rgt)
                    right = rgt[0] if rgt[0].isalpha() else rgt
                    sub = expr
                    if sub not in result: result.append(sub)
    return result

@app.route("/", methods=["GET", "POST"])
def index():
    table = []
    expr_input = ""
    vars = []
    expressions = []
    if request.method=="POST":
        # User dapat isi multi ekspresi, satu/banyak exp per baris
        expr_input = request.form["expr"].strip()
        expr_lines = [ln.strip() for ln in expr_input.split('\n') if ln.strip()]
        all_exprs = []
        for main_expr in expr_lines:
            # Subekspresi (urut: NOT dulu, kurung, biner, dst)
            subs = extract_all_subexpressions(main_expr)
            for s in subs:
                if s not in all_exprs: all_exprs.append(s)
            if main_expr not in all_exprs:
                all_exprs.append(main_expr)
        expressions = all_exprs
        # Kumpulkan variabel
        vars_set = set()
        for expr in expressions:
            vars_set.update(re.findall(RE_VAR, expr))
        vars = sorted(vars_set)
        # Generate tabel kebenaran (kombinasi semua variabel)
        for combo in itertools.product([True,False], repeat=len(vars)):
            values = dict(zip(vars, combo))
            row = {var: format_bool(values[var]) for var in vars}
            for expr in expressions:
                res = eval_logic(expr, values)
                row[expr] = format_bool(res)
            table.append(row)
    return render_template("index.html",
        table=table,vars=vars,expressions=expressions,expr=expr_input
    )

if __name__ == '__main__':
    app.run(debug=True)
