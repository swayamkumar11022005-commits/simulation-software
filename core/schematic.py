"""
Schematic -> netlist conversion.

The drag-and-drop editor (ui/circuit_builder) produces a *schematic*: a list of
placed components and a list of wire segments, all on a 20px grid.  This module
turns that schematic into exactly the same SPICE-style netlist text that
core.parser.NetlistParser already understands, so the rest of the simulator
(solver + analyses) does not care whether a circuit was typed or drawn.

Schematic format (JSON-serialisable)::

    {
      "components": [
        {"name": "R1", "type": "R", "x": 300, "y": 160, "rot": 0, "value": "1k"},
        {"name": "V1", "type": "VSIN", "x": 160, "y": 200, "rot": 1,
         "amp": "10", "freq": "60"},
        {"name": "GND1", "type": "GND", "x": 280, "y": 280, "rot": 0},
        ...
      ],
      "wires": [{"x1": 160, "y1": 160, "x2": 260, "y2": 160}, ...]
    }

Connectivity rules (mirrored in the front-end so node badges match):
  * a wire joins everything at both of its end points,
  * a wire also joins any terminal / wire end point that lies on its body
    (T-junctions),
  * terminals that share the same grid point are connected,
  * every GND symbol is node 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.parser import parse_spice_value

GRID = 20

# type -> (netlist prefix, human label, value fields)
COMPONENT_SPECS = {
    "GND":  {"prefix": "GND", "label": "Ground",             "fields": []},
    "R":    {"prefix": "R",   "label": "Resistor",           "fields": ["value"]},
    "C":    {"prefix": "C",   "label": "Capacitor",          "fields": ["value"]},
    "L":    {"prefix": "L",   "label": "Inductor",           "fields": ["value"]},
    "VDC":  {"prefix": "V",   "label": "DC Voltage Source",  "fields": ["value"]},
    "VSIN": {"prefix": "V",   "label": "Sine Voltage Source", "fields": ["amp", "freq"]},
    "VAC":  {"prefix": "V",   "label": "AC Sweep Source",    "fields": ["mag", "phase"]},
    "IDC":  {"prefix": "I",   "label": "DC Current Source",  "fields": ["value"]},
    "ISIN": {"prefix": "I",   "label": "Sine Current Source", "fields": ["amp", "freq"]},
    "IAC":  {"prefix": "I",   "label": "AC Current Source",  "fields": ["mag", "phase"]},
    "D":    {"prefix": "D",   "label": "Diode",              "fields": []},
}

# Terminal offsets for rotation 0 (rotating by 90deg steps: (dx, dy) -> (-dy, dx)).
_TERMINALS_R0 = {
    "GND": [(0, -GRID)],
}
_TWO_TERMINAL = [(-2 * GRID, 0), (2 * GRID, 0)]


def terminals_for(comp: dict) -> list[tuple[int, int]]:
    """Absolute terminal coordinates of a placed component."""
    offsets = _TERMINALS_R0.get(comp["type"], _TWO_TERMINAL)
    rot = int(comp.get("rot", 0)) % 4
    x, y = int(comp["x"]), int(comp["y"])
    out = []
    for dx, dy in offsets:
        for _ in range(rot):
            dx, dy = -dy, dx
        out.append((x + dx, y + dy))
    return out


@dataclass
class NetlistResult:
    netlist: str = ""
    nodes: list[str] = field(default_factory=list)      # non-ground node names
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    component_count: int = 0
    # e.g. {"R1": ("1", "2")} -> which node each terminal ended up on
    connections: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors and bool(self.netlist.strip())


# --------------------------------------------------------------------------
# union-find
# --------------------------------------------------------------------------
class _DSU:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def _on_segment(px, py, x1, y1, x2, y2) -> bool:
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if cross != 0:
        return False
    return min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2)


def compute_nets(schematic: dict):
    """
    Returns (dsu, terminal_points) where terminal_points is a list of
    (component, index, (x, y)) in component order.
    """
    comps = schematic.get("components", [])
    wires = schematic.get("wires", [])
    dsu = _DSU()

    points = set()
    term_pts = []
    for c in comps:
        pts = c.get("terminals")
        pts = [tuple(int(v) for v in p) for p in pts] if pts else terminals_for(c)
        for i, p in enumerate(pts):
            term_pts.append((c, i, p))
            points.add(p)

    for w in wires:
        a = (int(w["x1"]), int(w["y1"]))
        b = (int(w["x2"]), int(w["y2"]))
        points.add(a)
        points.add(b)
        dsu.union(a, b)

    for w in wires:
        x1, y1, x2, y2 = (int(w[k]) for k in ("x1", "y1", "x2", "y2"))
        for p in points:
            if _on_segment(p[0], p[1], x1, y1, x2, y2):
                dsu.union(p, (x1, y1))

    for _, _, p in term_pts:
        dsu.find(p)
    return dsu, term_pts


# --------------------------------------------------------------------------
# value helpers
# --------------------------------------------------------------------------
def _clean(v) -> str:
    return "" if v is None else str(v).strip()


def _check_value(label: str, raw: str, errors: list, warnings: list,
                 positive=False, comp_type=None):
    if not raw:
        errors.append(f"{label}: value is empty.")
        return None
    if any(ch.isspace() for ch in raw):
        errors.append(f"{label}: value '{raw}' must not contain spaces.")
        return None
    try:
        num = parse_spice_value(raw)
    except ValueError:
        errors.append(f"{label}: '{raw}' is not a valid number (try 1k, 4.7u, 10m, 2MEG).")
        return None
    if positive and num <= 0:
        errors.append(f"{label}: value must be greater than zero.")
        return None
    suffix = "".join(ch for ch in raw if ch.isalpha()).upper()
    if suffix == "M" and comp_type == "R":
        warnings.append(f"{label}: '{raw}' means {num:g} ohm (milli). Use MEG for mega-ohms.")
    if suffix == "F" and comp_type == "C":
        warnings.append(f"{label}: 'F' means femto in SPICE. Use u, n or p for capacitor values.")
    return num


def sanitize_name(name: str, prefix: str) -> str:
    """Component names must start with their type letter (the parser keys off it)."""
    clean = "".join(ch for ch in _clean(name).upper() if ch.isalnum() or ch == "_")
    if not clean.startswith(prefix):
        clean = prefix + clean
    return clean


# --------------------------------------------------------------------------
# main entry point
# --------------------------------------------------------------------------
def schematic_to_netlist(schematic: dict | None) -> NetlistResult:
    res = NetlistResult()
    if not schematic or not schematic.get("components"):
        res.errors.append("The canvas is empty - drag some components onto it.")
        return res

    comps = schematic["components"]
    unknown = [c for c in comps if c.get("type") not in COMPONENT_SPECS]
    if unknown:
        res.errors.append(f"Unknown component type: {unknown[0].get('type')!r}.")
        return res

    dsu, term_pts = compute_nets(schematic)

    ground_roots = {dsu.find(p) for c, _, p in term_pts if c["type"] == "GND"}
    if not ground_roots:
        res.errors.append("No ground symbol. Add a Ground (0 V) to give the circuit a reference node.")

    # terminals per net, for dangling-pin detection
    count = {}
    for c, _, p in term_pts:
        r = dsu.find(p)
        count[r] = count.get(r, 0) + 1

    # node naming: ground -> '0', others numbered by first appearance
    names: dict = {}
    nxt = 1

    def node_of(root):
        nonlocal nxt
        if root in ground_roots:
            return "0"
        if root not in names:
            names[root] = str(nxt)
            nxt += 1
        return names[root]

    real = [c for c in comps if c["type"] != "GND"]
    for c in comps:
        if c["type"] == "GND" and count.get(dsu.find(terminals_for(c)[0] if not c.get("terminals") else tuple(c["terminals"][0])), 0) == 1:
            res.warnings.append(f"{c.get('name', 'GND')} is not connected to anything.")
    if not real:
        res.errors.append("Only a ground symbol is on the canvas - add some components.")
        return res

    # unique, well-formed names
    seen = set()
    lines = []
    any_on_ground = False
    for c in real:
        spec = COMPONENT_SPECS[c["type"]]
        name = sanitize_name(c.get("name", ""), spec["prefix"])
        if name in seen:
            res.errors.append(f"Duplicate component name {name}. Rename one of them.")
            continue
        seen.add(name)

        pts = [p for cc, _, p in term_pts if cc is c]
        nodes = []
        for i, p in enumerate(pts):
            root = dsu.find(p)
            if count[root] == 1:
                res.errors.append(f"{name}: terminal {i + 1} is not connected. Wire it up.")
            nodes.append(node_of(root))
        if "0" in nodes:
            any_on_ground = True
        if len(nodes) == 2 and nodes[0] == nodes[1]:
            res.warnings.append(f"{name}: both terminals are on node {nodes[0]} (shorted out).")
        res.connections[name] = tuple(nodes)

        t = c["type"]
        n1, n2 = nodes[0], nodes[1]
        if t == "D":
            lines.append(f"{name} {n1} {n2}")
        elif t in ("R", "C", "L"):
            raw = _clean(c.get("value"))
            _check_value(name, raw, res.errors, res.warnings, positive=True, comp_type=t)
            lines.append(f"{name} {n1} {n2} {raw}")
        elif t in ("VDC", "IDC"):
            raw = _clean(c.get("value"))
            _check_value(name, raw, res.errors, res.warnings)
            lines.append(f"{name} {n1} {n2} {raw}")
        elif t in ("VSIN", "ISIN"):
            amp, freq = _clean(c.get("amp")), _clean(c.get("freq"))
            _check_value(f"{name} amplitude", amp, res.errors, res.warnings)
            _check_value(f"{name} frequency", freq, res.errors, res.warnings, positive=True)
            lines.append(f"{name} {n1} {n2} SINE {amp} {freq}")
        elif t in ("VAC", "IAC"):
            mag, phase = _clean(c.get("mag")), _clean(c.get("phase")) or "0"
            _check_value(f"{name} magnitude", mag, res.errors, res.warnings, positive=True)
            try:
                float(phase)
            except ValueError:
                res.errors.append(f"{name}: phase '{phase}' must be a plain number of degrees.")
            lines.append(f"{name} {n1} {n2} AC {mag} {phase}")

    if ground_roots and not any_on_ground:
        res.errors.append("Nothing is connected to the ground symbol - the circuit is floating.")

    res.component_count = len(real)
    res.nodes = sorted(set(names.values()), key=int)
    header = "* Generated by the Schematic Builder"
    res.netlist = "\n".join([header, *lines]) + "\n"
    return res


# --------------------------------------------------------------------------
# Example schematics (also used by the app's "load example" menu)
# --------------------------------------------------------------------------
def _c(name, type_, x, y, rot=0, **kw):
    return {"name": name, "type": type_, "x": x, "y": y, "rot": rot, **kw}


def _w(x1, y1, x2, y2):
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def _rail(x_left, x_right, y=260):
    return _w(x_left, y, x_right, y)


def example_schematics() -> dict[str, dict]:
    rc = {
        "components": [
            _c("V1", "VDC", 160, 200, 1, value="5"),
            _c("R1", "R", 300, 160, 0, value="1k"),
            _c("C1", "C", 400, 200, 1, value="1u"),
            _c("GND1", "GND", 280, 280),
        ],
        "wires": [
            _w(160, 160, 260, 160), _w(340, 160, 400, 160),
            _w(160, 240, 160, 260), _rail(160, 400), _w(400, 240, 400, 260),
        ],
    }
    diode = {
        "components": [
            _c("V1", "VDC", 120, 200, 1, value="12"),
            _c("R1", "R", 240, 160, 0, value="4k"),
            _c("I1", "IDC", 320, 220, 3, value="2m"),
            _c("R2", "R", 400, 160, 0, value="1k"),
            _c("D1", "D", 480, 200, 1),
            _c("GND1", "GND", 300, 280),
        ],
        "wires": [
            _w(120, 160, 200, 160), _w(280, 160, 360, 160), _w(320, 160, 320, 180),
            _w(440, 160, 480, 160),
            _w(120, 240, 120, 260), _rail(120, 480), _w(480, 240, 480, 260),
        ],
    }
    rectifier = {
        "components": [
            _c("V1", "VSIN", 120, 200, 1, amp="10", freq="60"),
            _c("D1", "D", 240, 160, 0),
            _c("R1", "R", 340, 200, 1, value="1k"),
            _c("GND1", "GND", 240, 280),
        ],
        "wires": [
            _w(120, 160, 200, 160), _w(280, 160, 340, 160),
            _w(120, 240, 120, 260), _rail(120, 340), _w(340, 240, 340, 260),
        ],
    }
    highpass = {
        "components": [
            _c("V1", "VAC", 120, 200, 1, mag="5", phase="0"),
            _c("C1", "C", 240, 160, 0, value="1u"),
            _c("R1", "R", 340, 200, 1, value="1k"),
            _c("GND1", "GND", 240, 280),
        ],
        "wires": [
            _w(120, 160, 200, 160), _w(280, 160, 340, 160),
            _w(120, 240, 120, 260), _rail(120, 340), _w(340, 240, 340, 260),
        ],
    }
    rlc = {
        "components": [
            _c("V1", "VDC", 120, 200, 1, value="5"),
            _c("R1", "R", 240, 160, 0, value="10"),
            _c("L1", "L", 400, 160, 0, value="10m"),
            _c("C1", "C", 500, 200, 1, value="1u"),
            _c("GND1", "GND", 300, 280),
        ],
        "wires": [
            _w(120, 160, 200, 160), _w(280, 160, 360, 160), _w(440, 160, 500, 160),
            _w(120, 240, 120, 260), _rail(120, 500), _w(500, 240, 500, 260),
        ],
    }
    return {
        "RC step response": rc,
        "Diode + current source": diode,
        "Half-wave rectifier": rectifier,
        "High-pass filter (AC sweep)": highpass,
        "Series RLC": rlc,
    }
