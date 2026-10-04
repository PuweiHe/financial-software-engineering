const yearSelect = document.querySelector('#year');
const branchSelect = document.querySelector('#branch');
const status = document.querySelector('#status');
const retry = document.querySelector('#retry');
const output = {
  total: document.querySelector('#total'),
  count: document.querySelector('#count'),
  share: document.querySelector('#share'),
  growth: document.querySelector('#growth'),
  rows: document.querySelector('#rows'),
  year: document.querySelector('#year-label'),
};

function percent(value) {
  return value === null ? 'No baseline' : `${(value * 100).toFixed(1)}%`;
}

async function jsonResponse(url) {
  const response = await fetch(url, { signal: AbortSignal.timeout(10000) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}

function render(report) {
  output.total.textContent = report.total_revenue_million.toFixed(1);
  output.count.textContent = String(report.branches.length);
  output.share.textContent = report.selected_branch ? (report.selected_branch.share === null ? 'Undefined' : percent(report.selected_branch.share)) : 'Choose a branch';
  output.growth.textContent = report.selected_branch ? percent(report.selected_branch.growth) : 'Choose a branch';
  output.year.textContent = `${report.year} · synthetic observations`;
  output.rows.replaceChildren();
  report.branches.forEach((branch, index) => {
    const row = document.createElement('tr');
    if (branch.branch_id === branchSelect.value) row.className = 'selected';
    const values = [String(index + 1), branch.branch_id, branch.revenue_million.toFixed(1), branch.share === null ? 'Undefined' : percent(branch.share), percent(branch.growth)];
    values.forEach(value => {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.append(cell);
    });
    output.rows.append(row);
  });
}

async function loadReport(resetBranch = false) {
  status.textContent = 'Loading metrics…';
  retry.hidden = true;
  document.querySelector('.workspace').setAttribute('aria-busy', 'true');
  yearSelect.disabled = true;
  branchSelect.disabled = true;
  try {
    if (resetBranch) branchSelect.value = '';
    const params = new URLSearchParams({ year: yearSelect.value });
    if (branchSelect.value) params.set('branch_id', branchSelect.value);
    const report = await jsonResponse(`/api/metrics?${params}`);
    if (resetBranch || branchSelect.options.length <= 1) {
      branchSelect.replaceChildren(new Option('All branches', ''));
      report.branches.forEach(branch => branchSelect.add(new Option(branch.branch_id, branch.branch_id)));
    }
    render(report);
    status.textContent = 'Showing local sample data';
  } catch (error) {
    clearReport();
    retry.hidden = false;
    status.textContent = `Unable to load: ${error.message}`;
  } finally {
    document.querySelector('.workspace').setAttribute('aria-busy', 'false');
    yearSelect.disabled = false;
    branchSelect.disabled = false;
  }
}

yearSelect.addEventListener('change', () => loadReport(true));
branchSelect.addEventListener('change', () => loadReport());

function clearReport() {
  for (const key of ['total', 'count', 'share', 'growth']) output[key].textContent = '—';
  output.rows.replaceChildren();
  output.year.textContent = '';
}

retry.addEventListener('click', () => initialize());

async function initialize() {
  retry.hidden = true;
  try {
    const data = await jsonResponse('/api/years');
    yearSelect.replaceChildren();
    data.years.forEach(year => yearSelect.add(new Option(String(year), String(year))));
    if (data.years.length) await loadReport(true);
    else {
      clearReport();
      yearSelect.disabled = true;
      branchSelect.disabled = true;
      status.textContent = 'No sample years available';
    }
  } catch (error) {
    clearReport();
    retry.hidden = false;
    status.textContent = `Unable to load: ${error.message}`;
  }
}

initialize();

async function initializeAgent() {
  const response = await fetch('/api/capabilities');
  if (!response.ok) return;
  const capabilities = await response.json();
  if (!capabilities.agent) return;
  document.querySelector('#agent-panel').hidden = false;
  document.querySelector('#agent-mode').textContent = capabilities.mode === 'live'
    ? 'Live model · synthetic SQLite data'
    : 'Scripted model · real tool execution · synthetic SQLite data';
}

document.querySelector('#agent-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = document.querySelector('#ask');
  const status = document.querySelector('#agent-status');
  const answer = document.querySelector('#agent-answer');
  const evidence = document.querySelector('#agent-evidence');
  button.disabled = true;
  answer.textContent = '';
  evidence.replaceChildren();
  status.textContent = 'Starting request…';
  let reader;
  let completed = false;
  try {
    const response = await fetch('/api/agent/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: document.querySelector('#question').value }),
      signal: AbortSignal.timeout(35000),
    });
    if (!response.ok) throw new Error('Question could not be accepted');
    reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary;
      while ((boundary = buffer.search(/\r?\n\r?\n/)) !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary).replace(/^\r?\n\r?\n/, '');
        const lines = frame.split(/\r?\n/);
        const type = lines.find(line => line.startsWith('event:'))?.slice(6).trim();
        const payload = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
        if (!payload) continue;
        const data = JSON.parse(payload);
        if (type === 'status') status.textContent = data.message;
        if (type === 'answer') answer.textContent = data.text;
        if (type === 'report') {
          evidence.replaceChildren();
          const heading = document.createElement('p');
          heading.textContent = `SQLite evidence · ${data.year} · total revenue ${data.total_revenue_million.toFixed(1)} million`;
          evidence.append(heading);
          const branches = data.selected_branch ? [data.selected_branch] : data.branches;
          for (const branch of branches) {
            const row = document.createElement('p');
            row.textContent = `${branch.branch_id}: revenue ${branch.revenue_million.toFixed(1)} million; share ${branch.share === null ? 'Undefined' : percent(branch.share)}; growth ${percent(branch.growth)}.`;
            evidence.append(row);
          }
        }
        if (type === 'error') throw new Error(data.message);
        if (type === 'done') { completed = true; status.textContent = 'Complete · synthetic data'; }
      }
    }
    if (!completed) throw new Error('Connection ended before the request completed');
  } catch (error) {
    answer.textContent = '';
    evidence.replaceChildren();
    status.textContent = `Unable to complete: ${error.message}`;
  } finally {
    await reader?.cancel().catch(() => {});
    button.disabled = false;
  }
});

initializeAgent().catch(() => {});
