import numpy as np
from core.devices import Diode

class Circuit:
    def __init__(self):
        self.components = []
        self.diodes = []
        self.capacitors = []
        self.nodes = set()
        self.node_map = {}
        self.v_source_count = 0

    def add_resistor(self, name, n1, n2, value):
        self.components.append(('R', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])

    def add_v_source(self, name, n1, n2, value):
        self.components.append(('V', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])
        self.v_source_count += 1

    def add_i_source(self, name, n1, n2, value):
        self.components.append(('I', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])

    def add_diode(self, name, n1, n2, Is=1e-14, n=1.0):
        self.diodes.append(Diode(name, n1, n2, Is, n))
        self.nodes.update([str(n1), str(n2)])

    def add_capacitor(self, name, n1, n2, value):
        self.capacitors.append(('C', name, str(n1), str(n2), float(value)))
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
        return results

    def solve(self, max_iter=200, tol=1e-6, dt=None, x_prev=None, return_raw=False):
        self._map_nodes()
        N = len(self.node_map) - 1
        M = self.v_source_count
        
        A_lin = np.zeros((N + M, N + M))
        z_lin = np.zeros(N + M)
        
        # --- Base Linear Components (R, V, I) ---
        v_idx = 0
        for comp in self.components:
            comp_type, name, n1, n2, val = comp
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

        # --- Transient Capacitor Stamps (Backward Euler) ---
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

        # --- Newton-Raphson Loop ---
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