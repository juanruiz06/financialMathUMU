import { exec } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import express from "express";
import type { Request, Response } from "express";
import { z, ZodError } from "zod";

const execAsync = promisify(exec);

export const PricingRequestSchema = z.object({
  S0: z.number(),
  mu: z.number(),
  sigma: z.number(),
  T: z.number(),
  N: z.number().int(),
  n_paths: z.number().int().optional(),
  K: z.number(),
  r: z.number(),
  tipo_opcion: z.enum(["Call", "Put", "Straddle", "Binary"]),
});

export type PricingRequest = z.infer<typeof PricingRequestSchema>;

export const HedgingRequestSchema = z.object({
  S0: z.number(),
  mu: z.number(),
  sigma: z.number(),
  T: z.number(),
  K: z.number(),
  r: z.number(),
  tipo_opcion: z.enum(["Call", "Put", "Straddle", "Binary"]),
  frecuencia: z.number().int().positive(),
  use_risk_neutral: z.boolean(),
});

export type HedgingRequest = z.infer<typeof HedgingRequestSchema>;

const PricingResponseSchema = z.object({
  S0: z.number(),
  mu: z.number(),
  sigma: z.number(),
  T: z.number(),
  N: z.number(),
  K: z.number(),
  r: z.number(),
  tipo_opcion: z.enum(["Call", "Put", "Straddle", "Binary"]),
  simulated_paths: z.array(z.array(z.number())),
  black_scholes_price: z.number(),
});

export type PricingResponse = z.infer<typeof PricingResponseSchema>;

const HedgingResponseSchema = z.object({
  tiempos: z.array(z.number()),
  hist_cartera: z.array(z.number()),
  hist_bs_teorico: z.array(z.number()),
  hist_deltas: z.array(z.number()),
  metrics: z.object({
    pnl_final: z.number(),
    tracking_error: z.number(),
    error_vs_prima: z.number(),
    error_vs_payoff: z.number(),
  }),
});

export type HedgingResponse = z.infer<typeof HedgingResponseSchema>;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const backendDir = path.resolve(__dirname);
const cliBridgePath = path.resolve(backendDir, "..", "cli_bridge.py");

function buildCliCommand(body: PricingRequest): string {
  /** Por defecto `python3`; usa `PYTHON_EXECUTABLE=python` si el binario se llama así. */
  const pythonBin = process.env["PYTHON_EXECUTABLE"] ?? "python3";
  const parts: string[] = [
    pythonBin,
    cliBridgePath,
    "--S0",
    String(body.S0),
    "--mu",
    String(body.mu),
    "--sigma",
    String(body.sigma),
    "--T",
    String(body.T),
    "--N",
    String(body.N),
    "--K",
    String(body.K),
    "--r",
    String(body.r),
    "--tipo_opcion",
    body.tipo_opcion,
  ];
  if (body.n_paths !== undefined) {
    parts.push("--n_paths", String(body.n_paths));
  }
  return parts.map(shellQuote).join(" ");
}

function buildHedgingCliCommand(body: HedgingRequest): string {
  const pythonBin = process.env["PYTHON_EXECUTABLE"] ?? "python3";
  const parts: string[] = [
    pythonBin,
    cliBridgePath,
    "--mode",
    "hedging",
    "--S0",
    String(body.S0),
    "--mu",
    String(body.mu),
    "--sigma",
    String(body.sigma),
    "--T",
    String(body.T),
    "--K",
    String(body.K),
    "--r",
    String(body.r),
    "--tipo_opcion",
    body.tipo_opcion,
    "--frecuencia",
    String(body.frecuencia),
    "--use_risk_neutral",
    String(body.use_risk_neutral),
  ];
  return parts.map(shellQuote).join(" ");
}

function shellQuote(arg: string): string {
  return `'${arg.replace(/'/g, `'\\''`)}'`;
}

async function runPricingCli(body: PricingRequest): Promise<PricingResponse> {
  const cmd = buildCliCommand(body);
  const { stdout, stderr } = await execAsync(cmd, {
    encoding: "utf8",
    maxBuffer: 50 * 1024 * 1024,
  });

  const errText = stderr.trim();
  if (errText.length > 0) {
    throw new Error(`Python stderr: ${errText}`);
  }

  const raw: unknown = JSON.parse(stdout);
  return PricingResponseSchema.parse(raw);
}

async function runHedgingCli(body: HedgingRequest): Promise<HedgingResponse> {
  const cmd = buildHedgingCliCommand(body);
  const { stdout, stderr } = await execAsync(cmd, {
    encoding: "utf8",
    maxBuffer: 50 * 1024 * 1024,
  });

  const errText = stderr.trim();
  if (errText.length > 0) {
    throw new Error(`Python stderr: ${errText}`);
  }

  const raw: unknown = JSON.parse(stdout);
  return HedgingResponseSchema.parse(raw);
}

const app = express();
app.use(express.json());

app.post("/api/pricing", async (req: Request, res: Response) => {
  let body: PricingRequest;
  try {
    body = PricingRequestSchema.parse(req.body);
  } catch (err: unknown) {
    if (err instanceof ZodError) {
      return res.status(400).json({ error: err.flatten() });
    }
    console.error("Unexpected validation error:", err);
    return res.status(500).json({
      message: "Error interno calculando el pricing",
    });
  }

  try {
    const result = await runPricingCli(body);
    return res.status(200).json(result);
  } catch (err: unknown) {
    console.error("Pricing CLI error:", err);
    return res.status(500).json({
      message: "Error interno calculando el pricing",
    });
  }
});

app.post("/api/hedging", async (req: Request, res: Response) => {
  let body: HedgingRequest;
  try {
    body = HedgingRequestSchema.parse(req.body);
  } catch (err: unknown) {
    if (err instanceof ZodError) {
      return res.status(400).json({ error: err.flatten() });
    }
    console.error("Unexpected validation error:", err);
    return res.status(500).json({
      message: "Error interno calculando el pricing",
    });
  }

  try {
    const result = await runHedgingCli(body);
    return res.status(200).json(result);
  } catch (err: unknown) {
    console.error("Hedging CLI error:", err);
    return res.status(500).json({
      message: "Error interno calculando el pricing",
    });
  }
});

const PORT = Number(process.env["PORT"]) || 3000;
app.listen(PORT, () => {
  console.error(`API listening on port ${PORT}`);
});
