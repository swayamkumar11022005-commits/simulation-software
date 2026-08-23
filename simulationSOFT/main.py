from core.solver import Circuit

def test_two_loop_circuit():
    circuit = Circuit()
        
    """
    ex 1:
        circuit.add_v_source('V1', '1', '0', 12.0)  
        circuit.add_resistor('R1', '1', '2', 4.0)   
        circuit.add_resistor('R2', '2', '0', 8.0)  
    """
    
    """
    ex 2:
    """
    #voltage
    circuit.add_v_source('V1', '1', '0', 15.0)  
    circuit.add_v_source('V2', '3', '0', 10.0)  
    
    #resistors
    circuit.add_resistor('R1', '1', '2', 10.0)  # Top resistor, left loop
    circuit.add_resistor('R2', '2', '0', 5.0)   # Shared middle resistor to ground
    circuit.add_resistor('R3', '2', '3', 2.0)   # Top resistor, right loop

    print("Solving circuit...")
    
    try:
        results = circuit.solve()
    except ValueError as e:
        print(f"Simulation failed: {e}")
        return

    print("\n--- Node Voltages ---")
    for node, voltage in results["node_voltages"].items():
        print(f"{node}: {voltage} V")

    print("\n--- Source Currents ---")
    for source, current in results["source_currents"].items():
        print(f"{source}: {current} A")

if __name__ == "__main__":
    test_two_loop_circuit()