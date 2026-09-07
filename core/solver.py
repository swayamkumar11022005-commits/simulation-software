import numpy as np
from core.devices import Diode

class Circuit:
    def __init__(self):
        self.components = []
        self.diodes = []
        self.nodes = set()
        self.node_map = {}
        self.v_source_count = 0
        
    def add_resistor(self, name, n1, n2, value):
        """Adds a resistor to the circuit."""
        self.components.append(('R', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])
        
    def add_v_source(self, name, n1, n2, value):
        """Adds an independent DC voltage source."""
        self.components.append(('V', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])
        self.v_source_count += 1
        
    def add_i_source(self, name, n1, n2, value):
        """Adds an independent DC current source."""
        self.components.append(('I', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])

    def _map_nodes(self):
        """Maps string node names to integer matrix indices. Ground ('0') is ignored."""
        # Sort to ensure consistent matrix indexing
        active_nodes = sorted(list(self.nodes - {'0'}))
        self.node_map = {node: i for i, node in enumerate(active_nodes)}
        self.node_map['0'] = -1  # Ground doesn't get a row/col in the MNA matrix

    def add_diode(self, name, n1, n2, Is=1e-14, n=1.0):
        self.diodes.append(Diode(name, n1, n2, Is, n))
        self.nodes.update([str(n1), str(n2)])

    def solve(self, max_iter=50, tol=1e-6):
        self._map_nodes()
        N = len(self.node_map) - 1
        M = self.v_source_count
        
        # 1. Build the STATIC linear base matrices
        A_lin = np.zeros((N + M, N + M))
        z_lin = np.zeros(N + M)
        
        v_idx = 0
        for comp in self.components:
            comp_type, name, n1, n2, val = comp
            idx1, idx2 = self.node_map[n1], self.node_map[n2]
            
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

        # 2. Newton-Raphson Iteration
        x = np.zeros(N + M) # Initial guess: 0V at all nodes
        
        for iteration in range(max_iter):
            A = np.copy(A_lin)
            z = np.copy(z_lin)
            
            # Add non-linear contributions
            for diode in self.diodes:
                idx1, idx2 = self.node_map[diode.n1], self.node_map[diode.n2]
                
                # Get current voltage guess across the diode
                v1 = x[idx1] if idx1 != -1 else 0.0
                v2 = x[idx2] if idx2 != -1 else 0.0
                vd = v1 - v2
                
                # Calculate device state
                Id = diode.get_current(vd)
                gd = diode.get_conductance(vd)
                Ieq = Id - (gd * vd)
                
                # Stamp dynamic conductance into A matrix
                if idx1 != -1: A[idx1, idx1] += gd
                if idx2 != -1: A[idx2, idx2] += gd
                if idx1 != -1 and idx2 != -1:
                    A[idx1, idx2] -= gd
                    A[idx2, idx1] -= gd
                    
                # Stamp equivalent current into z vector
                if idx1 != -1: z[idx1] -= Ieq
                if idx2 != -1: z[idx2] += Ieq
                
            # Solve linearized system
            try:
                x_new = np.linalg.solve(A, z)
            except np.linalg.LinAlgError:
                raise ValueError("Singular matrix encountered.")
                
            # Check convergence
            if np.max(np.abs(x_new - x)) < tol:
                print(f"Converged in {iteration + 1} iterations.")
                return self._format_results(x_new, N)
                
            # REMOVE THE DAMPING (alpha = 0.2). Let Newton-Raphson run at full speed!
            x = x_new
        
        raise ValueError(f"Failed to converge after {max_iter} iterations.")
    
    
    def _format_results(self, x, N):
        """Packages the solved numpy array into a readable dictionary."""
        results = {"node_voltages": {}, "source_currents": {}}
        
        # Extract Node Voltages
        for node, idx in self.node_map.items():
            if node != '0':
                results["node_voltages"][f"V({node})"] = round(x[idx], 6)
                
        # Extract Voltage Source Currents
        v_idx = 0
        for comp in self.components:
            if comp[0] == 'V':
                results["source_currents"][f"I({comp[1]})"] = round(x[N + v_idx], 6)
                v_idx += 1
                
        return results