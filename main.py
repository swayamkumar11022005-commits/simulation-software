from core.parser import NetlistParser
from analysis.dcsweep import DCSweep

def run_dc_sweep(netlist_file):
    # 1. Parse the netlist
    parser = NetlistParser(netlist_file)
    circuit = parser.parse()
    
    # 2. Initialize the Sweep Analyzer
    analyzer = DCSweep(circuit)
    
    # 3. Sweep V1 from 0.0V to 1.0V over 100 data points
    try:
        voltages, currents = analyzer.sweep_v_source('V1', 0.0, 1.0, 100)
    except ValueError as e:
        print(f"Sweep failed: {e}")
        return

    # 4. Generate the plot
    analyzer.plot_iv_curve(voltages, currents, title="1N4148 Diode I-V Curve (Simulated)")

if __name__ == "__main__":
    run_dc_sweep("circuit.net")