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
            # You may want a longer t_stop here depending on the SINE frequency (e.g., 60Hz needs ~0.05s)
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
                print("Running DC Sweep...")
                analyzer = DCSweep(circuit)
                sweep_target = v_sources[0]
                voltages, currents = analyzer.sweep_v_source(sweep_target, -5.0, 15.0, 200)
                analyzer.plot_iv_curve(voltages, currents, title=f"DC Sweep for {sweep_target}")
            else:
                print("No voltage source found for a sweep. Calculating static DC Operating Point...")
                results = circuit.solve()
                for node, voltage in results["node_voltages"].items():
                    print(f"{node}: {voltage} V")
                
    except Exception as e:
        print(f"Simulation failed: {e}")

if __name__ == "__main__":
    run_simulation("circuit.net")