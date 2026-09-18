import os
from core.parser import NetlistParser
from analysis.transient import TransientAnalysis

def run_transient_test():
    # 1. Create a temporary netlist for an RC step response
    # 1k resistor and 1uF capacitor = 1ms Time Constant (tau)

    temp_file = "circuit.net"

    print(f"Reading netlist: {temp_file}...")
    
    # 2. Parse the netlist
    parser = NetlistParser(temp_file)
    circuit = parser.parse()
    
    # 3. Run Transient Analysis
    analyzer = TransientAnalysis(circuit)
    
    try:
        # Simulate for 5 time constants (5ms) with a 0.1ms step size
        results = analyzer.run(t_stop=0.005, t_step=0.0001)
        
        # Plot the input voltage (Node 1) and capacitor voltage (Node 2)
        analyzer.plot(results, plot_nodes=['1', '2'])
        
    except ValueError as e:
        print(f"Simulation failed: {e}")
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    run_transient_test()
    
    
"""

basic capacitor circuit

    Node 1                      Node 2
         +------------[ R1 ]---------+
         |            (1kΩ)          |
         |                           |
        (+) V1                      --- C1
       (5.0V)                       --- (1µF)
        (-)                          |
         |                           |
         +---------------------------+
                                     |
                                    ===  Node 0 (Ground)
                                     -


basic diode ckt

Node 1                      Node 2                      Node 3
         +------------[ R1 ]---------+----------[ R2 ]-----------+
         |            (4kΩ)          |            (1kΩ)          |
         |                           |                           |
        (+) V1                      (^) I1                     _\|/_ D1
       (12V)                        (2mA)                       / \  
        (-)                          |                         -----
         |                           |                           |
         |                           |                           |
         +---------------------------+---------------------------+
                                     |
                                    ===  Node 0 (Ground)
                                     -

"""