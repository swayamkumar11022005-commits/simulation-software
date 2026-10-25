import numpy as np

class Diode:
    def __init__(self, name, n1, n2, Is=1e-14, n=1.0, Vt=0.02585):
        self.name = name
        self.n1 = str(n1)
        self.n2 = str(n2)
        self.Is = Is
        self.n = n
        self.Vt = Vt
        self.v_crit = 0.7  # Critical voltage for extrapolation

    def get_current(self, vd):
        """Calculates diode current. Uses linear extrapolation above 0.7V to prevent overflow."""
        if vd > self.v_crit:
            # Calculate current and slope at 0.7V, then draw a straight line
            I_crit = self.Is * (np.exp(self.v_crit / (self.n * self.Vt)) - 1)
            g_crit = (self.Is / (self.n * self.Vt)) * np.exp(self.v_crit / (self.n * self.Vt))
            return I_crit + g_crit * (vd - self.v_crit)
        else:
            # Standard Shockley equation
            return self.Is * (np.exp(vd / (self.n * self.Vt)) - 1)

    def get_conductance(self, vd):
        """Calculates dynamic conductance (derivative)."""
        if vd > self.v_crit:
            # Constant slope above 0.7V
            return (self.Is / (self.n * self.Vt)) * np.exp(self.v_crit / (self.n * self.Vt))
        else:
            return (self.Is / (self.n * self.Vt)) * np.exp(vd / (self.n * self.Vt))
        
