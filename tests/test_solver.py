import numpy as np
from core.parser import NetlistParser
from analysis.dcsweep import DCSweep

def calculate_analytical_current(voltages, Is=1e-14, n=1.0, Vt=0.02585):
    """Calculates pure theoretical diode current using the Shockley equation."""
    return Is * (np.exp(voltages / (n * Vt)) - 1)

def run_validation():
    print("Running validation and error analysis...")
    
    # 1. Run our custom simulator sweep
    parser = NetlistParser("circuit.net")
    circuit = parser.parse()
    analyzer = DCSweep(circuit)
    
    # Sweep from 0.4V to 0.8V where the diode behavior is prominent
    voltages, sim_currents = analyzer.sweep_v_source('V1', 0.4, 0.8, 50)
    ref_currents = calculate_analytical_current(np.array(voltages) - (np.array(sim_currents) * 1000))
    
    sim_arr = np.array(sim_currents)
    ref_arr = np.array(ref_currents)
    
    # 2. Calculate Error Metrics
    # Mean Absolute Error (MAE)
    mae = np.mean(np.abs(sim_arr - ref_arr))
    
    # Root Mean Square Error (RMSE)
    rmse = np.sqrt(np.mean((sim_arr - ref_arr) ** 2))
    
    # Percentage Error (avoiding division by zero by filtering tiny values)
    non_zero_mask = ref_arr > 1e-9
    if np.any(non_zero_mask):
        pct_error = np.mean(np.abs((sim_arr[non_zero_mask] - ref_arr[non_zero_mask]) / ref_arr[non_zero_mask])) * 100
    else:
        pct_error = 0.0

    # 3. Print Validation Report
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