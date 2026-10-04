###
Simulation software

the MNA is implemented in a basic way like its main.py, you have to specify the circuit first in the main.py in order to get its nodeal analysis (for now it can calculate voltages and currents on nodes)

in the current main.py we have used these

![image](images/WhatsApp%20Image%202026-08-23%20at%2013.06.25.jpeg)

as the examples

## Circuit Studio (web UI)

```
pip install -r requirements.txt
streamlit run app.py
```

Two ways to define a circuit, one simulation pipeline:

* **Draw circuit** - drag R, C, L, DC/Sine/AC voltage sources, DC/Sine/AC current sources, diodes and
  ground from the palette, wire terminal to terminal, click a part to edit its values
  (SPICE suffixes such as `4.7k`, `10u`, `2MEG`). `core/schematic.py` converts the drawing into a netlist
  (shown live below the canvas) which is parsed by the existing `NetlistParser`.
* **Netlist editor** - type the netlist by hand; "Edit as netlist" copies a drawn circuit there.

Analyses: DC operating point, transient, AC sweep (Bode) and DC sweep, auto-detected with the same
router as `main.py` or chosen manually. Results can be exported as CSV.

Editor shortcuts: `W` wire, `V` select, `R` rotate, `Del` delete, `Ctrl+Z/Y` undo/redo, scroll to zoom,
drag the background to pan. A wire that passes over a terminal connects to it (a dot marks the junction).
