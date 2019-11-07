import numpy as np


def monte_carlo_results(m):
    try:
        sol = m.localsolve(verbosity=0)
        #print("fuel consumption: %i lbs" % sol("W_f").to("lbf").magnitude)
    except Exception:
        return (None,None)
    else:
        N = 29
        failures = 0
        for var in m.varkeys:
            if var.fix:
                m.substitutions[var] = sol["variables"][var]
            if var.margin:
                m.substitutions[var] = 1
        for val in np.linspace(1e-5, 4e-5, N):
            m.substitutions["W_W_coeff1"] = val
            try:
                m.localsolve(verbosity=0, x0=sol["variables"])
            except Exception:
                failures += 1
        #print("    failure rate: % 2.1f%% " % (100*failures/float(N)))
        return (sol("W_f").to("lbf").magnitude, 100*failures/float(N))
