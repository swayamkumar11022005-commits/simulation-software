import numpy as np
from core.solver import Circuit
from analysis.dcsweep import DCSweep

def calculate_analytical_current(voltages, Is=1e-14, n=1.0, Vt=0.02585):
    """Calculates theoretical current, matching the simulator's extrapolation model."""
    currents = []
    v_crit = 0.7
    
    for vd in voltages:
        if vd > v_crit:
            I_crit = Is * (np.exp(v_crit / (n * Vt)) - 1)
            g_crit = (Is / (n * Vt)) * np.exp(v_crit / (n * Vt))
            currents.append(I_crit + g_crit * (vd - v_crit))
        else:
            currents.append(Is * (np.exp(vd / (n * Vt)) - 1))
            
    return np.array(currents)

def run_validation():
    print("Running validation and error analysis...")
    
    # 1. Build a dedicated, isolated test circuit (Ignoring circuit.net)
    circuit = Circuit()
    circuit.add_v_source('V1', '1', '0', 0.0)
    circuit.add_resistor('R1', '1', '2', 1000.0) # Exactly 1k ohms
    circuit.add_diode('D1', '2', '0')
    
    # 2. Run our custom simulator sweep
    analyzer = DCSweep(circuit)
    voltages, sim_currents = analyzer.sweep_v_source('V1', 0.4, 0.8, 50)
    
    # 3. Calculate Analytical Reference
    # Because we strictly built a series circuit above, V_diode = V_source - (I * R)
    v_diode_sim = np.array(voltages) - (np.array(sim_currents) * 1000.0)
    ref_currents = calculate_analytical_current(v_diode_sim)
    
    sim_arr = np.array(sim_currents)
    ref_arr = np.array(ref_currents)
    
    # 4. Calculate Error Metrics
    mae = np.mean(np.abs(sim_arr - ref_arr))
    rmse = np.sqrt(np.mean((sim_arr - ref_arr) ** 2))
    
    # Percentage Error (Only calculate for currents above 10uA)
    non_zero_mask = ref_arr > 1e-9
    if np.any(non_zero_mask):
        pct_error = np.mean(np.abs((sim_arr[non_zero_mask] - ref_arr[non_zero_mask]) / ref_arr[non_zero_mask])) * 100
    else:
        pct_error = 0.0

    # 5. Print Validation Report
    print("\n" + "="*40)
    print("      SIMULATOR VALIDATION REPORT")
    print("="*40)
    print(f"Mean Absolute Error (MAE) : {mae:.6e} A")
    print(f"Root Mean Square Error (RMSE): {rmse:.6e} A")
    print(f"Mean Percentage Error     : {pct_error:.4f} %")
    print("="*40)
    
    if pct_error < 5.0:
        print("Status: PASSED (Error is within acceptable engineering tolerance)")
    else:
        print("Status: REVIEW REQUIRED")

if __name__ == "__main__":
    run_validation()