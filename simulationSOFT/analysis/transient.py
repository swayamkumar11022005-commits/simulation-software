import numpy as np
import matplotlib.pyplot as plt

class TransientAnalysis:
    def __init__(self, circuit):
        self.circuit = circuit

    def run(self, t_stop, t_step):
        self.circuit._map_nodes()
        N = len(self.circuit.node_map) - 1
        
        # CRITICAL FIX: Expanded to provide history storage for inductor current
        M = self.circuit.v_source_count + len(self.circuit.inductors)
        
        times = np.arange(0, t_stop, t_step)
        x_prev = np.zeros(N + M)  
        
        results_history = {"times": times, "node_voltages": {}}
        print(f"Solving transient response from 0 to {t_stop}s (Step: {t_step}s)...")
        
        for t in times:
            # The crucial 't=t' argument injects the current time into the sine wave
            x_new = self.circuit.solve(dt=t_step, x_prev=x_prev, return_raw=True, t=t)
            
            formatted = self.circuit._format_results(x_new, N)
            
            for node, voltage in formatted["node_voltages"].items():
                if node not in results_history["node_voltages"]:
                    results_history["node_voltages"][node] = []
                results_history["node_voltages"][node].append(voltage)
                
            x_prev = x_new  
            
        return results_history

    def plot(self, results, plot_nodes):
        plt.figure(figsize=(8, 5))
        times = results["times"] * 1000 
        
        for node in plot_nodes:
            voltages = results["node_voltages"].get(f"V({node})")
            if voltages:
                plt.plot(times, voltages, label=f"V({node})", linewidth=2)
                
        plt.title("Transient Response")
        plt.xlabel("Time (ms)")
        plt.ylabel("Voltage (V)")
        plt.grid(True, linestyle='--', linewidth=0.5)
        plt.legend()
        plt.tight_layout()
        plt.show()