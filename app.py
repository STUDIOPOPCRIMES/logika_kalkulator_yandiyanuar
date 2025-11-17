from flask import Flask, render_template, request
import itertools
import re

app = Flask(__name__)

# ================================================
# Fungsi evaluasi ekspresi logika
# ================================================
def eval_logic(expr, values):
    """
    Evaluasi ekspresi logika dengan nilai variabel.
    values: dict, misal {'P': True, 'Q': False}
    
    Operator yang didukung:
    - ¬ atau ~ : NOT (negasi)
    - ∧ : AND (konjungsi)
    - ∨ : OR (disjungsi)
    - → : Implikasi (P→Q = ¬P∨Q)
    - ↔ : Bi-implikasi (P↔Q = (P→Q)∧(Q→P))
    - ⊕ : XOR (exclusive OR)
    - P~Q : NAND (¬(P∧Q))
    """
    expr_eval = expr

    # Ganti variabel dengan True/False
    for var, val in values.items():
        expr_eval = re.sub(rf"\b{var}\b", str(val), expr_eval)

    # LANGKAH 1: Tangani operator biner khusus SEBELUM replace sederhana
    
    # NAND: P~Q → not (P and Q)
    expr_eval = re.sub(
        r"(True|False)\s*~\s*(True|False)", 
        r"(not (\1 and \2))", 
        expr_eval
    )
    
    # Implikasi: P→Q → (not P or Q)
    expr_eval = re.sub(
        r"(True|False)\s*→\s*(True|False)", 
        r"((not \1) or \2)", 
        expr_eval
    )
    expr_eval = re.sub(
        r"(True|False)\s*->\s*(True|False)", 
        r"((not \1) or \2)", 
        expr_eval
    )
    expr_eval = re.sub(
        r"(True|False)\s*=>\s*(True|False)", 
        r"((not \1) or \2)", 
        expr_eval
    )
    
    # Bi-implikasi: P↔Q → (P == Q)
    expr_eval = re.sub(
        r"(True|False)\s*↔\s*(True|False)", 
        r"(\1 == \2)", 
        expr_eval
    )
    expr_eval = re.sub(
        r"(True|False)\s*<->\s*(True|False)", 
        r"(\1 == \2)", 
        expr_eval
    )
    
    # XOR: P⊕Q → (P != Q)
    expr_eval = re.sub(
        r"(True|False)\s*⊕\s*(True|False)", 
        r"(\1 != \2)", 
        expr_eval
    )

    # LANGKAH 2: Ganti operator sederhana
    expr_eval = expr_eval.replace("∧", " and ")
    expr_eval = expr_eval.replace("∨", " or ")
    
    # LANGKAH 3: Negasi tunggal (¬P atau ~P) - diproses TERAKHIR
    expr_eval = expr_eval.replace("¬", " not ")
    expr_eval = expr_eval.replace("~", " not ")

    try:
        result = eval(expr_eval)
        return result
    except Exception as e:
        print(f"Error evaluating '{expr}' -> '{expr_eval}': {e}")
        return False


# ================================================
# Route utama
# ================================================
@app.route("/", methods=["GET", "POST"])
def index():
    table = []
    expr_input = ""
    vars = []
    expressions = []

    if request.method == "POST":
        expr_input = request.form["expr"].strip()
        
        # Split input menjadi beberapa ekspresi (pisahkan dengan spasi)
        expressions = expr_input.split()
        
        # Ambil semua variabel dari semua ekspresi
        vars_set = set()
        for expr in expressions:
            vars_set.update(re.findall(r"[A-Z]", expr))
        vars = sorted(vars_set)

        # Bangun tabel kebenaran
        for combo in itertools.product([True, False], repeat=len(vars)):
            values = dict(zip(vars, combo))
            row = {var: "B" if values[var] else "S" for var in vars}

            # Evaluasi semua ekspresi satu per satu
            for expr in expressions:
                res = eval_logic(expr, values)
                row[expr] = "B" if res else "S"

            table.append(row)

    return render_template("index.html",
                           table=table,
                           vars=vars,
                           expressions=expressions,
                           expr=expr_input)


if __name__ == "__main__":
    app.run(debug=True)