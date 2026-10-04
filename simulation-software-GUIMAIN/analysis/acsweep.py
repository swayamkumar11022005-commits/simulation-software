import numpy as np
import matplotlib.pyplot as plt

class ACSweep:
    def __init__(self, circuit):
        self.circuit = circuit

    def run(self, f_start, f_stop, points_per_decade=20):
        # Calculate static DC operating point first to linearize non-linear components
        dc_op = self.circuit.solve()
        
        num_decades = np.log10(f_stop) - np.log10(f_start)
        total_points = int(num_decades * points_per_decade)
        frequencies = np.logspace(np.log10(f_start), np.log10(f_stop), total_points)
        
        results = {"frequencies": frequencies, "magnitude_db": {}, "phase_deg": {}}
        
        print(f"Running AC Sweep from {f_start}Hz to {f_stop}Hz...")
        
        for f in frequencies:
            ac_state = self.circuit.solve_ac(f, dc_op)
            
            for node, complex_v in ac_state["node_voltages"].items():
                if node not in results["magnitude_db"]:
                    results["magnitude_db"][node] = []
                    results["phase_deg"][node] = []
                    
                # Calculate dB: 20 * log10(|V|)
                mag = np.abs(complex_v)
                mag_db = 20 * np.log10(mag) if mag > 1e-12 else -240
                phase = np.rad2deg(np.angle(complex_v))
                
                results["magnitude_db"][node].append(mag_db)
                results["phase_deg"][node].append(phase)
                
        return results

    def plot_bode(self, results, plot_nodes):
        freqs = results["frequencies"]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        
        for node in plot_nodes:
            node_key = f"V({node})"
            if node_key in results["magnitude_db"]:
                ax1.semilogx(freqs, results["magnitude_db"][node_key], label=node_key, linewidth=2)
                ax2.semilogx(freqs, results["phase_deg"][node_key], label=node_key, linewidth=2)
                
        ax1.set_title("Bode Plot: Magnitude")
        ax1.set_ylabel("Magnitude (dB)")
        ax1.grid(True, which="both", ls="--", linewidth=0.5)
        ax1.legend()
        
        ax2.set_title("Bode Plot: Phase")
        ax2.set_xlabel("Frequency (Hz)")
        ax2.set_ylabel("Phase (Degrees)")
        ax2.grid(True, which="both", ls="--", linewidth=0.5)
        
        plt.tight_layout()
        plt.show()