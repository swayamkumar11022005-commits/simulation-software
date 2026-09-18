import numpy as np
import matplotlib.pyplot as plt

class TransientAnalysis:
    def __init__(self, circuit):
        self.circuit = circuit

    def run(self, t_stop, t_step):
        self.circuit._map_nodes()
        N = len(self.circuit.node_map) - 1
        M = self.circuit.v_source_count
        
        times = np.arange(0, t_stop, t_step)
        x_prev = np.zeros(N + M)  # Assume initial state is 0V/0A
        
        results_history = {"times": times, "node_voltages": {}}
        
        print(f"Running transient analysis (Step: {t_step}s, Stop: {t_stop}s)...")
        
        for t in times:
            try:
                # Pass previous state into solver
                x_new = self.circuit.solve(dt=t_step, x_prev=x_prev, return_raw=True)
            except ValueError as e:
                raise ValueError(f"Transient solver failed at t={t}: {e}")
                
            formatted = self.circuit._format_results(x_new, N)
            
            # Store voltages for plotting
            for node, voltage in formatted["node_voltages"].items():
                if node not in results_history["node_voltages"]:
                    results_history["node_voltages"][node] = []
                results_history["node_voltages"][node].append(voltage)
                
            x_prev = x_new # Advance time
            
        return results_history

    def plot(self, results, plot_nodes):
        plt.figure(figsize=(8, 5))
        times = results["times"]
        
        for node in plot_nodes:
            voltages = results["node_voltages"].get(f"V({node})")
            if voltages:
                plt.plot(times, voltages, label=f"V({node})", linewidth=2)
                
        plt.title("Transient Response")
        plt.xlabel("Time (s)")
        plt.ylabel("Voltage (V)")
        plt.grid(True, linestyle='--', linewidth=0.5)
        plt.legend()
        plt.show()