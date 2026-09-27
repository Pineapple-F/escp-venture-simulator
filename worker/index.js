import { Container, getContainer } from "@cloudflare/containers";
import { SaveStore } from "./save-store.mjs";
export { ContainerProxy } from "@cloudflare/containers";

export class VentureSimulatorV2 extends Container {
  defaultPort = 8080;
  sleepAfter = "10m";
  envVars = {
    MARKET_HOST: "0.0.0.0",
    MARKET_PORT: "8080",
    COOKIE_SECURE: "1",
    MODEL_DEVICE: "cpu",
    MODEL_CPU_THREADS: "1",
    MODEL_PRELOAD_SEMANTIC: "0",
    MODEL_ALLOW_DOWNLOAD: "0",
    TRANSFORMERS_OFFLINE: "1",
    MODEL_WARM_ON_START: "0",
    SAVE_STORE_URL: "http://saves.internal/",
  };

  constructor(ctx, env) {
    super(ctx, env);
    this.envVars.COOKIE_SECURE = env.COOKIE_SECURE ?? "1";
    this.saves = new SaveStore(ctx.storage.sql);
  }

  saveOperation(payload) {
    return this.saves.operate(payload);
  }
}

VentureSimulatorV2.outboundByHost = {
  "saves.internal": async (request, env, ctx) => {
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405 });
    const id = env.VENTURE_SIMULATOR.idFromString(ctx.containerId);
    const result = await env.VENTURE_SIMULATOR.get(id).saveOperation(await request.json());
    return Response.json(result);
  },
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      try {
        return await getContainer(env.VENTURE_SIMULATOR, "production").fetch(request);
      } catch (error) {
        console.error("Container request failed", error.message);
        return Response.json({ error: "服务正在启动或暂时不可用，请稍后重试。" }, {
          status: 503, headers: { "Retry-After": "10", "Cache-Control": "no-store" },
        });
      }
    }
    return env.ASSETS.fetch(request);
  },
};
