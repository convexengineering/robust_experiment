import numpy as np
import scipy.stats as stats
from gpkit import ureg, NamedVariables
from simpleac import SimPleAC

m = SimPleAC()
N = 100


def monte_carlo_results(m, progress=None, out=None, sol=None, quiet=False, seed=246):
    NamedVariables.reset_modelnumbers()
    np.random.seed(seed=seed)
    monte_up = [{k.name: stats.truncnorm.rvs(-3, 3, loc=1,
                                             scale=(k.key.orig_pr/300.))
                 for k in m.substitutions if k.pr}
                for _ in range(N)]
    try:
        if sol is None:
            sol = m.localsolve(verbosity=0)
        if out:
            with out:
                print("Fuel consumption: %i lbs" % sol("W_f").to("lbf").magnitude)
        elif not quiet:
            print("Fuel consumption: %i lbs" % sol("W_f").to("lbf").magnitude)
    except Exception:
        return (None, None)
    else:
        failures = 0
        for var in m.varkeys:
            if var.fix:
                m.substitutions[var] = sol["variables"][var.name]
            if var.margin:
                m.substitutions[var] = 1
        m.pop()
        for i, subs in enumerate(monte_up):
            m.substitutions.update(subs)
            try:
                # assert not does_it_fail(sol, W_W_coeff1)
                # UNCOMMENT THE ABOVE AND COMMENT OUT THE BELOW TO SPEED UP
                m.solve(verbosity=0)
            except Exception:
                failures += 1
            if progress:
                progress.value = i/N
        if out:
            with out:
                print("    Failure rate: % 2.1f%% " % (100*failures/float(N)))
        elif not quiet:
            print("    Failure rate: % 2.1f%% " % (100*failures/float(N)))
        return (sol("W_f").to("lbf").magnitude, 100*failures/float(N))


def does_it_fail(sol, W_W_coeff1):
    W_W_coeff1 *= ureg("1/m")

    W_W_coeff2 = sol("W_W_coeff2")
    tau = sol("tau")
    N_ult = sol("N_ult")
    W_0 = sol("W_0")
    V_f_fuse = sol("V_f_fuse")
    g = sol("g")
    e = sol("e")
    k = sol("k")
    S_wetratio = sol("S_wetratio")
    rho_f = sol("rho_f")
    rho = sol("rho")
    mu = sol("mu")
    TSFC = sol("TSFC")
    Range = sol("Range")
    C_Lmax = sol("C_Lmax")
    V_min = sol("V_{min}")

    # free variable
    A = sol("A")
    S = sol("S")
    V_f_fuse = sol("V_f_fuse")
    C_L = sol("C_L")

    # iterate
    V_cruisemax = sol("V")
    W = W_orig = sol("W")
    V_cruisemax_prev = W_prev = 0

    # kinda changed
    W_f = sol("W_f")

    while abs((W - W_prev).magnitude) >= 0.1:
        W_w_surf = W_W_coeff2 * S
        W_w_strc = ((W_W_coeff1**2 / tau**2
                     * (N_ult**2 * A**3
                        * ((W_0+V_f_fuse*g*rho_f) * W * S))))**0.5
        W_w = W_w_surf + W_w_strc
        W_prev = W
        W = W_0 + W_w + W_f

    # so the above is for fully-loaded, but,
    # we may not be able to lift off with a full fuel load

    if (0.5 * rho * S * C_Lmax * V_min ** 2 < W - W_f):
        # cannot take off with any fuel!
        return True

    # full or partial fuel
    W_f = min(0.5 * rho * S * C_Lmax * V_min ** 2 - (W-W_f), W_f)

    V_f = W_f / g / rho_f
    V_f_wing = (0.0009*S**3/A*tau**2)**0.5
    V_f_avail = V_f_wing + V_f_fuse

    CDA0 = V_f_fuse/(10*ureg('m'))
    C_D_fuse = CDA0 / S

    while (V_cruisemax - V_cruisemax_prev).magnitude >= 0.1:
        Re = (rho / mu) * V_cruisemax * (S / A) ** 0.5
        C_f = 0.074 / Re ** 0.2
        C_D_wpar = k * C_f * S_wetratio

        C_D_ind = C_L ** 2 / (np.pi * A * e)
        C_D = C_D_fuse + C_D_wpar + C_D_ind

        V_cruisemax_prev = V_cruisemax
        V_cruisemax = 1/(TSFC * Range * 0.5 * rho * S * C_D / W_f)
    V_cruisemin = ((W_0 + W_w + 0.5 * W_f)/(0.5 * rho * S * C_L))**0.5

    if (V_cruisemin > V_cruisemax):
        return True
