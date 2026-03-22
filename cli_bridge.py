import argparse
import json
import pathlib
import sys
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.finance import GBM


OPTION_TYPES = ("Call", "Put", "Straddle", "Binary")


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(
        "use_risk_neutral debe ser true/false"
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "--mode",
        type=str,
        default="pricing",
        choices=("pricing", "hedging"),
    )
    p.add_argument("--S0", type=float)
    p.add_argument("--mu", type=float)
    p.add_argument("--sigma", type=float)
    p.add_argument("--T", type=float)
    p.add_argument("--N", type=int)
    p.add_argument("--n_paths", type=int, default=1)
    p.add_argument("--K", type=float)
    p.add_argument("--r", type=float)
    p.add_argument(
        "--tipo_opcion",
        type=str,
        choices=OPTION_TYPES,
    )
    p.add_argument("--frecuencia", type=int)
    p.add_argument("--use_risk_neutral", type=_parse_bool)
    p.add_argument("-h", "--help", action="help", help="Mostrar ayuda y salir")
    return p


def _validate_required(args: argparse.Namespace, required_fields: tuple[str, ...]) -> None:
    missing = [field for field in required_fields if getattr(args, field) is None]
    if missing:
        raise ValueError(
            f"Faltan argumentos requeridos para mode={args.mode}: {', '.join(missing)}"
        )


def _run_pricing(args: argparse.Namespace) -> dict:
    _validate_required(
        args,
        ("S0", "mu", "sigma", "T", "N", "K", "r", "tipo_opcion"),
    )
    gbm = GBM(S0=args.S0, mu=args.mu, sigma=args.sigma, T=args.T, N=args.N)
    paths = gbm.simulate(n_paths=args.n_paths, use_risk_neutral=True, r=args.r)
    bs = gbm.black_scholes_price(
        K=args.K, r=args.r, option_type=args.tipo_opcion
    )
    return {
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


def _run_hedging(args: argparse.Namespace) -> dict:
    _validate_required(
        args,
        (
            "S0",
            "mu",
            "sigma",
            "T",
            "K",
            "r",
            "tipo_opcion",
            "frecuencia",
            "use_risk_neutral",
        ),
    )
    n_steps = 252
    rebalance_steps = max(1, int(args.frecuencia))

    modelo = GBM(S0=args.S0, mu=args.mu, sigma=args.sigma, T=args.T, N=n_steps)
    S = modelo.simulate(
        n_paths=1,
        use_risk_neutral=args.use_risk_neutral,
        r=args.r,
    ).flatten()
    tiempos = modelo.time_grid

    prima_inicial = modelo.black_scholes_price(
        K=args.K, r=args.r, option_type=args.tipo_opcion
    )
    delta_t = modelo.get_delta(
        S[0],
        args.K,
        args.r,
        args.sigma,
        args.T,
        option_type=args.tipo_opcion,
    )
    caja = prima_inicial - delta_t * S[0]

    hist_cartera = [float(prima_inicial)]
    hist_bs_teorico = [float(prima_inicial)]
    hist_deltas = [float(delta_t)]

    for t in range(1, len(tiempos)):
        dt_step = tiempos[t] - tiempos[t - 1]
        T_restante = max(args.T - tiempos[t], 0.0)
        caja *= float(np.exp(args.r * dt_step))

        if t % rebalance_steps == 0 or t == len(tiempos) - 1:
            nueva_delta = modelo.get_delta(
                S[t],
                args.K,
                args.r,
                args.sigma,
                T_restante,
                option_type=args.tipo_opcion,
            )
            compra_venta = nueva_delta - delta_t
            caja -= compra_venta * S[t]
            delta_t = nueva_delta

        valor_total_cartera = caja + delta_t * S[t]
        hist_cartera.append(float(valor_total_cartera))

        valor_bs_teorico = modelo.black_scholes_price(
            args.K,
            args.r,
            S[t],
            T_restante,
            option_type=args.tipo_opcion,
        )
        hist_bs_teorico.append(float(valor_bs_teorico))
        hist_deltas.append(float(delta_t))

    valor_final = hist_cartera[-1]
    payoff_final = hist_bs_teorico[-1]
    pnl_final = float(valor_final - payoff_final)
    error_abs = abs(pnl_final)

    diff_temporal = np.abs(np.array(hist_cartera) - np.array(hist_bs_teorico))
    tracking_error = float(np.mean(diff_temporal))
    error_vs_prima = float((error_abs / prima_inicial * 100) if prima_inicial > 0 else 0.0)
    error_vs_payoff = float((error_abs / payoff_final * 100) if payoff_final > 0 else 0.0)

    return {
        "tiempos": [float(x) for x in tiempos.tolist()],
        "hist_cartera": hist_cartera,
        "hist_bs_teorico": hist_bs_teorico,
        "hist_deltas": hist_deltas,
        "metrics": {
            "pnl_final": pnl_final,
            "tracking_error": tracking_error,
            "error_vs_prima": error_vs_prima,
            "error_vs_payoff": error_vs_payoff,
        },
    }


def _main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.mode == "hedging":
        out = _run_hedging(args)
    else:
        out = _run_pricing(args)

    sys.stdout.write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    _main()
