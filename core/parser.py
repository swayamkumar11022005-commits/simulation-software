import re
from core.solver import Circuit

def parse_spice_value(val_str):
    """Converts a SPICE value string like '10k' or '5m' to a float."""
    # SPICE Multiplier Dictionary (uppercase)
    multipliers = {
        'T': 1e12, 'G': 1e9, 'MEG': 1e6, 'K': 1e3,
        'M': 1e-3, 'U': 1e-6, 'N': 1e-9, 'P': 1e-12, 'F': 1e-15
    }
    
    # Regex to separate the numeric part from the letter suffix
    match = re.match(r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)([a-zA-Z]*)", val_str)
    if not match:
        raise ValueError(f"Cannot parse value: {val_str}")
        
    num = float(match.group(1))
    unit = match.group(2)
    
    if unit:
        # Check for 'MEG' first, otherwise grab the first letter
        mult = 'MEG' if unit.startswith('MEG') else unit[0]
        if mult in multipliers:
            num *= multipliers[mult]
            
    return num

class NetlistParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.circuit = Circuit()

    def parse(self):
        try:
            with open(self.filepath, 'r') as file:
                lines = file.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"Error: Could not find netlist at {self.filepath}")

        for line in lines:
            line = line.strip().upper()
            if not line or line.startswith('*'):
                continue

            tokens = line.split()
            # We need at least 3 tokens (Name, Node1, Node2)
            if len(tokens) >= 3:
                name, n1, n2 = tokens[0], tokens[1], tokens[2]

                # Diodes don't need a value string in our simple SPICE format
                if name.startswith('D'):
                    self.circuit.add_diode(name, n1, n2)
                    continue # Skip the value parsing below

                # For R, V, and I, we MUST have a 4th token (the value)
                if len(tokens) >= 4:
                    val_str = tokens[3]
                    try:
                        value = parse_spice_value(val_str)
                    except ValueError:
                        print(f"Warning: Could not parse value for {name}. Skipping.")
                        continue

                    if name.startswith('R'):
                        self.circuit.add_resistor(name, n1, n2, value)
                    elif name.startswith('V'):
                        self.circuit.add_v_source(name, n1, n2, value)
                    elif name.startswith('I'):
                        self.circuit.add_i_source(name, n1, n2, value)
                    else:
                        print(f"Warning: Unsupported device '{name}'. Skipping.")
        return self.circuit