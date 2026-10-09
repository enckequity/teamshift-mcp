import { build } from 'esbuild';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
const digest = path => createHash('sha256').update(readFileSync(path)).digest('hex');
const manifest = JSON.parse(readFileSync('native/upstream/manifest.json', 'utf8'));
if (manifest.revision !== '21a9a2febd7100d7c17ac1021ee7f2ed9f66a1e0') throw new Error('Unexpected upstream source');
for (const [path, receipt] of Object.entries(manifest.files)) {
  if (digest(`native/upstream/${path}`) !== receipt.installed_sha256) throw new Error(`Upstream source differs: ${path}`);
}
await build({entryPoints:['native/main.ts'],bundle:true,platform:'node',format:'esm',
  banner:{js:'import { createRequire } from "node:module"; const require = createRequire(import.meta.url);'},
  outfile:'native/runner.mjs'});
writeFileSync('native/build-receipt.json',JSON.stringify({upstream:manifest.revision,
  lockfile_sha256:digest('package-lock.json'),runner_sha256:digest('native/runner.mjs'),
  manifest_sha256:digest('native/upstream/manifest.json')},null,2)+'\n');