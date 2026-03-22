import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.finance import GBM


def _main() -> None:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--S0", type=float, required=True)
    p.add_argument("--mu", type=float, required=True)
    p.add_argument("--sigma", type=float, required=True)
    p.add_argument("--T", type=float, required=True)
    p.add_argument("--N", type=int, required=True)
    p.add_argument("--n_paths", type=int, default=1)
    p.add_argument("--K", type=float, required=True)
    p.add_argument("--r", type=float, required=True)
    p.add_argument(
        "--tipo_opcion",
        type=str,
        required=True,
        choices=("Call", "Put", "Straddle", "Binary"),
    )
    p.add_argument("-h", "--help", action="help", help="Mostrar ayuda y salir")
    args = p.parse_args()

    gbm = GBM(S0=args.S0, mu=args.mu, sigma=args.sigma, T=args.T, N=args.N)
    paths = gbm.simulate(n_paths=args.n_paths, use_risk_neutral=True, r=args.r)
    bs = gbm.black_scholes_price(
        K=args.K, r=args.r, option_type=args.tipo_opcion
    )

    out = {
        "S0": args.S0,
        "mu": args.mu,
        "sigma": args.sigma,
        "T": args.T,
        "N": args.N,
        "K": args.K,
        "r": args.r,
        "tipo_opcion": args.tipo_opcion,
        "simulated_paths": paths.tolist(),
        "black_scholes_price": float(bs),
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    _main()
