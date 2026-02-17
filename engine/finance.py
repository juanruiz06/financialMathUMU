from engine.stochastic import StochasticProcess
import numpy as np

class GBM(StochasticProcess):
    def __init__(self, S0, mu, sigma, T, N):
        super().__init__(T,N)
        self.S0 = S0
        self.mu = mu
        self.sigma = sigma
    def simulate(self, n_paths=1):
        W = self.generate_Brownian(n_paths)
        t = self.time_grid.reshape(-1,1)
        S = self.S0 * np.exp((self.mu - 0.5 * self.sigma**2) * t + self.sigma * W)
        return S
    
    def calculate_mc_price(self, K, r, simulated_paths, option_type = "Call"):
        S_T = simulated_paths[-1,:]
        if option_type == "Call":
            payoffs = np.maximum(S_T - K, 0)
        elif option_type == "Put":
            payoffs = np.maximum(K - S_T, 0)
        elif option_type == "Straddle":
            payoffs = np.abs(S_T - K)
        elif option_type == "Binary":
            payoffs = (S_T > K).astype(float)
        
        average_payoff = np.mean(payoffs)
        price = np.exp(-r * self.T) * average_payoff
        return price
    