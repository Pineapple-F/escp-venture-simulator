import { createHash } from 'node:crypto';
import { appendFileSync, readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

// Reuse an existing account subdomain; only register when Cloudflare explicitly
// reports that none exists. An authentication failure must never cause a rename.
export async function ensureSubdomain(request, account) {
  try {
    const result = await request('/workers/subdomain');
    return result.subdomain;
  } catch (error) {
    if (!error.codes?.includes(10007)) throw error;
  }
  const suffix = createHash('sha256').update(account).digest('hex').slice(0, 12);
  const result = await request('/workers/subdomain', {
    method: 'PUT',
    body: JSON.stringify({ subdomain: `escp-${suffix}` }),
  });
  return result.subdomain;
}

async function main() {
  const token = process.env.CLOUDFLARE_API_TOKEN;
  const account = process.env.CLOUDFLARE_ACCOUNT_ID;
  if (!token || !/^[a-f0-9]{32}$/i.test(account || '')) {
    throw new Error('Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in GitHub Actions secrets.');
  }
  const request = async (path, options = {}) => {
    const response = await fetch(`https://api.cloudflare.com/client/v4/accounts/${account}${path}`, {
      ...options,
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(30000),
    });
    const body = await response.json();
    if (!response.ok || body.success === false) {
      const detail = (body.errors || []).map(e => `${e.code || ''} ${e.message || ''}`).join('; ');
      const error = new Error(`Cloudflare ${path}: HTTP ${response.status}. ${detail}`.replaceAll(token, '[REDACTED]'));
      error.codes = (body.errors || []).map(e => e.code);
      throw error;
    }
    return body.result;
  };
  for (const [name, path] of [['Workers', '/workers/scripts'], ['Containers', '/containers/applications']]) {
    await request(path);
    console.log(`${name}: account access OK`);
  }
  const subdomain = await ensureSubdomain(request, account);
  const config = JSON.parse(readFileSync(new URL('../wrangler.jsonc', import.meta.url), 'utf8'));
  const dnsLabel = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;
  if (!dnsLabel.test(subdomain || '') || !dnsLabel.test(config.name)) {
    throw new Error('Cloudflare returned an invalid workers.dev subdomain or the Worker name is invalid.');
  }
  const url = `https://${config.name}.${subdomain}.workers.dev`;
  console.log(`Deployment target: ${url}`);
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `url=${url}\n`);
  if (process.env.GITHUB_STEP_SUMMARY) {
    appendFileSync(process.env.GITHUB_STEP_SUMMARY, `Deployment target: [${url}](${url})\n\nThe container job must finish successfully before this deployment is verified.\n`);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => {
    console.error(`::error::${error.message}`);
    console.error('Check Workers Paid, the account scope, and Workers Scripts Edit / Containers Edit / Account Settings Read permissions. See docs/cloudflare-deployment.md.');
    process.exitCode = 1;
  });
}
