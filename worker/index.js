import { Container, getContainer } from "@cloudflare/containers";

export class VentureSimulator extends Container {
  defaultPort = 8080;
  sleepAfter = "24h";
}

export default {
  async fetch(request, env) {
    return getContainer(env.VENTURE_SIMULATOR, "production").fetch(request);
  },
};
