from core.solver import Circuit

def test_basic_circuit():
    circuit = Circuit()
    
    circuit.add_v_source('V1', '1', '0', 12.0)  
    circuit.add_resistor('R1', '1', '2', 4.0)   
    circuit.add_resistor('R2', '2', '0', 8.0)   

    print("Solving circuit...")
    
    # Catch the error properly
    try:
        results = circuit.solve()
    except ValueError as e:
        print(f"Simulation failed: {e}")
        return

    # Pylance will no longer complain here!
    print("\n--- Node Voltages ---")
    for node, voltage in results["node_voltages"].items():
        print(f"{node}: {voltage} V")

    print("\n--- Source Currents ---")
    for source, current in results["source_currents"].items():
        print(f"{source}: {current} A")

if __name__ == "__main__":
    test_basic_circuit()