/* ── Tab navigation ─────────────────────────────── */
const tabButtons = document.querySelectorAll('.tab-btn');
if (tabButtons.length) {
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
      btn.classList.add('active');
      const section = document.getElementById('tab-' + btn.dataset.tab);
      if (section) section.classList.add('active');
    });
  });
}

// Handle hash-based navigation from navbar
window.addEventListener('DOMContentLoaded', () => {
  const hash = window.location.hash.replace('#','');
  if (hash) {
    const btn = document.querySelector(`.tab-btn[data-tab="${hash}"]`);
    if (btn) btn.click();
  }
  if (document.getElementById('unassignedArea') && window.INITIAL_DATA && window.DEFAULT_TIERS) {
    initTierEditor();
  }
});

/* ── Helpers ─────────────────────────────────────── */
function showMsg(id, html, isErr=false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `<div class="${isErr?'msg-err':'msg-ok'}">${html}</div>`;
}
function showLoading(id, text='Processing…') {
  const el = document.getElementById(id);
  if (el) el.innerHTML = `<div class="msg-loading">⏳ ${text}</div>`;
}

async function api(url, body={}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  return res.json();
}

/* ── Setup ───────────────────────────────────────── */
function addPlayer() {
  const list = document.getElementById('playerList');
  const rows = list.querySelectorAll('.player-input-row');
  if (rows.length >= 10) { showMsg('setupMsg','Max 10 players allowed.',true); return; }
  const idx = rows.length;
  const div = document.createElement('div');
  div.className = 'player-input-row';
  div.dataset.idx = idx;
  div.innerHTML = `<input type="text" class="player-name-input" value="Player ${idx+1}"/>
    <button class="btn-danger-sm" onclick="removePlayer(this)">✕</button>`;
  list.appendChild(div);
  updateRemoveButtons();
}

function removePlayer(btn) {
  const rows = document.querySelectorAll('.player-input-row');
  if (rows.length <= 2) return;
  btn.closest('.player-input-row').remove();
  updateRemoveButtons();
}

function updateRemoveButtons() {
  const rows = document.querySelectorAll('.player-input-row');
  rows.forEach(row => {
    const btn = row.querySelector('.btn-danger-sm');
    if (btn) btn.style.display = rows.length > 2 ? '' : 'none';
  });
}

async function saveSetup() {
  const leagueName = document.getElementById('leagueName').value.trim();
  const budget = parseInt(document.getElementById('budget').value);
  const players = Array.from(document.querySelectorAll('.player-name-input'))
    .map(i => i.value.trim()).filter(Boolean);
  if (players.length < 2 || players.length > 10) {
    showMsg('setupMsg', 'Need between 2 and 10 players.', true); return;
  }
  const r = await api('/api/setup', {league_name: leagueName, budget, players});
  if (r.ok) {
    showMsg('setupMsg', 'Setup saved! Now configure your tiers →');
    setTimeout(() => { document.querySelector('.tab-btn[data-tab="tiers"]').click(); }, 700);
  }
}

/* ── Tier Editor ─────────────────────────────────── */
let dragTeam = null;
let currentTiers = {};

function initTierEditor() {
  const tierSource = (window.INITIAL_DATA && window.INITIAL_DATA.tiers) || window.DEFAULT_TIERS || {};
  if (!document.getElementById('unassignedArea')) return;
  // Deep copy from server-rendered data
  currentTiers = JSON.parse(JSON.stringify(tierSource));
  renderTierEditor();
}

