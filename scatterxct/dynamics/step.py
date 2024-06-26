# %%
import numpy as np
from numpy.typing import ArrayLike

from scatterxct.core.wavefunction import WaveFunctionData
from scatterxct.core.propagator import PropagatorBase

from enum import Enum, unique
from typing import Tuple

@unique
class SplitOperatorType(Enum):
    PLAIN = 1
    TVT = 2
    VTV = 3

def kinetic_propagate(
    psi_data: WaveFunctionData, # (ngrid, nstates)
    T_propagator: ArrayLike, # (ngrid, ) since T_propagator is diagonal 
) -> WaveFunctionData:
    # technical note: 
    # WavefunctionData is an immutable dataclass (with frozen=True)
    # hence psi_data.psi cannot be reassigned to another reference.
    # The only viable (and legit) way to update the psi_data.psi is through broadcasting,
    # since at the end of the day, the psi_data.psi itself is a numpy array, which is mutable.
    # This particular choice of design is to ensure the safety of the data,
    # and to avoid reallocation of memory.
    psi_data.real_space_to_k_space()
    psi_data.psi[:] *= T_propagator[:, np.newaxis]
    psi_data.k_space_to_real_space()
    return psi_data
    
def potential_propagate(
    psi_data: WaveFunctionData, # (ngrid, nstates)
    V_propagator: ArrayLike, # (nstates, nstates, ngrid, )
) -> WaveFunctionData:
    # technical note: WavefunctionData is an immutable dataclass
    # (more details explained in the kinetic_propagate function)
    # output = np.einsum("jki,ik->ij", V_propagator, psi_data.psi)
    output = np.einsum("jki,ik->ij", V_propagator, psi_data.psi)
    # psi_data.psi[:] = np.einsum("jki,ik->ij", V_propagator, psi_data.psi)
    psi_data.psi[:] = output
    return psi_data    
    
def plain_propagate(
    psi_data: WaveFunctionData, # (ngrid, nstates)
    T_propagator: ArrayLike, # (ngrid, ) 
    V_propagator: ArrayLike, # (nstates, nstates, ngrid)
) -> WaveFunctionData:
    psi_data = kinetic_propagate(psi_data, T_propagator)
    psi_data = potential_propagate(psi_data, V_propagator)
    return psi_data

def TVT_propagate(
    psi_data: WaveFunctionData, # (ngrid, nstates)
    half_T_propagator: ArrayLike, # (ngrid, )  
    V_propagator: ArrayLike, # (ngrid, nstates, nstates)
) -> WaveFunctionData:
    psi_data = kinetic_propagate(psi_data, half_T_propagator)
    psi_data = potential_propagate(psi_data, V_propagator)
    psi_data = kinetic_propagate(psi_data, half_T_propagator)
    return psi_data

def VTV_propagate(
    psi_data: WaveFunctionData, # (ngrid, nstates)
    T_propagator: ArrayLike, # (ngrid, ) 
    half_V_propagator: ArrayLike, # (nstates, nstates, ngrid)
) -> WaveFunctionData:
    psi_data = potential_propagate(psi_data, half_V_propagator)
    psi_data = kinetic_propagate(psi_data, T_propagator)
    psi_data = potential_propagate(psi_data, half_V_propagator)
    return psi_data

def propagate(
    time: float,
    psi_data: WaveFunctionData, # (ngrid, nstates)
    propagator: PropagatorBase,
    split_operator_type: SplitOperatorType = SplitOperatorType.PLAIN,
) -> Tuple[float, WaveFunctionData]:
    if split_operator_type == SplitOperatorType.PLAIN:
        T_propagator: ArrayLike = propagator.get_T_propagator(time)
        V_propagator: ArrayLike = propagator.get_V_propagator(time)
        time += propagator.dt
        return time, plain_propagate(psi_data, T_propagator, V_propagator)
    elif split_operator_type == SplitOperatorType.TVT:
        half_T_propagator: ArrayLike = propagator.get_half_T_propagator(time)
        V_propagator: ArrayLike = propagator.get_V_propagator(time)
        time += propagator.dt
        return time, TVT_propagate(psi_data, half_T_propagator, V_propagator)
    elif split_operator_type == SplitOperatorType.VTV:
        T_propagator: ArrayLike = propagator.get_T_propagator(time)
        half_V_propagator: ArrayLike = propagator.get_half_V_propagator(time)
        time += propagator.dt
        return time, VTV_propagate(psi_data, T_propagator, half_V_propagator)
    else:
        raise ValueError(f"Unknown split operator type: {split_operator_type}")
