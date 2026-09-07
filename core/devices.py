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