function renderTierEditor() {
  const ua = document.getElementById('unassignedArea');
  if (!ua) return;
  updatePriceChips();
  // Build unassigned pool
  const assigned = Object.values(currentTiers).flat();
  const unassigned = (window.ALL_TEAMS || []).filter(t => !assigned.includes(t.name));

  if (unassigned.length) {
    ua.innerHTML = `<div class="unassigned-pool" style="margin-bottom:1rem">
      <div class="pool-label">Unassigned (${unassigned.length})</div>
      <div class="drop-zone" id="dropZone0"
        ondragover="dragOver(event)" ondragleave="dragLeave(event)" ondrop="dropTeam(event,0)">
        ${unassigned.map(t => chipHTML(t.name, 0)).join('')}
      </div>
    </div>`;
  } else {
    ua.innerHTML = '';
  }

  // Update drop zones for each tier
  for (let t = 1; t <= 6; t++) {
    const zone = document.getElementById(`dropZone${t}`);
    if (!zone) continue;
    const teams = currentTiers[t] || currentTiers[String(t)] || [];
    zone.innerHTML = teams.map(name => chipHTML(name, t)).join('');
    const countEl = document.getElementById(`tierCount${t}`);
    if (countEl) countEl.textContent = `${teams.length}/8`;
  }
}

function chipHTML(name, tier) {
  const tm = (window.ALL_TEAMS || []).find(x => x.name === name);
  const cls = tier > 0 ? `tier${tier}-chip` : '';
  return `<span class="team-chip ${cls}" draggable="true" data-team="${name}"
    ondragstart="startDrag(event)" ondragend="endDrag(event)">
    <span class="chip-flag">${tm ? tm.flag : ''}</span> ${name}
  </span>`;
}

function startDrag(e) {
  dragTeam = e.currentTarget.dataset.team;
  e.currentTarget.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
}
function endDrag(e) {
  e.currentTarget.classList.remove('dragging');
  document.querySelectorAll('.drop-zone').forEach(d => d.classList.remove('drag-over'));
}
function dragOver(e) { e.preventDefault(); e.currentTarget.classList.add('drag-over'); }
function dragLeave(e) { e.currentTarget.classList.remove('drag-over'); }

function dropTeam(e, newTier) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  if (!dragTeam) return;
  const name = dragTeam;
  // Remove from all tiers (1–6)
  for (let t = 1; t <= 6; t++) {
    const key = String(t);
    if (currentTiers[key]) currentTiers[key] = currentTiers[key].filter(x => x !== name);
    if (currentTiers[t]) currentTiers[t] = currentTiers[t].filter(x => x !== name);
  }
  // Add to new tier
  if (newTier >= 1 && newTier <= 6) {
    const key = String(newTier);
    if (!currentTiers[key]) currentTiers[key] = [];
    currentTiers[key].push(name);
  }
  dragTeam = null;
  renderTierEditor();
}

function updatePriceChips() {
  for (let t = 1; t <= 6; t++) {
    const inp = document.getElementById(`tierPrice${t}`);
    const chip = document.getElementById(`tierPriceChip${t}`);
    if (inp && chip) chip.textContent = inp.value + ' rupees';
  }
}

function resetTiers() {
  currentTiers = JSON.parse(JSON.stringify(window.DEFAULT_TIERS || {}));
  renderTierEditor();
}

async function saveTiers() {
  const assigned = Object.values(currentTiers).flat();
  if (assigned.length < 48) {
    showMsg('tierMsg', `${48 - assigned.length} team(s) still unassigned. Assign all 48 teams first.`, true);
    return;
  }
  const tierPrices = {};
  for (let t = 1; t <= 6; t++) {
    tierPrices[t] = parseInt(document.getElementById(`tierPrice${t}`).value) || 20;
  }
  const r = await api('/api/tiers', {tiers: currentTiers, tier_prices: tierPrices});
  if (r.ok) {
    showMsg('tierMsg', 'Tiers saved! Heading to auction…');
    setTimeout(() => { window.location.href = '/#auction'; window.location.reload(); }, 700);
  }
}

/* ── Auction ─────────────────────────────────────── */
async function placeBid() {
  const amt = parseInt(document.getElementById('bidAmount').value);
  const r = await api('/api/auction/bid', {amount: amt});
  if (!r.ok) {
    document.getElementById('bidMsg').innerHTML = `<span style="color:#791f1f;font-size:13px">⚠ ${r.error}</span>`;
    return;
  }
  updateAuctionUI(r.data);
}

async function passOnTeam() {
  const r = await api('/api/auction/pass');
  if (r.ok) updateAuctionUI(r.data);
}

async function autoAssign() {
  if (!confirm('Auto-assign all remaining teams to players in rotation?')) return;
  const r = await api('/api/auction/auto');
  if (r.ok) { window.location.reload(); }
}

