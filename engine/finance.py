from engine.stochastic import StochasticProcess
import numpy as np
from scipy.stats import norm

class GBM(StochasticProcess):
    def __init__(self, S0, mu, sigma, T, N):
        super().__init__(T,N)
        self.S0 = S0
        self.mu = mu
        self.sigma = sigma
    def simulate(self, n_paths=1, use_risk_neutral = True, r = 0.03):
        drift = r if use_risk_neutral else self.mu
        W = self.generate_Brownian(n_paths)
        t = self.time_grid.reshape(-1,1)
        S = self.S0 * np.exp((drift - 0.5 * self.sigma**2) * t + self.sigma * W)
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
    
    def calculate_d1_d2(self, S, K, r, sigma, T):
        if T <= 1e-5:
            return 0.0, 0.0
        d1 = (np.log(S/K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return d1, d2
    
    def black_scholes_price(self, K, r, S = None, T_rem = None, option_type = "Call"):
        S = S if S is not None else self.S0
        T_rem = T_rem if T_rem is not None else self.T
        if T_rem <= 1e-5:
            if option_type == "Call":
                return max(S - K, 0)
            elif option_type == "Put":
                return max(K - S, 0)
            elif option_type == "Straddle":
                return abs(S - K)
            elif option_type == "Binary":
                return 1.0 if S > K else 0.0
            else:
                return 0.0
       
        T = max(T_rem, 1e-5)
        d1, d2 = self.calculate_d1_d2(S, K, r, self.sigma, T)

        if option_type == "Call":
            price = S * norm.cdf(d1) - K * np.exp(-r * T_rem) * norm.cdf(d2)
        elif option_type == "Put":
            price = K * np.exp(-r * T_rem) * norm.cdf(-d2) - S * norm.cdf(-d1)
        elif option_type == "Straddle":
            call_price = S * norm.cdf(d1) - K * np.exp(-r * T_rem) * norm.cdf(d2)
            put_price = K * np.exp(-r * T_rem) * norm.cdf(-d2) - S * norm.cdf(-d1)
            price = call_price + put_price
        elif option_type == "Binary":
            price = np.exp(-r * T_rem) * norm.cdf(d2)
        else:
            price = 0.0
        return price
    
    def get_delta(self, S, K, r, sigma, T, option_type = "Call"):
        if T <= 1e-5 if option_type != "Binary" else 5e-3: #1-2 dias para binarias para evitar inestabilidades
            if option_type == "Call":
                return 1.0 if S > K else 0.0
            elif option_type == "Put":
                return -1.0 if S < K else 0.0
            elif option_type == "Straddle":
                return 1.0 if S > K else (-1.0 if S < K else 0.0)
            elif option_type == "Binary":
                return 0.0
            return 0.0
        
        d1, d2 = self.calculate_d1_d2(S, K, r, sigma, T)
        if option_type == "Call":
            return norm.cdf(d1)
        elif option_type == "Put":
            return norm.cdf(d1) - 1
        elif option_type == "Straddle":
            return 2 * norm.cdf(d1) - 1
        elif option_type == "Binary":
            return (np.exp(-r * T) * norm.pdf(d2)) / (S * sigma * np.sqrt(T))
    
    def black_scholes_itm_probability(self, K, r, option_type = "Call", use_real_world = False):
        T = max(self.T, 1e-5)
        chosen_mu = self.mu if use_real_world else r
        d1, d2 = self.calculate_d1_d2(self.S0, K, chosen_mu, self.sigma, T)
        if option_type == "Call":
            return norm.cdf(d2)*100
        elif option_type == "Put":
            return norm.cdf(-d2)*100
        elif option_type == "Straddle":
            prima = self.black_scholes_price(K, r, option_type="Straddle")
            ku, kd = K + prima, max(0, K - prima)
            _, d2_u = self.calculate_d1_d2(self.S0, ku, chosen_mu, self.sigma, T)
            _, d2_d = self.calculate_d1_d2(self.S0, kd, chosen_mu, self.sigma, T)
            prob_u = norm.cdf(d2_u)     
            prob_d = norm.cdf(-d2_d)
            return (prob_u + prob_d)*100
        elif option_type == "Binary":
            return norm.cdf(d2)*100
        return 0.0
    