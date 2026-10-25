import numpy as np
from core.devices import Diode, BSIM4Mosfet

class Circuit:
    def __init__(self):
        self.components = []
        self.diodes = []
        self.mosfets = []
        self.capacitors = []
        self.inductors = []
        self.nodes = set()
        self.node_map = {}
        self.v_source_count = 0
        self.models = {}

    def add_model(self, model_name, mtype, params):
        self.models[model_name.upper()] = (mtype.upper(), params)

    def add_resistor(self, name, n1, n2, value):
        self.components.append(('R', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])

    def add_v_source(self, name, n1, n2, dc_val=0.0, ac_mag=0.0, ac_phase=0.0, wave_type='DC', wave_amp=0.0, wave_freq=0.0):
        self.components.append(('V', name, str(n1), str(n2), float(dc_val), float(ac_mag), float(ac_phase), wave_type, float(wave_amp), float(wave_freq)))
        self.nodes.update([str(n1), str(n2)])
        self.v_source_count += 1

    def add_i_source(self, name, n1, n2, dc_val=0.0, ac_mag=0.0, ac_phase=0.0, wave_type='DC', wave_amp=0.0, wave_freq=0.0):
        self.components.append(('I', name, str(n1), str(n2), float(dc_val), float(ac_mag), float(ac_phase), wave_type, float(wave_amp), float(wave_freq)))
        self.nodes.update([str(n1), str(n2)])

    def add_diode(self, name, n1, n2, Is=1e-14, n=1.0):
        self.diodes.append(Diode(name, n1, n2, Is, n))
        self.nodes.update([str(n1), str(n2)])

    def add_mosfet(self, name, d, g, s, b, model_name='NMOS', **instance_params):
        mtype, model_params = self.models.get(model_name.upper(), (model_name.upper(), {}))
        merged_params = {**model_params, **instance_params}
        mos = BSIM4Mosfet(name, d, g, s, b, mtype=mtype, **merged_params)
        self.mosfets.append(mos)
        self.nodes.update([str(d), str(g), str(s), str(b)])

    def add_capacitor(self, name, n1, n2, value):
        self.capacitors.append(('C', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])

    def add_inductor(self, name, n1, n2, value):
        self.inductors.append(('L', name, str(n1), str(n2), float(value)))
        self.nodes.update([str(n1), str(n2)])

    def _map_nodes(self):
        active_nodes = sorted(list(self.nodes - {'0'}))
        self.node_map = {node: i for i, node in enumerate(active_nodes)}
        self.node_map['0'] = -1

    def solve(self, max_iter=200, tol=1e-6, dt=None, x_prev=None, return_raw=False, t=0.0):
        self._map_nodes()
        N = len(self.node_map) - 1
        M = self.v_source_count + len(self.inductors)

        A_lin = np.zeros((N + M, N + M))
        z_lin = np.zeros(N + M)

        # --- 1. Stamp Linear Components (R, V, I) ---
        v_idx = 0
        for comp in self.components:
            comp_type, name, n1, n2 = comp[0], comp[1], comp[2], comp[3]
            val = comp[4]
            idx1 = self.node_map.get(n1, -1)
            idx2 = self.node_map.get(n2, -1)

            # Check for SINE wave during transient analysis
            if len(comp) > 7 and comp[7] == 'SINE' and dt is not None:
                amp, freq = comp[8], comp[9]
                val = amp * np.sin(2.0 * np.pi * freq * t)

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
                    A_lin[idx1, row] += 1.0
                    A_lin[row, idx1] += 1.0
                if idx2 != -1:
                    A_lin[idx2, row] -= 1.0
                    A_lin[row, idx2] -= 1.0
                z_lin[row] = val
                v_idx += 1

            elif comp_type == 'I':
                if idx1 != -1: z_lin[idx1] -= val
                if idx2 != -1: z_lin[idx2] += val

        # --- 2. Stamp Inductors (DC Short / Transient Backward Euler) ---
        l_idx = 0
        for comp in self.inductors:
            _, name, n1, n2, L = comp
            idx1 = self.node_map.get(n1, -1)
            idx2 = self.node_map.get(n2, -1)
            row = N + self.v_source_count + l_idx

            if idx1 != -1:
                A_lin[idx1, row] += 1.0
                A_lin[row, idx1] += 1.0
            if idx2 != -1:
                A_lin[idx2, row] -= 1.0
                A_lin[row, idx2] -= 1.0

            if dt is not None and x_prev is not None:
                req = L / dt
                A_lin[row, row] -= req
                z_lin[row] = -req * x_prev[row]

            l_idx += 1

        # --- 3. Stamp Capacitors (Transient Backward Euler) ---
        if dt is not None and x_prev is not None:
            for comp in self.capacitors:
                _, name, n1, n2, C = comp
                idx1 = self.node_map.get(n1, -1)
                idx2 = self.node_map.get(n2, -1)
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

        # --- 4. Newton-Raphson Iterative Loop for Non-Linear Devices ---
        x = np.copy(x_prev) if x_prev is not None else np.zeros(N + M)

        for iteration in range(max_iter):
            # A and z are initialized HERE inside the loop!
            A = np.copy(A_lin)
            z = np.copy(z_lin)

            # Stamp Diodes
            for diode in self.diodes:
                idx1 = self.node_map.get(diode.n1, -1)
                idx2 = self.node_map.get(diode.n2, -1)

                v1 = x[idx1] if idx1 != -1 else 0.0
                v2 = x[idx2] if idx2 != -1 else 0.0
                vd = v1 - v2

                id_curr = diode.get_current(vd)
                gd = diode.get_conductance(vd)
                ieq = id_curr - gd * vd

                if idx1 != -1:
                    A[idx1, idx1] += gd
                    z[idx1] -= ieq
                if idx2 != -1:
                    A[idx2, idx2] += gd
                    z[idx2] += ieq
                if idx1 != -1 and idx2 != -1:
                    A[idx1, idx2] -= gd
                    A[idx2, idx1] -= gd

            # Stamp BSIM4 MOSFETs (b4ld.c Jacobian Stamping)
            for mos in self.mosfets:
                id_d = self.node_map.get(mos.d, -1)
                id_g = self.node_map.get(mos.g, -1)
                id_s = self.node_map.get(mos.s, -1)
                id_b = self.node_map.get(mos.b, -1)

                vd = x[id_d] if id_d != -1 else 0.0
                vg = x[id_g] if id_g != -1 else 0.0
                vs = x[id_s] if id_s != -1 else 0.0
                vb = x[id_b] if id_b != -1 else 0.0

                state = mos.evaluate(vd, vg, vs, vb)
                gm, gds, gmbs, Ieq = state["gm"], state["gds"], state["gmbs"], state["Ieq"]

                # Stamp Drain row (id_d)
                if id_d != -1:
                    A[id_d, id_d] += gds
                    if id_g != -1: A[id_d, id_g] += gm
                    if id_b != -1: A[id_d, id_b] += gmbs
                    if id_s != -1: A[id_d, id_s] -= (gds + gm + gmbs)
                    z[id_d] -= Ieq

                # Stamp Source row (id_s)
                if id_s != -1:
                    A[id_s, id_s] += (gds + gm + gmbs)
                    if id_d != -1: A[id_s, id_d] -= gds
                    if id_g != -1: A[id_s, id_g] -= gm
                    if id_b != -1: A[id_s, id_b] -= gmbs
                    z[id_s] += Ieq

            # Solve Linearized System
            try:
                x_new = np.linalg.solve(A, z)
            except np.linalg.LinAlgError:
                raise ValueError("Singular matrix encountered.")

            # Check Convergence
            max_diff = np.max(np.abs(x_new - x))
            if max_diff < tol:
                if return_raw:
                    return x_new
                return self._format_results(x_new, N)

            # Voltage step limiting (SPICE-style pnjlim/fetlim damping)
            delta_x = x_new - x
            if self.diodes or self.mosfets:
                max_step = 0.25  # Limit maximum voltage jump to 0.25V per iteration
                if max_diff > max_step:
                    delta_x = delta_x * (max_step / max_diff)
            x = x + delta_x

        raise ValueError(f"Failed to converge after {max_iter} iterations.")
    
    def solve_ac(self, freq, dc_op):
        self._map_nodes()
        N = len(self.node_map) - 1
        M = self.v_source_count + len(self.inductors)

        A_ac = np.zeros((N + M, N + M), dtype=np.complex128)
        z_ac = np.zeros(N + M, dtype=np.complex128)
        omega = 2.0 * np.pi * freq

        v_idx = 0
        for comp in self.components:
            comp_type, name, n1, n2 = comp[0], comp[1], comp[2], comp[3]
            val = comp[4]
            ac_mag = comp[5] if len(comp) > 5 else 0.0
            ac_phase = comp[6] if len(comp) > 6 else 0.0
            idx1, idx2 = self.node_map.get(n1, -1), self.node_map.get(n2, -1)

            if comp_type == 'R':
                g = 1.0 / val
                if idx1 != -1: A_ac[idx1, idx1] += g
                if idx2 != -1: A_ac[idx2, idx2] += g
                if idx1 != -1 and idx2 != -1:
                    A_ac[idx1, idx2] -= g
                    A_ac[idx2, idx1] -= g
            elif comp_type == 'V':
                row = N + v_idx
                if idx1 != -1:
                    A_ac[idx1, row] += 1.0
                    A_ac[row, idx1] += 1.0
                if idx2 != -1:
                    A_ac[idx2, row] -= 1.0
                    A_ac[row, idx2] -= 1.0
                rad = np.deg2rad(ac_phase)
                z_ac[row] = ac_mag * (np.cos(rad) + 1j * np.sin(rad))
                v_idx += 1
            elif comp_type == 'I':
                rad = np.deg2rad(ac_phase)
                i_phasor = ac_mag * (np.cos(rad) + 1j * np.sin(rad))
                if idx1 != -1: z_ac[idx1] -= i_phasor
                if idx2 != -1: z_ac[idx2] += i_phasor

        for comp in self.capacitors:
            _, name, n1, n2, C = comp
            idx1, idx2 = self.node_map.get(n1, -1), self.node_map.get(n2, -1)
            Yc = 1j * omega * C
            if idx1 != -1: A_ac[idx1, idx1] += Yc
            if idx2 != -1: A_ac[idx2, idx2] += Yc
            if idx1 != -1 and idx2 != -1:
                A_ac[idx1, idx2] -= Yc
                A_ac[idx2, idx1] -= Yc

        l_idx = 0
        for comp in self.inductors:
            _, name, n1, n2, L = comp
            idx1, idx2 = self.node_map.get(n1, -1), self.node_map.get(n2, -1)
            row = N + self.v_source_count + l_idx
            if idx1 != -1:
                A_ac[idx1, row] += 1.0
                A_ac[row, idx1] += 1.0
            if idx2 != -1:
                A_ac[idx2, row] -= 1.0
                A_ac[row, idx2] -= 1.0
            A_ac[row, row] -= 1j * omega * L
            l_idx += 1

        for diode in self.diodes:
            idx1, idx2 = self.node_map.get(diode.n1, -1), self.node_map.get(diode.n2, -1)
            v1_dc = dc_op["node_voltages"].get(f"V({diode.n1})", 0.0) if idx1 != -1 else 0.0
            v2_dc = dc_op["node_voltages"].get(f"V({diode.n2})", 0.0) if idx2 != -1 else 0.0
            gd = diode.get_conductance(v1_dc - v2_dc)
            if idx1 != -1: A_ac[idx1, idx1] += gd
            if idx2 != -1: A_ac[idx2, idx2] += gd
            if idx1 != -1 and idx2 != -1:
                A_ac[idx1, idx2] -= gd
                A_ac[idx2, idx1] -= gd

        # Small-Signal BSIM4 MOSFETs (b4acld.c)
        for mos in self.mosfets:
            id_d = self.node_map.get(mos.d, -1)
            id_g = self.node_map.get(mos.g, -1)
            id_s = self.node_map.get(mos.s, -1)
            id_b = self.node_map.get(mos.b, -1)

            vd = dc_op["node_voltages"].get(f"V({mos.d})", 0.0) if id_d != -1 else 0.0
            vg = dc_op["node_voltages"].get(f"V({mos.g})", 0.0) if id_g != -1 else 0.0
            vs = dc_op["node_voltages"].get(f"V({mos.s})", 0.0) if id_s != -1 else 0.0
            vb = dc_op["node_voltages"].get(f"V({mos.b})", 0.0) if id_b != -1 else 0.0

            state = mos.evaluate(vd, vg, vs, vb)
            gm, gds, gmbs, cgg = state["gm"], state["gds"], state["gmbs"], state["cgg"]
            ycgg = 1j * omega * cgg

            if id_g != -1: A_ac[id_g, id_g] += ycgg
            if id_s != -1: A_ac[id_s, id_s] += ycgg
            if id_g != -1 and id_s != -1:
                A_ac[id_g, id_s] -= ycgg
                A_ac[id_s, id_g] -= ycgg

            if id_d != -1:
                A_ac[id_d, id_d] += gds
                if id_g != -1: A_ac[id_d, id_g] += gm
                if id_b != -1: A_ac[id_d, id_b] += gmbs
                if id_s != -1: A_ac[id_d, id_s] -= (gds + gm + gmbs)
            if id_s != -1:
                A_ac[id_s, id_s] += (gds + gm + gmbs)
                if id_d != -1: A_ac[id_s, id_d] -= gds
                if id_g != -1: A_ac[id_s, id_g] -= gm
                if id_b != -1: A_ac[id_s, id_b] -= gmbs

        try:
            x_ac = np.linalg.solve(A_ac, z_ac)
            return self._format_results_ac(x_ac, N)
        except np.linalg.LinAlgError:
            raise ValueError("Singular complex matrix encountered.")

    def _format_results(self, x, N):
        results = {"node_voltages": {}, "source_currents": {}}
        for node, idx in self.node_map.items():
            if node != '0':
                results["node_voltages"][f"V({node})"] = round(float(x[idx]), 6)

        v_idx = 0
        for comp in self.components:
            if comp[0] == 'V':
                results["source_currents"][f"I({comp[1]})"] = round(float(x[N + v_idx]), 6)
                v_idx += 1

        l_idx = 0
        for comp in self.inductors:
            results["source_currents"][f"I({comp[1]})"] = round(float(x[N + self.v_source_count + l_idx]), 6)
            l_idx += 1

        return results

    def _format_results_ac(self, x, N):
        results = {"node_voltages": {}}
        for node, idx in self.node_map.items():
            if node != '0':
                results["node_voltages"][f"V({node})"] = x[idx]
        return results