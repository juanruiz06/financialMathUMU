import numpy as np

class StochasticProcess:
    def __init__ (self, T: float, N:int):
        self.T = T #tiempo
        self.N = N #pasos de tiempo
        self.dt = T/N # "Diferencial de tiempo"
        self.time_grid = np.linspace(0,T,N)

    def generate_Brownian(self, n_paths=1):
        dw = np.random.normal(0,np.sqrt(self.dt), (self.N, n_paths))
        w = np.cumsum(dw, axis=0)
        return w
    

