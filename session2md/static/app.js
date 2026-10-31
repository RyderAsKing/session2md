'use strict';
const $ = id => document.getElementById(id);
const sources = ['claude', 't3', 'codex'];
let token = '';
function selection(source) {
  document.querySelector(`[data-source="${source}"]`).classList.toggle('selected', $(source + '-enabled').checked);
}
for (const source of sources) {
  $(source + '-enabled').addEventListener('change', () => selection(source));
  $(source + '-path').addEventListener('input', () => {
    $(source + '-enabled').checked = Boolean($(source + '-path').value.trim());
    selection(source);
  });
}
function result(title, text, error = false) {
  const box = $('result');
  box.replaceChildren();
  box.hidden = false;
  box.classList.toggle('error', error);
  const heading = document.createElement('h2'); heading.textContent = title; box.append(heading);
  const p = document.createElement('p'); p.textContent = text; box.append(p);
  return box;
}
async function run(demo, dryRun = false) {
  const output = $('output').value.trim();
  if (!output) { $('output').reportValidity(); return; }
  const selected = {};
  if (!demo) for (const s of sources) if ($(s + '-enabled').checked) {
    selected[s] = $(s + '-path').value.trim();
    if (!selected[s]) { result('Source path needed', `Enter a path for ${s}.`, true); return; }
  }
  if (!demo && !Object.keys(selected).length) { result('Choose a source', 'Enable at least one source or create a sample vault.', true); return; }
  const allChats = !demo && document.querySelector('input[name="scope"]:checked').value === 'all';
  const folder = demo || allChats ? null : $('project-folder').value.trim();
  if (!demo && !allChats && !folder) { result('Choose a project folder', 'Enter the project working folder, or explicitly select all chats.', true); $('project-folder').focus(); return; }
  const literals = $('redact-literals').value.split(/\r?\n/).filter(line => line.trim());
  if (literals.some(value => value.length < 3)) { result('Custom value is too short', 'Each custom redaction needs at least 3 characters.', true); return; }
  $('export-button').disabled = $('demo-button').disabled = $('scan-button').disabled = true;
  $('export-button').textContent = 'Exporting…';
  result('Preparing your vault', 'Reading local transcripts and writing Markdown. Large histories may take a while.');
  try {
    const response = await fetch('/api/export', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Session2md-Token': token}, body: JSON.stringify({sources: selected, output: demo ? output.replace(/[\\/]$/, '') + '-demo' : output, demo, folder, all_chats: allChats, exact_folder: !demo && !allChats && !$('include-subfolders').checked, literals, dry_run: dryRun, style: $('style').checked, reasoning: $('reasoning').checked})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Export failed');
    const box = result(dryRun ? 'Preview complete. No files written.' : data.imported === 0 ? 'No matching conversations. No files written.' : data.warnings.length ? 'Export finished with notes' : 'Your vault is ready', `${data.imported} conversations matched · ${data.excluded} excluded · ${data.written} files written · ${data.unchanged} unchanged · ${data.conflicts} preserved edits`);
    const privacy = document.createElement('p'); privacy.textContent = `${Object.values(data.redactions).reduce((a, b) => a + b, 0)} sensitive-content matches hidden across scanned fields. ${data.missing_workspace} excluded records had no working directory.`; box.append(privacy);
    if (!dryRun && data.imported > 0) {
    const code = document.createElement('code'); code.textContent = data.vault; box.append(code);
    const next = document.createElement('p'); next.textContent = 'In Obsidian, open this folder as a vault and start with “session2md home”. Enable the session2md snippet in Settings → Appearance → CSS snippets.'; box.append(next);
    }
    if (data.warnings.length) {
      const details = document.createElement('details'); const summary = document.createElement('summary'); summary.textContent = `${data.warnings.length} import or file notices`; details.append(summary);
      const list = document.createElement('ul'); for (const warning of data.warnings) { const li = document.createElement('li'); li.textContent = warning; list.append(li); } details.append(list); box.append(details);
    }
    box.scrollIntoView({behavior: 'smooth', block: 'nearest'});
  } catch (error) { result('Export could not finish', error.message, true); }
  finally { $('export-button').disabled = $('demo-button').disabled = $('scan-button').disabled = false; $('export-button').textContent = 'Export to Obsidian ↗'; }
}
$('export-form').addEventListener('submit', event => { event.preventDefault(); run(false); });
$('scan-button').addEventListener('click', () => run(false, true));
$('demo-button').addEventListener('click', () => run(true));
fetch('/api/config').then(r => {if (!r.ok) throw new Error('Cannot connect to the local app'); return r.json();}).then(config => {
  token = config.token;
  $('output').value = config.output;
  for (const s of sources) if (config.sources[s]) {
    $(s + '-path').value = config.sources[s];
    $(s + '-enabled').checked = true;
    $(s + '-status').textContent = '● Detected on this machine';
    selection(s);
  }
}).catch(error => result('Connection problem', error.message, true));
