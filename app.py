"""
Circuit Studio - Streamlit front-end for the custom SPICE-like simulator.

Two ways to describe a circuit, one simulation pipeline:

    draw it  ->  schematic (drag & drop)  ->  core.schematic  ->  netlist text  ┐
    type it  ->  netlist text editor  ───────────────────────────────────────────┤
                                                                                  v
                                  NetlistParser -> Circuit -> DC / Transient / AC / Sweep

Run with:
    streamlit run app.py
"""

import hashlib
import io

import pandas as pd
import streamlit as st

from analysis import runner
from core.parser import parse_spice_value
from core.schematic import example_schematics, schematic_to_netlist
from ui import plots, theme
from ui.circuit_builder import circuit_builder

st.set_page_config(page_title="Circuit Studio", page_icon="⚡", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(theme.CSS, unsafe_allow_html=True)

MODE_DRAW, MODE_TEXT = "🧩 Draw circuit", "📝 Netlist editor"
EXAMPLES = example_schematics()
ANALYSES = ["Auto-detect", *runner.ANALYSIS_LABELS.values()]
LABEL_TO_KEY = {v: k for k, v in runner.ANALYSIS_LABELS.items()}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def to_spice(x: float) -> str:
    """Format a float with a SPICE suffix that core.parser.parse_spice_value reads back."""
    if x == 0:
        return "0"
    for mult, suf in ((1e6, "MEG"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "u"), (1e-9, "n"), (1e-12, "p")):
        if abs(x) >= mult:
            return f"{x / mult:.6g}{suf}"
    return f"{x:.6g}"


def spice_input(label, default, key, help=None):
    raw = st.text_input(label, value=to_spice(default), key=key, help=help or "SPICE suffixes work: 5m, 100k, 1u, 2MEG")
    try:
        return parse_spice_value(raw.strip())
    except ValueError:
        st.error(f"'{raw}' is not a valid number for {label}.")
        return None


def init_state():
    first = list(EXAMPLES)[0]
    ss = st.session_state
    ss.setdefault("mode", MODE_DRAW)
    ss.setdefault("builder_schematic", EXAMPLES[first])
    ss.setdefault("builder_token", 0)
    ss.setdefault("netlist_text", schematic_to_netlist(EXAMPLES[first]).netlist)
    ss.setdefault("result", None)


def load_example():
    name = st.session_state.example_choice
    sch = EXAMPLES[name]
    st.session_state.builder_schematic = sch
    st.session_state.builder_token += 1
    st.session_state.netlist_text = schematic_to_netlist(sch).netlist
    st.session_state.result = None


def send_to_editor(netlist: str):
    st.session_state.netlist_text = netlist
    st.session_state.mode = MODE_TEXT


def issues_html(res):
    out = []
    for e in res.errors:
        out.append(f'<div class="issue">⛔ {e}</div>')
    for w in res.warnings:
        out.append(f'<div class="issue warn">⚠️ {w}</div>')
    if res.ok and not res.warnings:
        out.append(f'<div class="issue ok">✅ Circuit is valid: {res.component_count} components, '
                   f'{len(res.nodes)} nodes + ground.</div>')
    return "".join(out)


init_state()
ss = st.session_state

# --------------------------------------------------------------------------
# sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ Circuit Studio")
    st.radio("Circuit input", [MODE_DRAW, MODE_TEXT], key="mode",
             help="Both modes feed the exact same parser and solver.")
    st.divider()
    st.markdown("**Examples**")
    st.selectbox("Load a circuit", list(EXAMPLES), key="example_choice", label_visibility="collapsed")
    st.button("Load example", on_click=load_example, use_container_width=True)
    st.divider()
    st.markdown("**Supported elements**")
    st.caption("Resistor · Capacitor · Inductor · DC / Sine / AC voltage source · "
               "DC / Sine / AC current source · Diode")
    st.caption("SPICE suffixes: `k` 10³ · `MEG` 10⁶ · `m` 10⁻³ · `u` 10⁻⁶ · `n` 10⁻⁹ · `p` 10⁻¹²")

# --------------------------------------------------------------------------
# hero + circuit input
# --------------------------------------------------------------------------
st.markdown(theme.HERO, unsafe_allow_html=True)

if ss.mode == MODE_DRAW:
    st.markdown(theme.section("Schematic builder"), unsafe_allow_html=True)
    sch = circuit_builder(initial=ss.builder_schematic, load_token=ss.builder_token,
                          height=640, key="builder")
    if sch is not None:
        ss.builder_schematic = sch
    conv = schematic_to_netlist(ss.builder_schematic)
    active_netlist = conv.netlist if conv.ok else ""

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(theme.section("Generated netlist"), unsafe_allow_html=True)
        st.code(conv.netlist if conv.netlist else "* (nothing to show yet)", language="text")
        st.button("📝 Edit as netlist", on_click=send_to_editor, args=(conv.netlist,),
                  disabled=not conv.netlist, help="Copy this netlist into the text editor to tweak by hand.")
    with c2:
        st.markdown(theme.section("Checks"), unsafe_allow_html=True)
        st.markdown(issues_html(conv), unsafe_allow_html=True)
    build_error = None if conv.ok else (conv.errors[0] if conv.errors else "Circuit is empty.")
else:
    st.markdown(theme.section("Netlist editor"), unsafe_allow_html=True)
    st.text_area("Netlist", key="netlist_text", height=260, label_visibility="collapsed",
                 help="SPICE-style: `R1 1 2 1k`, `V1 1 0 SINE 10 60`, `V1 1 0 AC 5 0`, `D1 3 0` ...")
    active_netlist = ss.netlist_text
    build_error = None if active_netlist.strip() else "Netlist is empty."

# --------------------------------------------------------------------------
# simulation controls
# --------------------------------------------------------------------------
st.markdown(theme.section("Simulation"), unsafe_allow_html=True)

circuit = parser = None
parse_error = build_error
if active_netlist.strip() and not build_error:
    try:
        circuit, parser = runner.parse_netlist(active_netlist)
        if not circuit.components and not circuit.diodes and not circuit.capacitors and not circuit.inductors:
            parse_error = "The parser found no valid elements in this netlist."
            circuit = None
    except Exception as e:  # noqa: BLE001 - show anything the parser throws
        parse_error = f"Could not parse netlist: {e}"
        circuit = None

if circuit is None:
    st.info(parse_error or "Add components to get started.")
else:
    h = hashlib.md5(active_netlist.encode()).hexdigest()[:6]   # reset defaults when the circuit changes
    detected = runner.auto_analysis(parser)
    nodes = runner.active_nodes(circuit)
    defaults = runner.suggest_params(circuit)

    left, right = st.columns([1, 2])
    with left:
        choice = st.selectbox("Analysis", ANALYSES, key=f"analysis_{h}")
        kind = detected if choice == "Auto-detect" else LABEL_TO_KEY[choice]
        if choice == "Auto-detect":
            st.caption(f"Detected: **{runner.ANALYSIS_LABELS[kind]}** (same router as `main.py`)")
        sel_nodes = st.multiselect("Nodes to plot", nodes, default=nodes[:3], key=f"nodes_{h}")
    params, valid = {}, True
    with right:
        a, b, c = st.columns(3)
        if kind == "transient":
            with a: params["t_stop"] = spice_input("t_stop (s)", defaults["t_stop"], f"ts_{h}")
            with b: params["t_step"] = spice_input("t_step (s)", defaults["t_step"], f"td_{h}")
        elif kind == "ac_sweep":
            with a: params["f_start"] = spice_input("f_start (Hz)", defaults["f_start"], f"f1_{h}")
            with b: params["f_stop"] = spice_input("f_stop (Hz)", defaults["f_stop"], f"f2_{h}")
            with c: params["ppd"] = st.number_input("Points / decade", 5, 200, int(defaults["ppd"]), key=f"ppd_{h}")
        elif kind == "dc_sweep":
            srcs = runner.dc_sources(circuit)
            if srcs:
                with a: params["source"] = st.selectbox("Sweep source", srcs, key=f"src_{h}")
                with b: params["v_start"] = spice_input("Start (V)", defaults["v_start"], f"v1_{h}")
                with c: params["v_stop"] = spice_input("Stop (V)", defaults["v_stop"], f"v2_{h}")
                params["steps"] = st.slider("Steps", 10, 1000, int(defaults["steps"]), key=f"st_{h}")
            else:
                valid = False
                st.warning("DC sweep needs a DC voltage source in the circuit.")
        else:
            st.caption("Solves the circuit once with capacitors open and inductors shorted. No parameters needed.")
        if any(v is None for v in params.values()):
            valid = False

    if st.button("▶ Run simulation", type="primary", disabled=not valid):
        try:
            # the solver mutates nothing persistent, but re-parse for a clean state each run
            circuit, parser = runner.parse_netlist(active_netlist)
            with st.spinner("Solving…"):
                if kind == "transient":
                    res = runner.run_transient(circuit, params["t_stop"], params["t_step"])
                elif kind == "ac_sweep":
                    res = runner.run_ac_sweep(circuit, params["f_start"], params["f_stop"], params["ppd"])
                elif kind == "dc_sweep":
                    res = runner.run_dc_sweep(circuit, params["source"], params["v_start"], params["v_stop"], params["steps"])
                else:
                    res = runner.run_dc_op(circuit)
            res["netlist"], res["nodes"] = active_netlist, nodes
            res["n_components"] = len(circuit.components) + len(circuit.diodes) + len(circuit.capacitors) + len(circuit.inductors)
            ss.result = res
            ss.result_error = None
        except ValueError as e:
            ss.result, ss.result_error = None, f"Simulation failed: {e}"
        except Exception as e:  # noqa: BLE001
            ss.result, ss.result_error = None, f"Unexpected error: {type(e).__name__}: {e}"

    if ss.get("result_error"):
        st.error(ss.result_error)

    # ----------------------------------------------------------------------
    # results
    # ----------------------------------------------------------------------
    res = ss.result
    if res is not None:
        st.markdown(theme.section("Results"), unsafe_allow_html=True)
        m = st.columns(4)
        m[0].markdown(theme.metric(runner.ANALYSIS_LABELS[res["kind"]], "analysis", "a"), unsafe_allow_html=True)
        m[1].markdown(theme.metric(res["n_components"], "elements", "b"), unsafe_allow_html=True)
        m[2].markdown(theme.metric(len(res["nodes"]), "nodes (excl. ground)", "c"), unsafe_allow_html=True)
        m[3].markdown(theme.metric(f"{res['elapsed'] * 1000:.0f} ms", "solve time", "d"), unsafe_allow_html=True)
        st.write("")

        t_plot, t_data, t_net = st.tabs(["📈 Plot", "🔢 Data", "📄 Netlist used"])
        with t_plot:
            if res["kind"] == "dc_op":
                st.pyplot(plots.plot_dc_op(res), use_container_width=True)
            else:
                store = res["magnitude_db"] if res["kind"] == "ac_sweep" else res["node_voltages"]
                shown = [n for n in sel_nodes if f"V({n})" in store]
                if shown:
                    st.pyplot(plots.plot_result(res, shown), use_container_width=True)
                else:
                    st.info("Pick at least one node to plot.")
                if res["kind"] == "dc_sweep":
                    st.pyplot(plots.plot_iv(res), use_container_width=True)
        with t_data:
            if res["kind"] == "dc_op":
                rows = [{"quantity": k, "value": v, "unit": "V"} for k, v in res["node_voltages"].items()]
                rows += [{"quantity": k, "value": v, "unit": "A"} for k, v in res["source_currents"].items()]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                csv = runner.results_to_csv(res)
                df = pd.read_csv(io.StringIO(csv))
                st.dataframe(df.head(2000), use_container_width=True, hide_index=True)
                if len(df) > 2000:
                    st.caption(f"Showing the first 2000 of {len(df)} rows - download the CSV for everything.")
            st.download_button("⬇ Download CSV", runner.results_to_csv(res),
                               file_name=f"{res['kind']}_results.csv", mime="text/csv")
        with t_net:
            st.code(res["netlist"], language="text")
