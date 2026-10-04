import numpy as np
import matplotlib.pyplot as plt

class DCSweep:
    def __init__(self, circuit):
        self.circuit = circuit

    def sweep_v_source(self, source_name, v_start, v_stop, steps):
        """Sweeps a voltage source and records the resulting current."""
        # Find the index of the voltage source in the circuit's component list
        source_idx = None
        for i, comp in enumerate(self.circuit.components):
            if comp[0] == 'V' and comp[1] == source_name:
                source_idx = i
                break
                
        if source_idx is None:
            raise ValueError(f"Voltage source '{source_name}' not found in circuit.")

        voltages = np.linspace(v_start, v_stop, steps)
        currents = []

        print(f"Sweeping {source_name} from {v_start}V to {v_stop}V...")

        for v in voltages:
            # Update the voltage source value dynamically
            comp = list(self.circuit.components[source_idx])
            comp[4] = float(v)
            self.circuit.components[source_idx] = tuple(comp)
            
            # Solve the circuit for this specific voltage step
            results = self.circuit.solve()
            
            # Extract the current. (MNA calculates current leaving the source, 
            # so we multiply by -1 to get the current drawn by the circuit)
            i_val = -results["source_currents"][f"I({source_name})"]
            currents.append(i_val)

        return voltages, currents

    def plot_iv_curve(self, voltages, currents, title="Diode I-V Characteristic"):
        """Plots the sweep data using Matplotlib."""
        plt.figure(figsize=(8, 5))
        plt.plot(voltages, currents, label="Simulated Current", color='blue', linewidth=2)
        plt.title(title)
        plt.xlabel("Voltage (V)")
        plt.ylabel("Current (A)")
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        plt.axhline(y=0, color='k', linewidth=1)
        plt.axvline(x=0, color='k', linewidth=1)
        plt.legend()
        plt.tight_layout()
        plt.show()