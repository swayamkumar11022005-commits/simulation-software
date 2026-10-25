import os
from core.parser import NetlistParser
from analysis.dcsweep import DCSweep
from analysis.transient import TransientAnalysis
from analysis.acsweep import ACSweep

def run_simulation(target_file="circuit.net"):
    # 1. OS Check: Look for the physical file in the directory
    if not os.path.exists(target_file):
        print(f"Error: Could not find '{target_file}' in the current directory.")
        print("Please ensure your netlist file is saved exactly as 'circuit.net'.")
        return

    print(f"Found local netlist: {target_file}")
    print(f"Reading netlist: {target_file}...\n")

    try:
        # 2. Parse the Netlist
        parser = NetlistParser(target_file)
        circuit = parser.parse()

        if circuit.mosfets:
            print(f"BSIM4 Engine: Loaded {len(circuit.mosfets)} transistor(s): "
                  f"{[m.name for m in circuit.mosfets]} (Version {circuit.mosfets[0].version})")

        # 3. Topology Router: Decide between DC, AC, and Transient
        analysis_type = parser.determine_analysis_type()
        
        if analysis_type == "dc_transient":
            print("Router: Capacitors/Inductors detected. Running DC Transient Analysis...")
            analyzer = TransientAnalysis(circuit)
            results = analyzer.run(t_stop=0.005, t_step=0.0001)
            active_nodes = [n for n in circuit.node_map.keys() if n != '0']
            analyzer.plot(results, plot_nodes=active_nodes[:3])
            
        elif analysis_type == "ac_transient":
            print("Router: SINE wave detected. Running AC Transient Analysis...")
            analyzer = TransientAnalysis(circuit)
            results = analyzer.run(t_stop=0.05, t_step=0.0001)
            active_nodes = [n for n in circuit.node_map.keys() if n != '0']
            analyzer.plot(results, plot_nodes=active_nodes[:3])
            
        elif analysis_type == "ac_sweep":
            print("Router: AC source detected. Running AC Small-Signal Sweep...")
            analyzer = ACSweep(circuit)
            results = analyzer.run(f_start=10, f_stop=100000, points_per_decade=20)
            active_nodes = [n for n in circuit.node_map.keys() if n != '0']
            analyzer.plot_bode(results, plot_nodes=active_nodes[:3])
            
        elif analysis_type == "dc_sweep":
            print("Router: Static topology detected...")
            v_sources = [comp[1] for comp in circuit.components if comp[0] == 'V']
            if v_sources:
                analyzer = DCSweep(circuit)
                sweep_target = v_sources[0]

                # Use CMOS-safe sweep range (0V to 3.0V) if BSIM4 MOSFETs are present
                if circuit.mosfets:
                    v_start, v_stop, steps = 0.0, 3.0, 150
                    title = f"BSIM4.8.3 MOSFET Characteristic (Sweeping {sweep_target})"
                else:
                    v_start, v_stop, steps = -5.0, 15.0, 200
                    title = f"DC Sweep for {sweep_target}"

                print(f"Running DC Sweep on {sweep_target} ({v_start}V to {v_stop}V)...")
                voltages, currents = analyzer.sweep_v_source(sweep_target, v_start, v_stop, steps)

                # Print final operating point & BSIM4 parameters
                op = circuit.solve()
                print("\n--- Final Operating Point Node Voltages ---")
                for node, voltage in op["node_voltages"].items():
                    print(f"  {node}: {voltage} V")

                if circuit.mosfets:
                    print("\n--- BSIM4.8.3 Transistor Operating Point ---")
                    for mos in circuit.mosfets:
                        vd = op["node_voltages"].get(f"V({mos.d})", 0.0)
                        vg = op["node_voltages"].get(f"V({mos.g})", 0.0)
                        vs = op["node_voltages"].get(f"V({mos.s})", 0.0)
                        vb = op["node_voltages"].get(f"V({mos.b})", 0.0)
                        st = mos.evaluate(vd, vg, vs, vb)
                        print(f"  {mos.name} (W={mos.W*1e6:.2f}u, L={mos.L*1e6:.2f}u, mult_i={mos.mult_i}, mult_q={mos.mult_q}):")
                        print(f"    Ids  = {st['Ids']:.6e} A")
                        print(f"    gm   = {st['gm']:.6e} S")
                        print(f"    gds  = {st['gds']:.6e} S")
                        print(f"    gmbs = {st['gmbs']:.6e} S")
                        print(f"    Cgg  = {st['cgg']:.6e} F")

                analyzer.plot_iv_curve(voltages, currents, title=title)
            else:
                print("No voltage source found for a sweep. Calculating static DC Operating Point...")
                results = circuit.solve()
                for node, voltage in results["node_voltages"].items():
                    print(f"{node}: {voltage} V")
                
    except Exception as e:
        print(f"Simulation failed: {e}")

if __name__ == "__main__":
    run_simulation("circuit.net")