function updateAuctionUI(data) {
  if (!data) return;

  // Update stats
  const teamsLeft = 48 - Object.keys(data.team_sold || {}).length;
  const el = id => document.getElementById(id);
  if (el('aucTeamsLeft')) el('aucTeamsLeft').textContent = teamsLeft;
  if (el('aucRound')) el('aucRound').textContent = Math.floor(Object.keys(data.team_sold||{}).length / Math.max((data.players||[]).length, 1)) + 1;

  const players = data.players || [];
  if (data.auction_done || data.auction_idx >= (data.auction_queue||[]).length) {
    document.getElementById('auctionLive').innerHTML =
      `<div class="success-banner">🏆 Auction Complete! All teams have been assigned.</div>`;
    if (el('aucCurrentBidder')) el('aucCurrentBidder').textContent = 'Done';
    updateBudgetList(data);
    return;
  }

  const curBidder = players[data.current_bidder % players.length];
  if (el('aucCurrentBidder')) el('aucCurrentBidder').textContent = curBidder ? curBidder.name : '—';

  const teamName = data.auction_queue[data.auction_idx];
  const team = (window.ALL_TEAMS || []).find(t => t.name === teamName);
  let tier = 0;
  for (const [t, tl] of Object.entries(data.tiers || {})) {
    if (Array.isArray(tl) && tl.includes(teamName)) { tier = parseInt(t); break; }
  }
  const base = (data.tier_prices || {})[String(tier)] || 50;
  const curBid = data.current_bid || base;
  const curBidderName = curBidder ? curBidder.name : '';
  const maxBid = Math.min(curBid + 10, (data.budgets || {})[curBidderName] || 9999);

  document.getElementById('auctionLive').innerHTML = `
    <div class="auction-banner">
      <div class="auction-flag">${team ? team.flag : ''}</div>
      <div class="auction-team-name">${teamName}</div>
      <span class="tier-badge tier${tier}-badge">Tier ${tier} — ${base} rupees base</span>
      <div class="auction-bid-info">
        Current bid: <strong id="liveBidAmt">${curBid}</strong> rupees
        &nbsp;·&nbsp; Bidder: <strong id="liveBidder">${curBidderName}</strong>
      </div>
      <div class="auction-controls">
        <input type="number" id="bidAmount" value="${maxBid}" min="${base}" step="10"/>
        <button class="btn-primary" onclick="placeBid()">Place Bid ↗</button>
        <button class="btn-secondary" onclick="passOnTeam()">Pass</button>
        <button class="btn-outline" onclick="autoAssign()">Auto-assign All</button>
      </div>
      <div id="bidMsg"></div>
    </div>`;

  // Update team grid sold chips
  updateTeamGrid(data);
  updateBudgetList(data);
  addAuctionLog(data, teamName);
}

function addAuctionLog(data, lastTeam) {
  const log = document.getElementById('aucLog');
  if (!log) return;
  const entry = data.team_sold[lastTeam];
  if (entry) {
    const tm = (window.ALL_TEAMS || []).find(t => t.name === lastTeam);
    if (log.querySelector('.log-empty')) log.innerHTML = '';
    const div = document.createElement('div');
    div.className = 'log-item log-win';
    div.textContent = `${tm ? tm.flag : ''} ${lastTeam} → ${entry}`;
    log.prepend(div);
  }
}

function updateTeamGrid(data) {
  const grid = document.getElementById('teamGrid');
  if (!grid) return;
  let html = '';
  for (let t = 1; t <= 6; t++) {
    const price = (data.tier_prices || {})[String(t)] || 50;
    html += `<div class="sep-label">Tier ${t} — ${price} rupees base</div><div class="chip-group">`;
    const teams = (data.tiers || {})[String(t)] || [];
    teams.forEach(name => {
      const tm = (window.ALL_TEAMS || []).find(x => x.name === name);
      const owner = (data.team_sold || {})[name];
      html += `<span class="team-chip ${owner ? 'sold-chip' : `tier${t}-chip`}">
        ${tm ? tm.flag : ''} ${name}${owner ? ' ✓' : ''}
      </span>`;
    });
    html += '</div>';
  }
  grid.innerHTML = html;
}

