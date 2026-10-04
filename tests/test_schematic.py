"""Tests for the schematic -> netlist converter (run: pytest tests/)."""
from core.schematic import example_schematics, schematic_to_netlist, terminals_for


def _lines(res):
    return [l for l in res.netlist.splitlines() if l and not l.startswith("*")]


def test_examples_match_hand_written_netlists():
    ex = example_schematics()
    assert _lines(schematic_to_netlist(ex["RC step response"])) == ["V1 1 0 5", "R1 1 2 1k", "C1 2 0 1u"]
    assert _lines(schematic_to_netlist(ex["Diode + current source"])) == [
        "V1 1 0 12", "R1 1 2 4k", "I1 0 2 2m", "R2 2 3 1k", "D1 3 0"]
    assert _lines(schematic_to_netlist(ex["Half-wave rectifier"])) == ["V1 1 0 SINE 10 60", "D1 1 2", "R1 2 0 1k"]
    assert _lines(schematic_to_netlist(ex["High-pass filter (AC sweep)"])) == ["V1 1 0 AC 5 0", "C1 1 2 1u", "R1 2 0 1k"]


def test_rotation_moves_terminals():
    c = {"type": "R", "x": 100, "y": 100, "rot": 0}
    assert terminals_for(c) == [(60, 100), (140, 100)]
    c["rot"] = 1
    assert terminals_for(c) == [(100, 60), (100, 140)]


def test_empty_and_missing_ground():
    assert not schematic_to_netlist({"components": [], "wires": []}).ok
    s = example_schematics()["RC step response"]
    no_gnd = {"components": [c for c in s["components"] if c["type"] != "GND"], "wires": s["wires"]}
    res = schematic_to_netlist(no_gnd)
    assert not res.ok and any("ground" in e.lower() for e in res.errors)


def test_dangling_terminal_is_an_error():
    s = example_schematics()["RC step response"]
    cut = {"components": s["components"], "wires": s["wires"][:1]}
    res = schematic_to_netlist(cut)
    assert not res.ok and any("not connected" in e for e in res.errors)


def test_bad_values_and_warnings():
    s = example_schematics()["RC step response"]
    comps = [dict(c) for c in s["components"]]
    comps[1]["value"] = "abc"
    assert not schematic_to_netlist({"components": comps, "wires": s["wires"]}).ok
    comps[1]["value"] = "1M"
    res = schematic_to_netlist({"components": comps, "wires": s["wires"]})
    assert res.ok and any("MEG" in w for w in res.warnings)
    comps[1]["value"] = "0"
    assert not schematic_to_netlist({"components": comps, "wires": s["wires"]}).ok


def test_t_junction_and_duplicate_names():
    s = example_schematics()["RC step response"]
    comps = [dict(c) for c in s["components"]]
    comps[2].update(type="R", name="R1", value="1k")   # second resistor named R1
    res = schematic_to_netlist({"components": comps, "wires": s["wires"]})
    assert any("Duplicate" in e for e in res.errors)
