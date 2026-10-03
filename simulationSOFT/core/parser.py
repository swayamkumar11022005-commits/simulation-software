import re
from core.solver import Circuit

def parse_spice_value(val_str):
    multipliers = {
        'T': 1e12, 'G': 1e9, 'MEG': 1e6, 'K': 1e3,
        'M': 1e-3, 'U': 1e-6, 'N': 1e-9, 'P': 1e-12, 'F': 1e-15
    }
    match = re.match(r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)([a-zA-Z]*)", val_str)
    if not match:
        raise ValueError(f"Cannot parse value: {val_str}")
        
    num = float(match.group(1))
    unit = match.group(2)
    
    if unit:
        mult = 'MEG' if unit.startswith('MEG') else unit[0]
        if mult in multipliers:
            num *= multipliers[mult]
            
    return num

class NetlistParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.circuit: Circuit = Circuit()

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
            if len(tokens) >= 3:
                name, n1, n2 = tokens[0], tokens[1], tokens[2]

                if name.startswith('D'):
                    self.circuit.add_diode(name, n1, n2)
                    continue 

                # For R, V, C, L, and I, we MUST have a 4th token
                if len(tokens) >= 4:
                    dc_val, ac_mag, ac_phase = 0.0, 0.0, 0.0
                    wave_type, wave_amp, wave_freq = 'DC', 0.0, 0.0
                    
                    try:
                        # Intercept AC or SINE keywords before parsing a DC value
                        if 'AC' in tokens:
                            ac_idx = tokens.index('AC')
                            ac_mag = parse_spice_value(tokens[ac_idx + 1]) if len(tokens) > ac_idx + 1 else 0.0
                            ac_phase = float(tokens[ac_idx + 2]) if len(tokens) > ac_idx + 2 else 0.0
                        elif 'SINE' in tokens:
                            sine_idx = tokens.index('SINE')
                            wave_type = 'SINE'
                            wave_amp = parse_spice_value(tokens[sine_idx + 1]) if len(tokens) > sine_idx + 1 else 0.0
                            wave_freq = parse_spice_value(tokens[sine_idx + 2]) if len(tokens) > sine_idx + 2 else 0.0
                        else:
                            dc_val = parse_spice_value(tokens[3])
                    except ValueError:
                        print(f"Warning: Could not parse parameters for {name}. Skipping.")
                        continue

                    if name.startswith('R'):
                        self.circuit.add_resistor(name, n1, n2, dc_val)
                    elif name.startswith('C'):
                        self.circuit.add_capacitor(name, n1, n2, dc_val)
                    elif name.startswith('L'):
                        self.circuit.add_inductor(name, n1, n2, dc_val)
                    elif name.startswith('V'):
                        self.circuit.add_v_source(name, n1, n2, dc_val, ac_mag, ac_phase, wave_type, wave_amp, wave_freq)
                    elif name.startswith('I'):
                        self.circuit.add_i_source(name, n1, n2, dc_val, ac_mag, ac_phase, wave_type, wave_amp, wave_freq)
                    else:
                        print(f"Warning: Unsupported device '{name}'. Skipping.")
        return self.circuit

    def determine_analysis_type(self):
        has_ac = False
        has_sine = False
        has_reactive = len(self.circuit.capacitors) > 0 or len(getattr(self.circuit, 'inductors', [])) > 0

        # Scan all components for specific source parameters
        for comp in self.circuit.components:
            # Index 5 is AC Magnitude
            if (comp[0] == 'V' or comp[0] == 'I') and len(comp) > 5 and comp[5] > 0.0:
                has_ac = True
            # Index 7 is Wave Type
            if len(comp) > 7 and comp[7] == 'SINE':
                has_sine = True

        # Route based on topology combinations
        if has_sine:
            return "ac_transient"
        elif has_ac:
            return "ac_sweep"
        elif has_reactive:
            return "dc_transient"
        else:
            return "dc_sweep"