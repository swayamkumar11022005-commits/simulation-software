"""
Thin, UI-friendly wrappers around the existing analyses.

The original analysis classes call plt.show() inside their plot methods, which
doesn't suit a web app, so the app uses their `run`/`solve` methods only and
draws the data itself (see ui/plots.py).  Nothing in core/ or the existing
analysis modules had to change.
"""

from __future__ import annotations

import os
import tempfile
import time

import numpy as np

from analysis.acsweep import ACSweep
from analysis.transient import TransientAnalysis
from core.parser import NetlistParser

ANALYSIS_LABELS = {
    "dc_op": "DC Operating Point",
    "transient": "Transient",
    "ac_sweep": "AC Sweep (Bode)",
    "dc_sweep": "DC Sweep",
}

# what NetlistParser.determine_analysis_type() returns -> our key
_ROUTER = {
    "dc_transient": "transient",
    "ac_transient": "transient",
    "ac_sweep": "ac_sweep",
    "dc_sweep": "dc_sweep",
}


def parse_netlist(netlist_text: str):
    """Parse netlist text with the existing NetlistParser. Returns (circuit, parser)."""
    fd, path = tempfile.mkstemp(suffix=".net")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(netlist_text)
        parser = NetlistParser(path)
        circuit = parser.parse()
    finally:
        if os.path.exists(path):
            os.remove(path)
    return circuit, parser


def auto_analysis(parser) -> str:
    """Same topology router main.py uses."""
    return _ROUTER[parser.determine_analysis_type()]


def active_nodes(circuit) -> list[str]:
    circuit._map_nodes()
    return sorted((n for n in circuit.node_map if n != "0"),
                  key=lambda n: (not n.isdigit(), int(n) if n.isdigit() else 0, n))


def suggest_params(circuit) -> dict:
    """Sensible defaults for the parameter widgets, derived from the circuit."""
    p = {"t_stop": 0.005, "t_step": 0.0001, "f_start": 10.0, "f_stop": 100000.0,
         "ppd": 20, "v_start": -5.0, "v_stop": 15.0, "steps": 200}
    freqs = [c[9] for c in circuit.components
             if c[0] in ("V", "I") and len(c) > 9 and c[7] == "SINE" and c[9] > 0]
    if freqs:
        f = min(freqs)
        p["t_stop"] = 3.0 / f
        p["t_step"] = 1.0 / (f * 200.0)
    dc_v = [c[4] for c in circuit.components if c[0] == "V" and c[7] == "DC"]
    if dc_v:
        top = max(abs(v) for v in dc_v) or 5.0
        p["v_start"], p["v_stop"] = -0.5 * top, 1.5 * top
    return p


def dc_sources(circuit) -> list[str]:
    return [c[1] for c in circuit.components if c[0] == "V" and c[7] == "DC"]


# --------------------------------------------------------------------------
# analyses
# --------------------------------------------------------------------------
def run_dc_op(circuit) -> dict:
    t0 = time.perf_counter()
    res = circuit.solve()
    return {"kind": "dc_op", "node_voltages": res["node_voltages"],
            "source_currents": res["source_currents"], "elapsed": time.perf_counter() - t0}


def run_transient(circuit, t_stop: float, t_step: float) -> dict:
    if t_step <= 0 or t_stop <= 0:
        raise ValueError("t_stop and t_step must be positive.")
    if t_stop / t_step > 200_000:
        raise ValueError("That would take more than 200,000 time steps - increase t_step.")
    t0 = time.perf_counter()
    res = TransientAnalysis(circuit).run(t_stop=t_stop, t_step=t_step)
    return {"kind": "transient", "times": np.asarray(res["times"]),
            "node_voltages": {k: np.asarray(v) for k, v in res["node_voltages"].items()},
            "elapsed": time.perf_counter() - t0}


def run_ac_sweep(circuit, f_start: float, f_stop: float, ppd: int) -> dict:
    if not (0 < f_start < f_stop):
        raise ValueError("Need 0 < f_start < f_stop.")
    t0 = time.perf_counter()
    res = ACSweep(circuit).run(f_start, f_stop, points_per_decade=int(ppd))
    return {"kind": "ac_sweep", "frequencies": np.asarray(res["frequencies"]),
            "magnitude_db": {k: np.asarray(v) for k, v in res["magnitude_db"].items()},
            "phase_deg": {k: np.asarray(v) for k, v in res["phase_deg"].items()},
            "elapsed": time.perf_counter() - t0}


def run_dc_sweep(circuit, source: str, v_start: float, v_stop: float, steps: int) -> dict:
    """Same sweep DCSweep.sweep_v_source performs, but keeps node voltages too."""
    idx = next((i for i, c in enumerate(circuit.components)
                if c[0] == "V" and c[1] == source), None)
    if idx is None:
        raise ValueError(f"Voltage source '{source}' not found in circuit.")
    sweep = np.linspace(v_start, v_stop, int(steps))
    nodes: dict[str, list] = {}
    currents = []
    t0 = time.perf_counter()
    original = circuit.components[idx]
    try:
        for v in sweep:
            comp = list(original)
            comp[4] = float(v)
            circuit.components[idx] = tuple(comp)
            res = circuit.solve()
            currents.append(-res["source_currents"][f"I({source})"])
            for k, val in res["node_voltages"].items():
                nodes.setdefault(k, []).append(val)
    finally:
        circuit.components[idx] = original
    return {"kind": "dc_sweep", "source": source, "sweep": sweep,
            "source_current": np.asarray(currents),
            "node_voltages": {k: np.asarray(v) for k, v in nodes.items()},
            "elapsed": time.perf_counter() - t0}


# --------------------------------------------------------------------------
# export
# --------------------------------------------------------------------------
def results_to_csv(res: dict) -> str:
    """Flat CSV of whatever the analysis produced."""
    kind = res["kind"]
    if kind == "dc_op":
        rows = [("quantity", "value")]
        rows += [(k, v) for k, v in res["node_voltages"].items()]
        rows += [(k, v) for k, v in res["source_currents"].items()]
        return "\n".join(",".join(str(c) for c in r) for r in rows) + "\n"
    if kind == "transient":
        cols, x = res["node_voltages"], res["times"]
        head = ["time_s", *cols]
        data = [x, *cols.values()]
    elif kind == "ac_sweep":
        x = res["frequencies"]
        head = ["frequency_hz"] + [f"{k}_dB" for k in res["magnitude_db"]] + [f"{k}_deg" for k in res["phase_deg"]]
        data = [x, *res["magnitude_db"].values(), *res["phase_deg"].values()]
    else:
        x = res["sweep"]
        head = [f"{res['source']}_volts", f"I({res['source']})", *res["node_voltages"]]
        data = [x, res["source_current"], *res["node_voltages"].values()]
    lines = [",".join(head)]
    for i in range(len(x)):
        lines.append(",".join(f"{col[i]:.9g}" for col in data))
    return "\n".join(lines) + "\n"