class BSIM4Mosfet:
    """
    BSIM4.8.3 4-Terminal MOSFET Model (Drain, Gate, Source, Bulk)
    Implements parameter binning, temperature setup (b4temp.c), 
    and Jacobian evaluation/stamping (b4ld.c).
    """
    def __init__(self, name, d, g, s, b, mtype='NMOS', **kwargs):
        self.name = name
        self.d = str(d)
        self.g = str(g)
        self.s = str(s)
        self.b = str(b)
        self.type_sign = 1.0 if mtype.upper() == 'NMOS' else -1.0
        self.version = kwargs.get('version', 4.83)

        # Instance Parameters & BSIM4.8.3 Multipliers (b4set.c)
        self.W = float(kwargs.get('w', 1.2e-6))
        self.L = float(kwargs.get('l', 1.0e-6))
        self.mult_i = float(kwargs.get('mult_i', 1.0))
        self.mult_q = float(kwargs.get('mult_q', 1.0))
        self.mult_fn = float(kwargs.get('mult_fn', self.mult_i))

        # Geometry offset parameters (Default = 0.0 per 2024bug2)
        self.WINT = float(kwargs.get('wint', 0.0))
        self.LINT = float(kwargs.get('lint', 0.0))
        self.WL, self.WLN = float(kwargs.get('wl', 0.0)), float(kwargs.get('wln', 1.0))
        self.WW, self.WWN = float(kwargs.get('ww', 0.0)), float(kwargs.get('wwn', 1.0))
        self.WWL = float(kwargs.get('wwl', 0.0))
        self.LL, self.LLN = float(kwargs.get('ll', 0.0)), float(kwargs.get('lln', 1.0))
        self.LW, self.LWN = float(kwargs.get('lw', 0.0)), float(kwargs.get('lwn', 1.0))
        self.LWL = float(kwargs.get('lwl', 0.0))

        # Oxide & Material Parameters (b4temp.c)
        self.mtrlMod = int(kwargs.get('mtrlmod', 0))
        self.toxe = float(kwargs.get('toxe', 3.0e-9))
        self.toxp = float(kwargs.get('toxp', self.toxe))
        self.dtox = float(kwargs.get('dtox', 0.0))
        self.epsrox = float(kwargs.get('epsrox', 3.9))
        self.cf = kwargs.get('cf', None)

        # Base Process & Binnable Parameters (Note-11)
        self.vth0 = float(kwargs.get('vth0', 0.45 * self.type_sign))
        self.lvth0, self.wvth0, self.pvth0 = float(kwargs.get('lvth0', 0.0)), float(kwargs.get('wvth0', 0.0)), float(kwargs.get('pvth0', 0.0))

        self.keta = float(kwargs.get('keta', -0.047))
        self.lketa, self.wketa, self.pketa = float(kwargs.get('lketa', 0.0)), float(kwargs.get('wketa', 0.0)), float(kwargs.get('pketa', 0.0))

        # 2024bug1 Backward Compatibility: ketac defaults to keta
        self.ketac = float(kwargs.get('ketac', self.keta))
        self.lketac = float(kwargs.get('lketac', self.lketa))
        self.wketac = float(kwargs.get('wketac', self.wketa))
        self.pketac = float(kwargs.get('pketac', self.pketa))

        # Mobility & Channel Parameters
        self.mobMod = int(kwargs.get('mobmod', 3))
        self.u0 = float(kwargs.get('u0', 0.045 if self.type_sign > 0 else 0.02))
        self.ua = float(kwargs.get('ua', 1.0e-9))
        self.uc = float(kwargs.get('uc', -0.0465e-9))
        self.ud = float(kwargs.get('ud', 1.0e-2))
        self.ucs = float(kwargs.get('ucs', 1.0))
        self.eu = float(kwargs.get('eu', 1.67 if self.type_sign > 0 else 1.0))
        
        self.ndep = float(kwargs.get('ndep', 1.7e17))
        self.phin = float(kwargs.get('phin', 0.0))
        self.vfb = float(kwargs.get('vfb', -0.9))
        self.k1ox = float(kwargs.get('k1ox', 0.53))
        self.k2ox = float(kwargs.get('k2ox', -0.0186))
        self.a0 = float(kwargs.get('a0', 1.0))
        self.ags = float(kwargs.get('ags', 0.0))
        self.b0, self.b1 = float(kwargs.get('b0', 0.0)), float(kwargs.get('b1', 0.0))
        self.xj = float(kwargs.get('xj', 1.5e-7))
        self.pclm = float(kwargs.get('pclm', 0.06)) # Channel length modulation
        self.tnom = float(kwargs.get('tnom', 300.15))
        self.gmin = 1e-12

        self._b4temp_setup()

    def _bin_param(self, M, LM, WM, PM):
        """Implements Note-11 binnable parameter equation."""
        return M + (LM / self.Leff) + (WM / self.Weff) + (PM / (self.Leff * self.Weff))

    def _b4temp_setup(self):
        """Replicates b4temp.c initialization and checks."""
        EPS0 = 8.854187817e-12
        q = 1.60219e-19
        kB = 1.38065e-23

        # 1. Effective Geometry (Section 1.3 Eq 1.12)
        dW_prime = self.WINT + self.WL / (self.L ** self.WLN) + self.WW / (self.W ** self.WWN) + self.WWL / ((self.L ** self.WLN) * (self.W ** self.WWN))
        dL = self.LINT + self.LL / (self.L ** self.LLN) + self.LW / (self.W ** self.LWN) + self.LWL / ((self.L ** self.LLN) * (self.W ** self.LWN))
        self.Weff = max(self.W - 2.0 * dW_prime, 1e-9)
        self.Leff = max(self.L - 2.0 * dL, 1e-9)

        # 2. Updated TOXE & CF calculation (2019enh3)
        self.Coxe = (self.epsrox * EPS0) / self.toxe
        if self.cf is None:
            self.cf = (2.0 * self.epsrox * EPS0 / np.pi) * np.log(1.0 + 0.4e-6 / self.toxe)

        # 3. U0 Protection (2021enh1: multiply by 1e-4 if U0 > 1)
        if self.u0 > 1.0:
            self.u0 *= 1.0e-4

        # 4. Intrinsic Carrier Concentration (2021enh3 equation fix)
        self.Vtm0 = (kB * self.tnom) / q
        Eg = 1.16 - (7.02e-4 * (self.tnom ** 2)) / (self.tnom + 1108.0)
        self.ni = 1.45e10 * (self.tnom / 300.15) * np.sqrt(self.tnom / 300.15) * np.exp(21.5565981 - (q * Eg) / (2.0 * kB * self.tnom))

        # 5. Surface Potential Phi Check (2021enh2)
        self.phi = self.Vtm0 * np.log(self.ndep / self.ni) + self.phin + 0.4
        if self.phi <= 0.0:
            raise ValueError(f"Fatal: Phi ({self.phi}) is not positive in {self.name}. Check Phin and Ndep.")
        self.sqrtPhi = np.sqrt(self.phi)

        # 6. Binnable Parameters Evaluation
        self.vth0_binned = self._bin_param(self.vth0, self.lvth0, self.wvth0, self.pvth0)
        self.keta_binned = self._bin_param(self.keta, self.lketa, self.wketa, self.pketa)
        self.ketac_binned = self._bin_param(self.ketac, self.lketac, self.wketac, self.pketac)

    def _evaluate_core(self, vgs, vds, vbs):
        """Core BSIM4 physics for DC/Transient drain current and charges."""
        # Handle NMOS (+1) vs PMOS (-1) polarity
        Vgs = self.type_sign * vgs
        Vds = self.type_sign * vds
        Vbs = self.type_sign * vbs
        Vth0 = abs(self.vth0_binned)

        # Smooth Source-Drain symmetry (avoids derivative discontinuity at Vds = 0)
        eps_vds = 1e-3
        Vds_abs = np.sqrt(Vds * Vds + eps_vds * eps_vds) - eps_vds
        rev_factor = np.tanh(Vds / 0.01)  # Smoothly transitions between -1 and +1

        # Smooth Vbseff clamping
        Vbseff = min(Vbs, 0.95 * self.phi)
        sqrtPhis = np.sqrt(max(self.phi - Vbseff, 1e-3))
        Xdep = np.sqrt(2.0 * 11.7 * 8.854e-12 * max(self.phi - Vbseff, 1e-3) / (1.602e-19 * (self.ndep * 1e6)))

        # Threshold Voltage Vth
        Vth = Vth0 + self.k1ox * (sqrtPhis - self.sqrtPhi) - self.k2ox * Vbseff

        # Smooth Overdrive Voltage Vgsteff (Subthreshold to Strong Inversion continuity)
        n = 1.3
        nVt = n * self.Vtm0
        arg = np.clip((Vgs - Vth) / (2.0 * nVt), -40.0, 40.0)
        Vgsteff = 2.0 * nVt * np.log(1.0 + np.exp(arg))
        Vgsteff_Vth = 2.0 * nVt * np.log(2.0)

        # Abulk & Abulk_Q Calculation (b4ld.c - 2023bug2 & 2024bug1)
        T9 = np.sqrt(self.xj * Xdep)
        tmp1 = self.Leff + 2.0 * T9
        T5 = self.Leff / tmp1
        tmp2 = self.a0 * T5
        tmp3 = self.Weff + self.b1
        tmp4 = self.b0 / tmp3
        T2 = tmp2 + tmp4
        T1 = 0.5 * self.k1ox / sqrtPhis + self.k2ox
        
        Abulk0 = max(1.0 + T1 * T2, 0.1)
        T8 = self.ags * self.a0 * (T5 ** 3)
        Abulk = max(Abulk0 - T1 * T8 * Vgsteff, 0.1)

        # Scale Abulk with keta (DC) and Abulk_Q with ketac (CV)
        T2_dc = self.keta_binned * Vbseff
        T0_dc = 1.0 / (1.0 + T2_dc) if T2_dc >= -0.9 else (17.0 + 20.0 * T2_dc) / (0.8 + T2_dc)
        Abulk_dc = np.clip(Abulk * T0_dc, 0.1, 10.0)

        if self.ketac_binned != self.keta_binned:
            T2_cv = self.ketac_binned * Vbseff
            T0_cv = 1.0 / (1.0 + T2_cv) if T2_cv >= -0.9 else (17.0 + 20.0 * T2_cv) / (0.8 + T2_cv)
            Abulk_Q = np.clip(Abulk * T0_cv, 0.1, 10.0)
        else:
            Abulk_Q = Abulk_dc

        # Mobility Model MOBMOD = 3 (2022enh1 corrected equation)
        C0 = 2.0
        eff_field = max((Vgsteff + C0 * (Vth0 - self.vfb - self.phi)) / (6.0 * self.toxe), 0.0)
        denom_mob = 1.0 + (self.ua + self.uc * Vbseff) * ((eff_field * 1e-8) ** self.eu) + \
                    self.ud / ((0.5 * (1.0 + Vgsteff / Vgsteff_Vth)) ** self.ucs)
        ueff = self.u0 / max(denom_mob, 0.1)

        # Saturation Voltage Vdsat & Smooth Effective Vdseff
        Vdsat = max(Vgsteff / Abulk_dc, 1e-3)
        delta = 0.01
        Vdseff = Vdsat - 0.5 * (Vdsat - Vds_abs - delta + np.sqrt((Vdsat - Vds_abs - delta)**2 + 4.0 * delta * Vdsat))
        Vdseff = max(Vdseff, 0.0)

        # Drain Current Ids (with 2023bug1 guaranteed 0A at Vds=0)
        beta = ueff * self.Coxe * (self.Weff / self.Leff)
        Ids0 = beta * (Vgsteff - 0.5 * Abulk_dc * Vdseff) * Vdseff
        clm = 1.0 + self.pclm * max(Vds_abs - Vdseff, 0.0)
        
        # Apply MULT_I and MULT_Q (2022enh2)
        Ids = self.type_sign * rev_factor * self.mult_i * Ids0 * clm + self.gmin * vds
        Qgate = self.type_sign * self.mult_q * (self.Weff * self.Leff * self.Coxe * Vgsteff / max(1.0 + 0.1 * Abulk_Q, 0.2))
        
        return Ids, Qgate

    def evaluate(self, vd, vg, vs, vb):
        """
        Calculates Drain Current (Ids) and 4-terminal Jacobian conductances 
        (gm, gds, gmbs) for MNA Newton-Raphson stamping.
        """
        # Clamp extreme Newton-Raphson trial guesses to prevent math explosion
        vgs = np.clip(vg - vs, -10.0, 10.0)
        vds = np.clip(vd - vs, -10.0, 10.0)
        vbs = np.clip(vb - vs, -10.0, 10.0)

        Ids, Qgate = self._evaluate_core(vgs, vds, vbs)

        eps = 1e-5
        Ids_vg, Q_vg = self._evaluate_core(vgs + eps, vds, vbs)
        Ids_vd, _    = self._evaluate_core(vgs, vds + eps, vbs)
        Ids_vb, _    = self._evaluate_core(vgs, vds, vbs + eps)

        gm   = (Ids_vg - Ids) / eps
        gds  = max((Ids_vd - Ids) / eps, self.gmin)
        gmbs = (Ids_vb - Ids) / eps
        cgg  = abs((Q_vg - Qgate) / eps)

        # Equivalent Norton Current Source for Newton-Raphson linearization
        Ieq = Ids - (gm * (vg - vs) + gds * (vd - vs) + gmbs * (vb - vs))

        return {
            "Ids": Ids, "gm": gm, "gds": gds, "gmbs": gmbs, 
            "Ieq": Ieq, "cgg": cgg, "Qgate": Qgate
        }