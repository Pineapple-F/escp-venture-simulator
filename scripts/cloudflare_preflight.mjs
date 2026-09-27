// Read-only account checks. Never print tokens or registry credentials.
const token = process.env.CLOUDFLARE_API_TOKEN;
const account = process.env.CLOUDFLARE_ACCOUNT_ID;
if (!token || !/^[a-f0-9]{32}$/i.test(account || '')) {
  throw new Error('Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in GitHub Actions secrets.');
}
const headers = { Authorization: `Bearer ${token}` };
const base = `https://api.cloudflare.com/client/v4/accounts/${account}`;
let failed = false;
for (const [name, path] of [['Workers', '/workers/scripts'], ['Containers', '/containers/applications']]) {
  const response = await fetch(base + path, {headers});
  const raw = await response.text();
  let body; try {body=JSON.parse(raw);} catch {body={};}
  if (!response.ok || body.success === false) {
    failed = true;
    const detail = (body.errors || []).map(e=>`${e.code || ''} ${e.message || ''}`).join('; ');
    console.error(`::error::${name} preflight failed (HTTP ${response.status}). ${detail}`);
  } else console.log(`${name}: account access OK`);
}
if (failed) {
  console.error('Check Workers Paid enrollment, account scope, and Account > Containers Edit / Workers Scripts Edit permissions. See docs/cloudflare-deployment.md.');
  process.exit(1);
}
