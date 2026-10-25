import numpy as np
import matplotlib.pyplot as plt

class DCSweep:
    def __init__(self, circuit):
        self.circuit = circuit

    def sweep_v_source(self, source_name, v_start, v_stop, steps):
        """Sweeps a voltage source and records currents AND node voltages."""
        source_idx = None
        for i, comp in enumerate(self.circuit.components):
            if comp[0] == 'V' and comp[1] == source_name:
                source_idx = i
                break
                
        if source_idx is None:
            raise ValueError(f"Voltage source '{source_name}' not found in circuit.")

        voltages = np.linspace(v_start, v_stop, steps)
        currents = []
        self.node_history = {}
        self.source_history = {}

        x_prev = None
        self.circuit._map_nodes()
        N = len(self.circuit.node_map) - 1

        print(f"Sweeping {source_name} from {v_start}V to {v_stop}V...")

        for v in voltages:
            comp = list(self.circuit.components[source_idx])
            comp[4] = float(v)
            self.circuit.components[source_idx] = tuple(comp)
            
            # Warm-start each step from the previous solution
            x_sol = self.circuit.solve(max_iter=400, x_prev=x_prev, return_raw=True)
            x_prev = x_sol
            results = self.circuit._format_results(x_sol, N)
            
            # Record all node voltages at this sweep step
            for n_key, n_val in results["node_voltages"].items():
                self.node_history.setdefault(n_key, []).append(n_val)

            # Record all voltage source currents at this sweep step
            for s_key, s_val in results["source_currents"].items():
                self.source_history.setdefault(s_key, []).append(-s_val)

            i_val = -results["source_currents"][f"I({source_name})"]
            currents.append(i_val)

        return voltages, currents

    def plot_iv_curve(self, voltages, currents, title="DC Sweep Characteristic"):
        """Plots the sweep data. Automatically detects Gate sweeps (where I_gate == 0)."""
        # If the swept source current is 0 everywhere (e.g., sweeping a MOSFET Gate like VIN or VG)
        if np.max(np.abs(currents)) < 1e-11 and hasattr(self, 'node_history'):
            # Check if there is another supply source (like VD or VDD) carrying current
            other_currents = {
                k: v for k, v in self.source_history.items() 
                if np.max(np.abs(v)) > 1e-11
            }

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)

            # Top Plot: Node Voltages (e.g. CMOS Inverter Vout vs Vin)
            for node_name, node_vals in self.node_history.items():
                ax1.plot(voltages, node_vals, linewidth=2, label=node_name)
            ax1.set_title(f"{title} — Voltage Transfer Characteristic (VTC)")
            ax1.set_ylabel("Node Voltage (V)")
            ax1.grid(True, which='both', linestyle='--', linewidth=0.5)
            ax1.legend()

            # Bottom Plot: Drain / Supply Current (I(VDD) or I(VD))
            if other_currents:
                for src_name, src_vals in other_currents.items():
                    ax2.plot(voltages, src_vals, color='crimson', linewidth=2, label=f"Supply Current {src_name}")
            else:
                ax2.plot(voltages, currents, color='blue', linewidth=2, label="Gate Current")
            ax2.set_title("Supply / Drain Current vs Input Voltage")
            ax2.set_xlabel("Swept Input Voltage (V)")
            ax2.set_ylabel("Current (A)")
            ax2.grid(True, which='both', linestyle='--', linewidth=0.5)
            ax2.legend()

            plt.tight_layout()
            plt.show()
            return

        # Standard I-V Plot (Diode, Resistor, or MOSFET Drain Sweep VD)
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