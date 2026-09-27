import { Container, getContainer } from "@cloudflare/containers";

export class VentureSimulatorV2 extends Container {
  defaultPort = 8080;
  sleepAfter = "24h";
  envVars = {
    MARKET_HOST: "0.0.0.0",
    MARKET_PORT: "8080",
    COOKIE_SECURE: "1",
    MODEL_DEVICE: "cpu",
    MODEL_CPU_THREADS: "1",
    MODEL_PRELOAD_SEMANTIC: "0",
    MODEL_ALLOW_DOWNLOAD: "0",
    TRANSFORMERS_OFFLINE: "1",
  };
}

export default {
  async fetch(request, env) {
    return getContainer(env.VENTURE_SIMULATOR, "production").fetch(request);
  },
};
