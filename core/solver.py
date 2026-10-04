import numpy as np
from core.devices import Diode

class Circuit:
    def __init__(self):
        self.components = []
        self.diodes = []
        self.capacitors = []
        self.inductors = []
        self.nodes = set()
        self.node_map = {}
        self.v_source_count = 0

    def add_resistor(self, name, n1, n2, value):
        self.components.append(('R', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])

    def add_v_source(self, name, n1, n2, dc_val=0.0, ac_mag=0.0, ac_phase=0.0, wave_type='DC', wave_amp=0.0, wave_freq=0.0):
        self.components.append(('V', name, str(n1), str(n2), float(dc_val), float(ac_mag), float(ac_phase), wave_type, float(wave_amp), float(wave_freq)))
        self.nodes.update([str(n1), str(n2)])
        self.v_source_count += 1

    def add_i_source(self, name, n1, n2, dc_val=0.0, ac_mag=0.0, ac_phase=0.0, wave_type='DC', wave_amp=0.0, wave_freq=0.0):
        self.components.append(('I', name, str(n1), str(n2), float(dc_val), float(ac_mag), float(ac_phase), wave_type, float(wave_amp), float(wave_freq)))
        self.nodes.update([str(n1), str(n2)])
        
    def add_diode(self, name, n1, n2, Is=1e-14, n=1.0):
        self.diodes.append(Diode(name, n1, n2, Is, n))
        self.nodes.update([str(n1), str(n2)])

    def add_capacitor(self, name, n1, n2, value):
        self.capacitors.append(('C', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])
        
    def add_inductor(self, name, n1, n2, value):
        self.inductors.append(('L', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])

    
    def _map_nodes(self):
        active_nodes = sorted(list(self.nodes - {'0'}))
        self.node_map = {node: i for i, node in enumerate(active_nodes)}
        self.node_map['0'] = -1

    def _format_results(self, x, N):
        results = {"node_voltages": {}, "source_currents": {}}
        for node, idx in self.node_map.items():
            if node != '0':
                results["node_voltages"][f"V({node})"] = round(x[idx], 6)
                
        v_idx = 0
        for comp in self.components:
            if comp[0] == 'V':
                results["source_currents"][f"I({comp[1]})"] = round(x[N + v_idx], 6)
                v_idx += 1
                
        l_idx = 0
        for comp in self.inductors:
            results["source_currents"][f"I({comp[1]})"] = round(x[N + self.v_source_count + l_idx], 6)
            l_idx += 1
            
        return results

    def solve(self, max_iter=200, tol=1e-6, dt=None, x_prev=None, return_raw=False, t=0.0):
        self._map_nodes()
        N = len(self.node_map) - 1
        
        # CRITICAL FIX: Matrix dimensions now include inductors
        M = self.v_source_count + len(self.inductors) 
        
        if N + M == 0:
            raise ValueError("Circuit is completely empty. Check your netlist for parsing errors.")
        
        A_lin = np.zeros((N + M, N + M))
        z_lin = np.zeros(N + M)
        
        v_idx = 0
        for comp in self.components:
            # Safely unpack the base components
            comp_type = comp[0]
            name = comp[1]
            n1 = comp[2]
            n2 = comp[3]
            dc_val = comp[4] 
            
            # --- TRANSIENT SINE WAVE INJECTION ---
            wave_type = comp[7] if len(comp) > 7 else 'DC'
            
            if wave_type == 'SINE' and len(comp) > 9:
                wave_amp, wave_freq = comp[8], comp[9]
                val = wave_amp * np.sin(2.0 * np.pi * wave_freq * t)
            else:
                val = dc_val # Resistance for 'R', or static DC value for 'V'/'I'
            # ---------------------------------------
            
            idx1, idx2 = self.node_map[n1], self.node_map.get(n2, -1)
            
            if comp_type == 'R':
                g = 1.0 / val
                if idx1 != -1: A_lin[idx1, idx1] += g
                if idx2 != -1: A_lin[idx2, idx2] += g
                if idx1 != -1 and idx2 != -1:
                    A_lin[idx1, idx2] -= g
                    A_lin[idx2, idx1] -= g
            elif comp_type == 'V':
                row = N + v_idx
                if idx1 != -1:
                    A_lin[idx1, row] += 1
                    A_lin[row, idx1] += 1
                if idx2 != -1:
                    A_lin[idx2, row] -= 1
                    A_lin[row, idx2] -= 1
                z_lin[row] = val
                v_idx += 1
            elif comp_type == 'I':
                if idx1 != -1: z_lin[idx1] -= val 
                if idx2 != -1: z_lin[idx2] += val

        # --- Inductor Stamps ---
        l_idx = 0
        for comp in self.inductors:
            _, name, n1, n2, L = comp
            idx1, idx2 = self.node_map[n1], self.node_map[n2]
            row = N + self.v_source_count + l_idx
            
            if idx1 != -1:
                A_lin[idx1, row] += 1
                A_lin[row, idx1] += 1
            if idx2 != -1:
                A_lin[idx2, row] -= 1
                A_lin[row, idx2] -= 1
                
            if dt is not None and x_prev is not None:
                A_lin[row, row] -= L / dt
                z_lin[row] = - (L / dt) * x_prev[row]
            
            l_idx += 1

        # --- Capacitor Stamps ---
        if dt is not None and x_prev is not None:
            for comp in self.capacitors:
                _, name, n1, n2, C = comp
                idx1, idx2 = self.node_map[n1], self.node_map[n2]
                g_c = C / dt
                
                if idx1 != -1: A_lin[idx1, idx1] += g_c
                if idx2 != -1: A_lin[idx2, idx2] += g_c
                if idx1 != -1 and idx2 != -1:
                    A_lin[idx1, idx2] -= g_c
                    A_lin[idx2, idx1] -= g_c
                    
                v1_prev = x_prev[idx1] if idx1 != -1 else 0.0
                v2_prev = x_prev[idx2] if idx2 != -1 else 0.0
                i_hist = g_c * (v1_prev - v2_prev)
                
                if idx1 != -1: z_lin[idx1] += i_hist
                if idx2 != -1: z_lin[idx2] -= i_hist

        x = np.zeros(N + M) 
        
        for iteration in range(max_iter):
            A = np.copy(A_lin)
            z = np.copy(z_lin)
            
            for diode in self.diodes:
                idx1, idx2 = self.node_map[diode.n1], self.node_map[diode.n2]
                v1 = x[idx1] if idx1 != -1 else 0.0
                v2 = x[idx2] if idx2 != -1 else 0.0
                vd = v1 - v2
                
                Id = diode.get_current(vd)
                gd = diode.get_conductance(vd)
                Ieq = Id - (gd * vd)
                
                if idx1 != -1: A[idx1, idx1] += gd
                if idx2 != -1: A[idx2, idx2] += gd
                if idx1 != -1 and idx2 != -1:
                    A[idx1, idx2] -= gd
                    A[idx2, idx1] -= gd
                    
                if idx1 != -1: z[idx1] -= Ieq
                if idx2 != -1: z[idx2] += Ieq
                
            try:
                x_new = np.linalg.solve(A, z)
            except np.linalg.LinAlgError:
                raise ValueError("Singular matrix encountered.")
                
            if np.max(np.abs(x_new - x)) < tol:
                if return_raw:
                    return x_new
                return self._format_results(x_new, N)
                
            x = x_new 
            
        raise ValueError(f"Failed to converge after {max_iter} iterations.")
    
    def solve_ac(self, freq, dc_op):
        self._map_nodes()
        N = len(self.node_map) - 1
        M = self.v_source_count + len(self.inductors)
        
        A_ac = np.zeros((N + M, N + M), dtype=np.complex128)
        z_ac = np.zeros(N + M, dtype=np.complex128)
        
        omega = 2.0 * np.pi * freq
        
        # --- Base Components (R, V, I) ---
        v_idx = 0
        for comp in self.components:
            comp_type, name, n1, n2, val = comp[0:5]
            idx1, idx2 = self.node_map[n1], self.node_map.get(n2, -1)
            
            if comp_type == 'R':
                g = 1.0 / val
                if idx1 != -1: A_ac[idx1, idx1] += g
                if idx2 != -1: A_ac[idx2, idx2] += g
                if idx1 != -1 and idx2 != -1:
                    A_ac[idx1, idx2] -= g
                    A_ac[idx2, idx1] -= g
                    
            elif comp_type == 'V' or comp_type == 'I':
                ac_mag, ac_phase = comp[5], comp[6]
                # Euler's Formula: Convert Polar (Mag, Phase) to Rectangular Complex
                phasor = ac_mag * np.exp(1j * np.deg2rad(ac_phase))
                
                if comp_type == 'V':
                    row = N + v_idx
                    if idx1 != -1:
                        A_ac[idx1, row] += 1
                        A_ac[row, idx1] += 1
                    if idx2 != -1:
                        A_ac[idx2, row] -= 1
                        A_ac[row, idx2] -= 1
                    z_ac[row] = phasor
                    v_idx += 1
                else:
                    if idx1 != -1: z_ac[idx1] -= phasor
                    if idx2 != -1: z_ac[idx2] += phasor

        # --- Reactive Components (C, L) ---
        for comp in self.capacitors:
            _, name, n1, n2, C = comp
            idx1, idx2 = self.node_map[n1], self.node_map[n2]
            Yc = 1j * omega * C  # Admittance of Capacitor
            if idx1 != -1: A_ac[idx1, idx1] += Yc
            if idx2 != -1: A_ac[idx2, idx2] += Yc
            if idx1 != -1 and idx2 != -1:
                A_ac[idx1, idx2] -= Yc
                A_ac[idx2, idx1] -= Yc
                
        l_idx = 0
        for comp in self.inductors:
            _, name, n1, n2, L = comp
            idx1, idx2 = self.node_map[n1], self.node_map[n2]
            row = N + self.v_source_count + l_idx
            
            if idx1 != -1:
                A_ac[idx1, row] += 1
                A_ac[row, idx1] += 1
            if idx2 != -1:
                A_ac[idx2, row] -= 1
                A_ac[row, idx2] -= 1
                
            A_ac[row, row] -= 1j * omega * L  # Impedance of Inductor
            l_idx += 1

        # --- Small-Signal Diodes ---
        for diode in self.diodes:
            idx1, idx2 = self.node_map[diode.n1], self.node_map[diode.n2]
            # Pull static DC voltage to calculate locked dynamic conductance
            v1_dc = dc_op["node_voltages"].get(f"V({diode.n1})", 0.0) if idx1 != -1 else 0.0
            v2_dc = dc_op["node_voltages"].get(f"V({diode.n2})", 0.0) if idx2 != -1 else 0.0
            gd = diode.get_conductance(v1_dc - v2_dc)
            
            if idx1 != -1: A_ac[idx1, idx1] += gd
            if idx2 != -1: A_ac[idx2, idx2] += gd
            if idx1 != -1 and idx2 != -1:
                A_ac[idx1, idx2] -= gd
                A_ac[idx2, idx1] -= gd
                
        try:
            x_ac = np.linalg.solve(A_ac, z_ac)
            return self._format_results_ac(x_ac, N)
        except np.linalg.LinAlgError:
            raise ValueError("Singular complex matrix encountered.")

    def _format_results_ac(self, x, N):
        results = {"node_voltages": {}}
        for node, idx in self.node_map.items():
            if node != '0':
                results["node_voltages"][f"V({node})"] = x[idx]
        return results