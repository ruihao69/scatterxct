import numpy as np

from pymddrive.models.tullyone import get_tullyone, TullyOnePulseTypes
from pymddrive.integrators.state import State
from pymddrive.dynamics.options import BasisRepresentation, QunatumRepresentation, NonadiabaticDynamicsMethods, NumericalIntegrators    
from pymddrive.dynamics import NonadiabaticDynamics, run_nonadiabatic_dynamics 


def estimate_delay_time_tullyone(R0, P0, mass: float=2000.0):
    # model = TullyOne(A, B, C, D)
    hamiltonian = get_tullyone(
        pulse_type=TullyOnePulseTypes.NO_PULSE
    )
    print(f"{R0=}")
    print(f"{P0=}")
    rho0 = np.array([[1.0, 0], [0, 0.0]], dtype=np.complex128)
    s0 = State.from_variables(R=R0, P=P0, rho=rho0)
    dyn = NonadiabaticDynamics(
        hamiltonian=hamiltonian,
        t0=0.0,
        s0=s0,
        mass=mass,
        basis_rep=BasisRepresentation.Diabatic,
        qm_rep=QunatumRepresentation.DensityMatrix,
        solver=NonadiabaticDynamicsMethods.EHRENFEST,
        numerical_integrator=NumericalIntegrators.ZVODE,
        dt=1,
        save_every=1
    )
    def stop_condition(t, s, states):
        r, p, _ = s.get_variables()
        return (r>0.0) or (p<0.0)
    break_condition = lambda t, s, states: False
    res = run_nonadiabatic_dynamics(dyn, stop_condition, break_condition)
    return res['time'][-1]

def linspace_log10(start, stop, num=50):
    return np.power(10, np.linspace(np.log10(start), np.log10(stop), num))

def sample_sigmoid(x_left: float, x_right: float, n: int) -> np.ndarray:
    x_center = (x_left + x_right) / 2
    p0_seg1 = np.sort(x_center + x_left - linspace_log10(x_left, x_center, n // 2))
    dp = p0_seg1[-1] - p0_seg1[-2]
    p0_seg2 = x_center - x_left + dp + np.sort(linspace_log10(x_left, x_center, n - n // 2))
    return np.concatenate((p0_seg1, p0_seg2))

def get_tullyone_p0_list(nsamples: int, pulse_type: TullyOnePulseTypes=TullyOnePulseTypes.NO_PULSE) -> np.ndarray:
    if pulse_type.value == TullyOnePulseTypes.NO_PULSE.value or pulse_type.value == TullyOnePulseTypes.PULSE_TYPE3.value:
        p0_bounds_0 = (2.0, 12.0); n_bounds_0 = nsamples // 2
        p0_bounds_1 = (13, 35); n_bounds_1 = nsamples - n_bounds_0
    elif pulse_type.value == TullyOnePulseTypes.PULSE_TYPE1.value or pulse_type.value == TullyOnePulseTypes.PULSE_TYPE2.value:
        p0_bounds_0 = (0.5, 19); n_bounds_0 = nsamples // 3 * 2
        p0_bounds_1 = (20, 35); n_bounds_1 = nsamples - n_bounds_0

    p0_segment_0 = sample_sigmoid(*p0_bounds_0, n_bounds_0)
    p0_segment_1 = np.linspace(*p0_bounds_1, n_bounds_1)
    return np.concatenate((p0_segment_0, p0_segment_1))

def estimate_dt(Omega: float, dt: float = 0.1) -> float:
    SAFTY_FACTOR: float = 10.0
    T: float = 2 * np.pi / Omega
    if dt > T / SAFTY_FACTOR:
        return T / SAFTY_FACTOR
    else:
        return dt