import numpy as np

class Circuit:
    def __init__(self):
        self.components = []
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

    def solve(self):
        """Constructs the MNA matrix and solves for voltages and currents."""
        self._map_nodes()
        N = len(self.node_map) - 1 # Number of active nodes (excluding ground)
        M = self.v_source_count    # Number of independent voltage sources
        
        # Initialize MNA matrix A and known vector z (Ax = z)
        A = np.zeros((N + M, N + M))
        z = np.zeros(N + M)
        
        v_idx = 0 # Counter for tracking voltage source rows
        
        for comp in self.components:
            comp_type, name, n1, n2, val = comp
            idx1 = self.node_map[n1]
            idx2 = self.node_map[n2]
            
            if comp_type == 'R':
                g = 1.0 / val
                if idx1 != -1:
                    A[idx1, idx1] += g
                if idx2 != -1:
                    A[idx2, idx2] += g
                if idx1 != -1 and idx2 != -1:
                    A[idx1, idx2] -= g
                    A[idx2, idx1] -= g
                    
            elif comp_type == 'V':
                row = N + v_idx
                if idx1 != -1:
                    A[idx1, row] += 1
                    A[row, idx1] += 1
                if idx2 != -1:
                    A[idx2, row] -= 1
                    A[row, idx2] -= 1
                z[row] = val
                v_idx += 1
                
            elif comp_type == 'I':
                # Current leaves n1, enters n2
                if idx1 != -1:
                    z[idx1] -= val 
                if idx2 != -1:
                    z[idx2] += val

        # Solve the linear system (Update this part at the bottom of solver.py)
        try:
            x = np.linalg.solve(A, z)
            return self._format_results(x, N)
        except np.linalg.LinAlgError:
            # Raise an actual error instead of returning a mixed dictionary
            raise ValueError("Singular matrix. Check for floating nodes or shorted voltage sources.")
        
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