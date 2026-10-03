import os
import glob
import shutil

def pla_to_blif(pla_file, blif_file):
    with open(pla_file, 'r') as f:
        lines = f.readlines()
        
    num_in = 0
    num_out = 0
    product_terms = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'): continue
        if line.startswith('.i '):
            num_in = int(line.split()[1])
        elif line.startswith('.o '):
            num_out = int(line.split()[1])
        elif line.startswith('.p '):
            pass
        elif line.startswith('.e'):
            break
        elif line.startswith('.'):
            # Other directives
            pass
        else:
            # product term
            parts = line.split()
            if len(parts) >= 2:
                product_terms.append((parts[0], parts[1]))
                
    with open(blif_file, 'w') as f:
        name = os.path.basename(pla_file).replace('.pla', '').replace('.PLA', '')
        f.write(f".model {name}\n")
        
        inputs = [f"pi_{i}" for i in range(num_in)]
        outputs = [f"po_{i}" for i in range(num_out)]
        
        f.write(f".inputs {' '.join(inputs)}\n")
        f.write(f".outputs {' '.join(outputs)}\n")
        
        # for each output, find the product terms that contribute to it
        for j in range(num_out):
            f.write(f".names {' '.join(inputs)} {outputs[j]}\n")
            # Has any ON-set product term?
            has_onset = False
            for in_str, out_str in product_terms:
                if len(out_str) > j and out_str[j] == '1':
                    f.write(f"{in_str} 1\n")
                    has_onset = True
            if not has_onset:
                # If no product term sets this output to 1, it must be constant 0
                # But wait, in blif, a .names with no ON-set rows evaluates to 0 anyway.
                # However, our parser handles an empty truth table by making it CONST 0.
                pass
        f.write(".end\n")

targets = ['alu4', 'apex1', 'apex2', 'apex3', 'apex4', 'b12', 'clip', 'cordic', 'ex5', 'misex1', 'misex2', 'misex3', 'rd84', 'seq', 'squar5', 'table3', 'table5', 'z5xp1']

pla_files = glob.glob('benchmarks/**/*.pla', recursive=True)
blif_files = glob.glob('benchmarks/**/*.blif', recursive=True)

os.makedirs('examples', exist_ok=True)

for name in targets:
    lower_name = name.lower()
    
    # check blif
    blif_src = next((f for f in blif_files if os.path.basename(f).lower() == f"{lower_name}.blif"), None)
    if blif_src:
        shutil.copy(blif_src, f"examples/{name}.blif")
        print(f"Copied {name}.blif to examples/")
        continue
        
    pla_src = next((f for f in pla_files if os.path.basename(f).lower() == f"{lower_name}.pla"), None)
    if pla_src:
        pla_to_blif(pla_src, f"examples/{name}.blif")
        print(f"Converted {name}.pla to examples/{name}.blif")
        continue
        
    print(f"WARNING: Could not find {name}")
