'use strict';
// All paths are relative to this index document, so a static subdirectory deployment works.
const ORMS = ['Jdbc', 'Kronos', 'Jpa', 'Jimmer', 'Ktorm', 'Mybatis'];
const byId = id => document.getElementById(id);
const text = (id, value) => { byId(id).textContent = value; };
const format = value => Number.isFinite(value) ? value.toLocaleString('en', {maximumFractionDigits: 3}) : '—';
const labelFor = definition => {
  const p = definition.parameters;
  return definition.kind === 'read'
    ? `${p.projection} · ${Number(p.tableRows).toLocaleString()} table rows · ${p.resultRows} returned rows · ${p.access}`
    : `${p.transactionRows} assigned-key row-wise INSERTs / transaction`;
};
function localPath(path) {
  if (typeof path !== 'string' || path.startsWith('/') || path.includes('\\') || path.split('/').includes('..') || /^[a-z][a-z0-9+.-]*:/i.test(path)) throw new Error('Invalid local report path');
  return new URL(path, document.baseURI).href;
}
function anchor(label, path) {
  const result = document.createElement('a'); result.textContent = label; result.href = localPath(path); return result;
}
function appendCell(row, content) {
  const cell = document.createElement('td');
  if (content instanceof Node) cell.append(content); else cell.textContent = String(content);
  row.append(cell);
}
async function main() {
  const response = await fetch(new URL('./data/report.json', document.baseURI));
  if (!response.ok) throw new Error(`Report JSON HTTP ${response.status}`);
  const report = await response.json();
  if (report.schemaVersion !== 1 || !report.reportId || !report.scenarios?.length) throw new Error('Unsupported or incomplete report data');
  text('identity', `${report.candidateGitSha} · benchmark source ${report.benchmarkSourceSha256} · ${report.runRangeUTC.start} — ${report.runRangeUTC.end}`);
  const c = report.coverage;
  text('coverage', `${c.passedForkRuns}/${c.plannedForkRuns} scheduled fork runs passed; ${c.failedForkRuns} failed; ${c.notRunForkRuns} not run. Scenario states: ${JSON.stringify(c.scenarioStates)}.`);
  text('limitations', report.partialReason || 'Interpret the complete scene matrix with its confidence intervals and configuration. Scope: this host, JVM and MySQL workload.');
  for (const [label, path] of Object.entries(report.downloads)) byId('downloads').append(anchor(label, path));
  for (const [name, value] of Object.entries(report.environment)) {
    if (value !== null && typeof value !== 'object') {
      const key = document.createElement('dt'), item = document.createElement('dd');
      key.textContent = name; item.textContent = String(value); byId('environment').append(key, item);
    }
  }
  text('artifacts', JSON.stringify({requested: report.requestedVersions, resolved: report.resolvedArtifacts}, null, 2));
  const selector = byId('case');
  for (const scenario of report.scenarios) {
    const option = document.createElement('option'); option.value = scenario.id; option.textContent = labelFor(scenario.definition); selector.append(option);
  }
  let requestNumber = 0;
  async function render(id) {
    const request = ++requestNumber;
    const scenario = report.scenarios.find(item => item.id === id) || report.scenarios[0];
    selector.value = scenario.id;
    const detailsResponse = await fetch(localPath(scenario.details));
    if (!detailsResponse.ok) throw new Error(`Scenario JSON HTTP ${detailsResponse.status}`);
    const detail = await detailsResponse.json();
    if (request !== requestNumber) return;
    if (detail.id !== scenario.id) throw new Error('Scenario identity differs from index');
    text('case-description', labelFor(scenario.definition));
    text('latency-label', `Mean (${scenario.definition.primaryUnit})`);
    byId('results').replaceChildren();
    for (const orm of ORMS) {
      const score = detail.frameworks[orm], row = document.createElement('tr');
      const evidence = document.createElement('span');
      score.raw.forEach((entry, index) => {
        if (index) evidence.append(document.createTextNode(' · '));
        evidence.append(anchor(`block ${entry.block} ${entry.status}`, entry.path));
      });
      appendCell(row, orm); appendCell(row, score.status); appendCell(row, score.n);
      appendCell(row, format(score.mean));
      appendCell(row, score.mean95CI ? `${format(score.mean95CI[0])} — ${format(score.mean95CI[1])}` : '—');
      appendCell(row, format(score.median)); appendCell(row, evidence); byId('results').append(row);
    }
    byId('figure-section').hidden = !scenario.figure;
    if (scenario.figure) {
      byId('figure').src = localPath(scenario.figure.png);
      text('figure-caption', `${labelFor(scenario.definition)}. Dots: independent JVM fork means. Mean and 95% Student t CI. Source: formal JMH JSON; ${report.runRangeUTC.start} — ${report.runRangeUTC.end} UTC.`);
    }
    byId('case-download').replaceChildren(anchor('Scenario details, paired ratios, raw references and run states', scenario.details));
    const url = new URL(location.href); url.searchParams.set('case', scenario.id); history.replaceState(null, '', url);
  }
  selector.addEventListener('change', () => render(selector.value).catch(showError));
  const initial = new URL(location.href).searchParams.get('case');
  await render(initial);
}
function showError(error) {
  byId('load-error').hidden = false;
  text('load-error', `Could not load this report: ${error.message}. Serve the complete bundle over HTTP, or open its readme.md.`);
}
main().catch(showError);
