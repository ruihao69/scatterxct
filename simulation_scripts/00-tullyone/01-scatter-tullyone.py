import numpy as np
from joblib import Parallel, delayed

from scatterxct.dynamics.run import run_time_independent_dynamics
from scatterxct.models.tullyone import get_tullyone, TullyOnePulseTypes

from utils import get_tullyone_p0_list, estimate_delay_time_tullyone, estimate_dt

from typing import Optional
from pathlib import Path
import argparse

def check_if_has_ffmpeg():
    import shutil
    return shutil.which("ffmpeg") is not None

def run_single_tullyone(
    R0: float,
    k0: float,
    pulse_type: TullyOnePulseTypes,
    Omega: Optional[float] = None,
    tau: Optional[float] = None,
    phi: Optional[float] = None,
    project_dir: Path = Path("./"),
    save_movie: bool = False
):
    # estimate the delay time using MQC dynamics
    if pulse_type != TullyOnePulseTypes.NO_PULSE:
        delay_time = estimate_delay_time_tullyone(R0, k0)
        
    # get the hamiltonian
    if pulse_type == TullyOnePulseTypes.NO_PULSE:
        hamiltonian = get_tullyone( 
            pulse_type=TullyOnePulseTypes.NO_PULSE
        )
    else:
        hamiltonian = get_tullyone(
            t0=delay_time, Omega=Omega, tau=tau, phi=phi,
            pulse_type=pulse_type
        )
    
    # estimate the time step based on the driving frequency
    dt = 0.1 if Omega is None else estimate_dt(Omega)
    
    # prepare the file name for the movie
    # if pulse_type == TullyOnePulseTypes.NO_PULSE:
    #     # fname_movie: str = f"scatter_movie-k0_{k0}.gif"
    #     fname_movie: str = f"scatter_movie-k0_{k0}.mp4"
    # else:
    #     # fname_movie: str = f"scatter_movie-k0_{k0}-Omega_{Omega}-tau_{tau}.gif"
    #     fname_movie: str = f"scatter_movie-k0_{k0}.mp4"
    if check_if_has_ffmpeg():
        fname_movie: str = f"scatter_movie-k0_{k0:0.4f}.mp4"
    else:
        fname_movie: str = f"scatter_movie-k0_{k0:0.4f}.gif"
        
    if save_movie:
        dir_movie: Path = project_dir / fname_movie
    else:
        dir_movie = None
    
    # run the dynamics
    return run_time_independent_dynamics(
        hamiltonian=hamiltonian,
        R0=R0,
        k0=k0,
        dt=dt,
        initial_state=0,
        save_every=10,
        movie_path=dir_movie
    )
    

def main(
    n_momentum_samples: int = 48, 
    pulse_type: TullyOnePulseTypes = TullyOnePulseTypes.NO_PULSE,
    Omega: Optional[float] = None,  
    tau: Optional[float] = None,
    phi: Optional[float] = None
):
    
    def pulse_type_to_dir_name(pulse_type: TullyOnePulseTypes) -> str:
        if pulse_type == TullyOnePulseTypes.NO_PULSE: 
            return f"data_{pulse_type.name}"
        else:
            return f"data_{pulse_type.name}-Omega_{Omega:0.4f}-tau_{tau:0.4f}"
    
    # make the directory if it does not exist
    project_dir: Path = Path(pulse_type_to_dir_name(pulse_type))
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # prepare the momentum list, and a fixed list of R0, Omega, and tau
    k0 = get_tullyone_p0_list(n_momentum_samples, pulse_type)
    R0 = np.array([-10.0] * n_momentum_samples)
    Omega = np.array([Omega] * n_momentum_samples)
    tau = np.array([tau] * n_momentum_samples)
    phi = np.array([phi] * n_momentum_samples)
    
    output = Parallel(n_jobs=-1)(
        delayed(run_single_tullyone)(
            R0[i], k0[i], pulse_type, Omega[i], tau[i], phi[i], project_dir, save_movie=True
        ) for i in range(n_momentum_samples)
    )
    
    for i, out in enumerate(output):
        if pulse_type == TullyOnePulseTypes.NO_PULSE:
            trajdir = project_dir / f"traj_k0_{k0[i]}.npz"
        else:   
            trajdir = project_dir / f"traj_k0_{k0[i]}-Omega_{Omega[i]}-tau_{tau[i]}.npz"
        np.savez(
            trajdir,
            time=out['time'],
            R=out['R'],
            k=out['k'],
            diab_populations=np.array(out['diab_populations']),
            adiab_populations=np.array(out['adiab_populations']),
            KE=out['KE'],
            PE=out['PE'],
            scatter_out_diab=np.array(out['scatter_out_diab']),
            scatter_out_adiab=np.array(out['scatter_out_adiab'])
        )
    
# %%
if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    # argparser.add_argument("--Omega", type=float)
    # argparser.add_argument("--tau", type=float)
    # argparser.add_argument("--pulse_type", type=int)
    argparser.add_argument("Omega", type=float)
    argparser.add_argument("tau", type=float)
    argparser.add_argument("phi", type=float)
    argparser.add_argument("pulse_type", type=int)
    
    # if the user does not provide the Omega and tau, then complain and throw an error
    parsed_args = argparser.parse_args()

    # if len(parsed_args) != 3:
    #     raise ValueError("Please provide the Omega and tau.")
    
    
    Omega = parsed_args.Omega
    tau = parsed_args.tau
    phi = parsed_args.phi
    _pulse_type = parsed_args.pulse_type
    if _pulse_type == 1:
        pulse_type = TullyOnePulseTypes.PULSE_TYPE1
    elif _pulse_type == 2:
        pulse_type = TullyOnePulseTypes.PULSE_TYPE2
    elif _pulse_type == 3:
        pulse_type = TullyOnePulseTypes.PULSE_TYPE3
    elif _pulse_type == 0:
        pulse_type = TullyOnePulseTypes.NO_PULSE
    else:
        raise ValueError(f"Unknown pulse type {_pulse_type=}")

    NSAMPLES = 48
    
    main(
        n_momentum_samples=NSAMPLES,
        Omega=Omega,
        tau=tau,
        pulse_type=pulse_type, 
    )
