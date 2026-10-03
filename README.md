# Logic Implication FRW — Soft Error Fault Tolerance

Implementation of **"An integrated fault tolerance technique for combinational circuits based on implications and transistor sizing"** (Sheikh & El-Maleh, INTEGRATION 2017).

This project implements the **implication-based FRW (Functionally Redundant Wire)** pipeline for enhancing soft error tolerance in combinational circuits through logical masking.

## Scope

- **Implemented**: Algorithms 1–5, Equations 1–3 (full implication FRW pipeline)
- **Excluded**: STR (Selective Transistor Redundancy) phase

## Usage

```bash
python main.py --netlist examples/fig4.txt --th1 0.3 --th2 0.4 --gain-th 0.02 --patterns 10000
```

## Project Structure

```
core/               # Circuit model, gate library, 5-valued logic engine
faultsim/           # Random-pattern fault simulation (P0/P1/Pdet)
implications/       # VP, IPI, gain, FRW addition, pipeline driver
reporting/          # Area computation, Table-1 style reports
examples/           # Hand-encoded paper example circuits
tests/              # Pytest test suite with deterministic oracles
```

## Testing

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## References & Verification

- **[Verification & Benchmark Analysis Report](SIMULATION_README.md)**: Detailed breakdown comparing simulation results with the paper's figures (Fig. 4 & Fig. 5), area models, fault coverage metrics, and zero-probability explanations.
- Sheikh, El-Maleh. "An integrated fault tolerance technique for combinational circuits based on implications and transistor sizing." INTEGRATION, the VLSI journal 58 (2017): 35–46.