function updateBudgetList(data) {
  const el = document.getElementById('budgetList');
  if (!el) return;
  const players = data.players || [];
  el.innerHTML = players.map((p, i) => {
    const owned = (data.ownership || {})[p.name] || [];
    const isCur = players.length > 0 && i === (data.current_bidder % players.length) && !data.auction_done;
    return `<div class="player-row">
      <div class="avatar av${i % 6}">${p.name[0]}</div>
      <div class="player-info">
        <div class="player-name">${p.name}${isCur ? ' <span class="bidding-badge">Bidding</span>' : ''}</div>
        <div class="player-teams muted">${owned.join(', ') || 'No teams yet'}</div>
      </div>
      <div class="player-budget">${(data.budgets || {})[p.name] ?? data.budget} rupees</div>
    </div>`;
  }).join('');
}

/* ── Matches ─────────────────────────────────────── */
async function submitMatch(useClaude) {
  const t1 = document.getElementById('matchTeam1').value;
  const t2 = document.getElementById('matchTeam2').value;
  const s1 = parseInt(document.getElementById('score1').value) || 0;
  const s2 = parseInt(document.getElementById('score2').value) || 0;
  const stage = document.getElementById('matchStage').value;
  const extra = document.getElementById('matchExtra').value || '';

  if (!t1 || !t2 || t1 === t2) {
    showMsg('matchMsg', 'Select two different teams.', true); return;
  }
  showLoading('matchMsg', useClaude ? 'Analysing match with Claude…' : 'Calculating rupees…');

  const r = await api('/api/match/add', {team1:t1, team2:t2, score1:s1, score2:s2, stage, extra, use_claude: useClaude});
  if (!r.ok) { showMsg('matchMsg', 'Something went wrong. Try again.', true); return; }

  const m = r.match;
  const o1 = m.owner1 || 'unowned', o2 = m.owner2 || 'unowned';
  const p1 = m.result.team1.rupees, p2 = m.result.team2.rupees;

  showMsg('matchMsg',
    `Points awarded! ${t1} (${o1}): ${p1>=0?'+':''}${p1} pts &nbsp;·&nbsp; ${t2} (${o2}): ${p2>=0?'+':''}${p2} pts` +
    ` &nbsp;<a href="/match/${m.id}" style="color:#0c447c">View full analysis →</a>`
  );

  // Prepend match card
  prependMatchCard(m);
}

function prependMatchCard(m) {
  const hist = document.getElementById('matchHistory');
  const empty = hist.querySelector('p');
  if (empty) empty.remove();

  const div = document.createElement('div');
  div.className = 'match-card';
  const p1 = m.result.team1.rupees, p2 = m.result.team2.rupees;
  div.innerHTML = `
    <div class="match-card-header">
      <span class="muted small">${m.timestamp}</span>
      <span class="stage-badge">${m.stage.toUpperCase()}</span>
    </div>
    <div class="match-scoreline">
      <div class="match-team-left">
        <span class="match-flag">${m.flag1}</span>
        <span class="match-name">${m.team1}</span>
        <span class="owner-tag muted">${m.owner1||'unowned'}</span>
      </div>
      <div class="match-score-box">${m.score1} – ${m.score2}</div>
      <div class="match-team-right">
        <span class="match-flag">${m.flag2}</span>
        <span class="match-name">${m.team2}</span>
        <span class="owner-tag muted">${m.owner2||'unowned'}</span>
      </div>
    </div>
    <div class="match-pts-row">
      <span class="pts-tag ${p1>=0?'pts-pos':'pts-neg'}">${p1>=0?'+':''}${p1} pts → ${m.owner1||'—'}</span>
      <a href="/match/${m.id}" class="detail-link">View analysis →</a>
      <span class="pts-tag ${p2>=0?'pts-pos':'pts-neg'}">${p2>=0?'+':''}${p2} pts → ${m.owner2||'—'}</span>
    </div>`;
  hist.prepend(div);
}
