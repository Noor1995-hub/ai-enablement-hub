// Shared render helpers for the prototypes. Everything renders from
// window.HUB (data.js). Session-only interaction state lives in MOCK_STATE so
// clicking around feels real; nothing persists.
/* global HUB */

window.MOCK_STATE = {
  fbStatus: {},        // feedback id -> overridden status
  matrix: {},          // "userId:itemId" -> overridden assign value ('yes' | '')
  selected: new Set(), // selected user ids in people tables
};

// ── tiny icon set (feather-style strokes) ─────────────────────────────────
const ICON_PATHS = {
  home:     '<path d="M3 9.5 12 3l9 6.5V21a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1z"/>',
  users:    '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  grid:     '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
  inbox:    '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  folder:   '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  search:   '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
  chevR:    '<path d="m9 18 6-6-6-6"/>',
  chevD:    '<path d="m6 9 6 6 6-6"/>',
  check:    '<path d="M20 6 9 17l-5-5"/>',
  alert:    '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  clock:    '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  mail:     '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
  plus:     '<path d="M12 5v14M5 12h14"/>',
  external: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6"/><path d="M10 14 21 3"/>',
  arrowL:   '<path d="M19 12H5M12 19l-7-7 7-7"/>',
  dots:     '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
  sparkle:  '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/>',
};
function icon(name, size = 16) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_PATHS[name] || ''}</svg>`;
}

// ── formatting helpers ───────────────────────────────────────────────────
const initials = n => n.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();
const projById = id => HUB.projects.find(p => p.id === id);
const companyOf = p => HUB.companies.find(c => c.id === p.companyId);
const usersOf = pid => HUB.users.filter(u => u.projectId === pid);
const trackById = id => HUB.tracks.find(t => t.id === id);
// Company-first labels: the company is what people recognize and navigate by;
// the project name is the qualifier (a company can run several projects).
const orgShort = p => companyOf(p).name;
const orgFull = p => `${companyOf(p).name} · ${p.name}`;

function lastActiveText(u) {
  if (u.lastActive === null) return '—';
  if (u.lastActive === 0) return 'today';
  if (u.lastActive === 1) return 'yesterday';
  return `${u.lastActive}d ago`;
}
function statusChip(u) {
  if (u.status === 'invited') return '<span class="chip neutral">Invited</span>';
  if (u.flags.length) return '<span class="chip warn">Needs attention</span>';
  return '<span class="chip good">Active</span>';
}
function levelBadge(code) {
  if (!code) return '<span class="subtext">Not assessed</span>';
  const l = HUB.levels[code];
  return `<span class="level-badge"><span class="swatch" style="background:${l.color}"></span>${l.name}</span>`;
}
function progressBar(pct) {
  return `<div class="progress"><div class="track"><div class="fill" style="width:${pct}%"></div></div><span class="pct">${pct}%</span></div>`;
}
function tile(label, value, { iconName = null, alert = false, delta = '' } = {}) {
  return `<div class="tile${alert ? ' alert' : ''}">
    <div class="label">${iconName ? icon(iconName, 14) : ''}${label}</div>
    <div class="value">${value}</div>
    ${delta ? `<div class="delta">${delta}</div>` : ''}
  </div>`;
}
function toast(msg) {
  let t = document.querySelector('.toast');
  if (!t) {
    t = document.createElement('div');
    t.className = 'toast';
    t.style.cssText = 'position:fixed;bottom:60px;left:50%;transform:translateX(-50%);background:#101820;color:#fff;font:600 13px "Work Sans",sans-serif;padding:10px 18px;border-radius:999px;z-index:100;box-shadow:0 10px 28px -8px rgba(16,24,32,.4)';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.display = 'block';
  clearTimeout(t._h);
  t._h = setTimeout(() => { t.style.display = 'none'; }, 1800);
}

// ── funnel (ordinal single-hue ramp, light→dark; labels carry the values) ─
const FUNNEL_RAMP = ['#EE9089', '#EA6A60', '#EF463C', '#C42828', '#941914'];
const FUNNEL_STAGES = [
  ['invited', 'Invited'], ['activated', 'Activated'], ['assessed', 'Assessed'],
  ['learning', 'Learning started'], ['completedTrack', 'Completed a track'],
];
function funnelHTML(f) {
  const max = f.invited || 1;
  let prev = null;
  return FUNNEL_STAGES.map(([key, label], i) => {
    const v = f[key];
    const conv = prev === null ? '' : ` · ${Math.round((v / (prev || 1)) * 100)}%`;
    prev = v;
    return `<div class="funnel-row">
      <div class="stage">${label}</div>
      <div class="bar-track"><div class="bar" style="width:${(v / max) * 100}%;background:${FUNNEL_RAMP[i]}"></div></div>
      <div class="meta"><b>${v}</b>${conv ? `<span>${conv}</span>` : ''}</div>
    </div>`;
  }).join('');
}

// ── maturity distribution (one labeled row per level — never a stacked bar,
//    the four brand colors fail adjacent-segment validation) ───────────────
function levelRowsHTML(maturity) {
  const entries = Object.entries(maturity);
  const max = Math.max(...entries.map(([, n]) => n), 1);
  return entries.map(([code, n]) => {
    const l = HUB.levels[code];
    return `<div class="level-row">
      <span class="level-badge"><span class="swatch" style="background:${l.color}"></span>${l.name}</span>
      <div class="bar-track"><div class="bar" style="width:${(n / max) * 100}%;background:${l.color}"></div></div>
      <span class="n">${n}</span>
    </div>`;
  }).join('');
}

// ── needs-attention list ─────────────────────────────────────────────────
function attentionRowsHTML(users, { showProject = false } = {}) {
  const flagged = users.filter(u => u.flags.length);
  if (!flagged.length) return '<div class="empty">Nobody needs a nudge right now.</div>';
  return `<div class="attn">` + flagged.map(u => {
    const p = projById(u.projectId);
    const why = u.stallNote
      || (u.flags.includes('never-started') ? 'Invited, never activated the account' : 'Assessment not started');
    return `<div class="attn-row">
      <span class="who">${u.name}</span>
      ${showProject ? `<span class="chip outline" title="${orgFull(p)}">${orgShort(p)}</span>` : ''}
      <span class="why">${why}</span>
      <span class="act">
        <button class="btn ghost sm" onclick="toast('Reminder email — not in this mock yet')">${icon('mail', 13)} Remind</button>
        <button class="btn subtle sm" onclick="toast('Jump to profile — not in this mock yet')">View</button>
      </span>
    </div>`;
  }).join('') + `</div>`;
}

// ── people table with multi-select + bulk bar ────────────────────────────
function peopleTableHTML(users, { showProject = false } = {}) {
  const rows = users.map(u => `
    <tr class="row${MOCK_STATE.selected.has(u.id) ? ' selected' : ''}" data-uid="${u.id}">
      <td style="width:34px"><input type="checkbox" data-sel="${u.id}" ${MOCK_STATE.selected.has(u.id) ? 'checked' : ''}></td>
      <td><div class="user-cell"><span class="avatar">${initials(u.name)}</span>
        <span><span class="name">${u.name}</span><br><span class="email">${u.email}</span></span></div></td>
      ${showProject ? `<td><span class="chip outline" title="${orgFull(projById(u.projectId))}">${orgShort(projById(u.projectId))}</span></td>` : ''}
      <td>${statusChip(u)}</td>
      <td>${levelBadge(u.level)}</td>
      <td>${u.status === 'invited' ? '<span class="subtext">—</span>' : progressBar(u.progress)}</td>
      <td><span class="subtext">${lastActiveText(u)}</span></td>
      <td><span class="chip ${u.role === 'admin' ? 'bad' : u.role === 'user+' ? 'info' : 'neutral'}">${u.role}</span></td>
      <td style="width:40px"><button class="btn subtle sm" onclick="toast('Row menu — not in this mock yet')">${icon('dots', 15)}</button></td>
    </tr>`).join('');
  return `<table class="data">
    <thead><tr>
      <th></th><th>Participant</th>${showProject ? '<th>Project</th>' : ''}<th>Status</th>
      <th>Maturity</th><th>Progress</th><th>Last active</th><th>Role</th><th></th>
    </tr></thead><tbody>${rows}</tbody></table>
    <div id="bulkbar-slot"></div>`;
}
function wirePeopleTable(container, rerender) {
  container.querySelectorAll('input[data-sel]').forEach(cb => {
    cb.addEventListener('change', () => {
      const id = cb.dataset.sel;
      cb.checked ? MOCK_STATE.selected.add(id) : MOCK_STATE.selected.delete(id);
      rerender();
    });
  });
  const slot = container.querySelector('#bulkbar-slot');
  const n = MOCK_STATE.selected.size;
  if (slot && n > 0) {
    slot.innerHTML = `<div class="bulkbar">
      <span class="sel">${n} selected</span>
      <button class="btn ghost sm" onclick="toast('Bulk assign — see the Assignments section')">${icon('grid', 13)} Assign content</button>
      <button class="btn ghost sm" onclick="toast('Bulk reminder — not in this mock yet')">${icon('mail', 13)} Send reminder</button>
      <button class="btn ghost sm" onclick="toast('Bulk role change — not in this mock yet')">Change role</button>
      <button class="close" title="Clear selection">✕</button>
    </div>`;
    slot.querySelector('.close').addEventListener('click', () => { MOCK_STATE.selected.clear(); rerender(); });
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// ASSIGNMENT MATRIX — self-contained component with track → module → lesson
// drill-down. mountMatrix(container, project, users) manages its own scope.
// ═══════════════════════════════════════════════════════════════════════════
const ovr = key => MOCK_STATE.matrix[key];

function trackState(u, tid) {
  const o = ovr(`${u.id}:${tid}`);
  return o !== undefined ? o : u.assign[tid];
}
function moduleState(u, track, mid) {
  const o = ovr(`${u.id}:${mid}`);
  if (o !== undefined) return o;
  const explicit = u.assignModules && u.assignModules[track.id] && u.assignModules[track.id][mid];
  if (explicit !== undefined) return explicit;
  const ts = trackState(u, track.id);
  return ts === 'part' ? '' : ts; // 'def' | 'yes' | ''
}
function lessonState(u, track, module, lid) {
  const o = ovr(`${u.id}:${lid}`);
  if (o !== undefined) return o;
  const explicit = u.assignLessons && u.assignLessons[module.id] && u.assignLessons[module.id][lid];
  if (explicit !== undefined) return explicit;
  const ms = moduleState(u, track, module.id);
  return ms === 'part' ? '' : ms;
}

const CELL_GLYPH = { yes: icon('check', 14), def: icon('check', 14), part: '◐', '': '' };
const CELL_TITLE = {
  yes: 'Assigned (explicit) — click to unassign',
  def: 'Assigned via project default — click to override',
  part: 'Partially assigned — drill in for detail, or click to assign all',
  '': 'Not assigned — click to assign',
};

function mountMatrix(container, project, users) {
  // scope: {level:'tracks'} | {level:'modules', trackId} | {level:'lessons', trackId, moduleId}
  // Navigation lives in an explicit content tree on the left (round-3 feedback:
  // drilling via column headers was too hidden); the breadcrumb stays in sync.
  let scope = { level: 'tracks' };

  function columns() {
    if (scope.level === 'tracks') return HUB.tracks.map(t => ({
      id: t.id, name: t.name, sub: HUB.levels[t.level],
      state: u => trackState(u, t.id),
      isDefault: project.defaults[t.id],
    }));
    const track = trackById(scope.trackId);
    if (scope.level === 'modules') return track.modules.map(m => ({
      id: m.id, name: m.name, sub: null,
      state: u => moduleState(u, track, m.id),
      isDefault: project.defaults[track.id],
    }));
    const module = track.modules.find(m => m.id === scope.moduleId);
    return module.lessons.map(l => ({
      id: l.id, name: l.name, sub: null,
      state: u => lessonState(u, track, module, l.id),
      isDefault: project.defaults[track.id],
    }));
  }

  function treeHTML() {
    const items = [`<button class="tree-item root${scope.level === 'tracks' ? ' active' : ''}" data-tree="tracks">${icon('grid', 14)} All tracks</button>`];
    HUB.tracks.forEach(t => {
      const lvl = HUB.levels[t.level];
      const open = scope.trackId === t.id;
      const trackActive = open && scope.level === 'modules';
      items.push(`<button class="tree-item${trackActive ? ' active' : ''}" data-tree="track:${t.id}">
        <span class="lvl-dot" style="background:${lvl.color}"></span>${t.name}
        <span class="tw-chev${open ? ' open' : ''}">${icon('chevR', 12)}</span></button>`);
      if (open) t.modules.forEach(m => {
        const modActive = scope.level === 'lessons' && scope.moduleId === m.id;
        items.push(`<button class="tree-item sub${modActive ? ' active' : ''}" data-tree="module:${t.id}:${m.id}">${m.name}</button>`);
      });
    });
    return `<nav class="content-tree">
      <div class="tree-title">Content scope</div>
      ${items.join('')}
      <div class="tree-foot">Pick a track for its modules,<br>a module for its lessons.</div>
    </nav>`;
  }

  function crumbHTML() {
    const track = scope.trackId && trackById(scope.trackId);
    const module = scope.level === 'lessons' && track.modules.find(m => m.id === scope.moduleId);
    const parts = [`<button class="crumb${scope.level === 'tracks' ? ' here' : ''}" data-crumb="tracks">All tracks</button>`];
    if (track) parts.push(`<button class="crumb${scope.level === 'modules' ? ' here' : ''}" data-crumb="modules">${track.name}</button>`);
    if (module) parts.push(`<span class="crumb here">${module.name}</span>`);
    const hint = scope.level === 'tracks' ? 'track-level assignment'
      : scope.level === 'modules' ? `modules of ${track.name}`
      : 'lesson-level assignment';
    return `<div class="matrix-nav">${parts.join(`<span class="sep">${icon('chevR', 13)}</span>`)}<span class="hint">${hint}</span></div>`;
  }

  function draw() {
    const cols = columns();
    const head = cols.map(c => {
      const sub = c.sub && c.sub.name !== c.name
        ? `<span class="lvl"><span class="lvl-dot" style="background:${c.sub.color}"></span>${c.sub.name}</span>` : '';
      return `<th>${c.name}${sub}</th>`;
    }).join('');

    const defaults = cols.map(c =>
      `<td><button class="cell ${c.isDefault ? 'yes' : ''}" title="Project default — new participants inherit this" onclick="toast('Toggling a project default — not wired in this mock')">${c.isDefault ? icon('check', 14) : ''}</button></td>`).join('');

    const body = users.map(u => `<tr>
      <td class="rowhead"><div class="user-cell"><span class="avatar">${initials(u.name)}</span><span class="name">${u.name}</span></div></td>
      ${cols.map(c => {
        const st = c.state(u);
        return `<td><button class="cell ${st}" data-cell="${u.id}:${c.id}" title="${CELL_TITLE[st]}">${CELL_GLYPH[st]}</button></td>`;
      }).join('')}
    </tr>`).join('');

    container.innerHTML = `
      <div class="assign-layout">
        ${treeHTML()}
        <div class="matrix-side">
          ${crumbHTML()}
          <div class="matrix-wrap"><table class="matrix">
            <thead><tr><th class="rowhead">Participant</th>${head}</tr></thead>
            <tbody>
              <tr class="defaults-row"><td class="rowhead">Project defaults<br><span class="subtext" style="font-weight:400">new participants inherit these</span></td>${defaults}</tr>
              ${body}
            </tbody></table></div>
          <div class="section-gap"></div>
          <div class="legend">
            <span><button class="cell yes">${icon('check', 14)}</button> assigned</span>
            <span><button class="cell def">${icon('check', 14)}</button> via project default</span>
            <span><button class="cell part">◐</button> partial — narrow the scope for detail</span>
            <span><button class="cell"></button> not assigned</span>
            <span style="margin-left:auto">Click a cell to toggle</span>
          </div>
        </div>
      </div>`;

    container.querySelectorAll('button[data-cell]').forEach(btn => {
      btn.addEventListener('click', () => {
        const key = btn.dataset.cell;
        const [uid, itemId] = key.split(':');
        const u = HUB.users.find(x => x.id === uid);
        const col = cols.find(c => c.id === itemId);
        const cur = col.state(u);
        MOCK_STATE.matrix[key] = (cur === '' || cur === 'part') ? 'yes' : '';
        draw();
      });
    });
    container.querySelectorAll('button[data-tree]').forEach(btn => {
      btn.addEventListener('click', () => {
        const parts = btn.dataset.tree.split(':');
        if (parts[0] === 'tracks') scope = { level: 'tracks' };
        else if (parts[0] === 'track') scope = { level: 'modules', trackId: parts[1] };
        else scope = { level: 'lessons', trackId: parts[1], moduleId: parts[2] };
        draw();
      });
    });
    container.querySelectorAll('button[data-crumb]').forEach(btn => {
      btn.addEventListener('click', () => {
        scope = btn.dataset.crumb === 'tracks'
          ? { level: 'tracks' }
          : { level: 'modules', trackId: scope.trackId };
        draw();
      });
    });
  }
  draw();
}

// ═══════════════════════════════════════════════════════════════════════════
// FEEDBACK QUEUE — self-contained component with status pills + track/type
// filters and structured track › module › lesson location on every card.
// mountFeedback(container, items, {showProject}).
// ═══════════════════════════════════════════════════════════════════════════
function fbStatus(f) { return MOCK_STATE.fbStatus[f.id] || f.status; }
function fbCounts(items) {
  const c = { new: 0, accepted: 0, dismissed: 0 };
  items.forEach(f => { c[fbStatus(f)]++; });
  return c;
}
function locParts(f) {
  const track = trackById(f.loc.track);
  const module = track.modules.find(m => m.id === f.loc.module);
  const lesson = module.lessons.find(l => l.id === f.loc.lesson);
  return { track, module, lesson };
}

function mountFeedback(container, items, { showProject = false } = {}) {
  const filter = { status: 'new', track: 'all', type: 'all' };
  const types = ['Content error', 'Suggestion', 'Unclear'];
  const tracksInData = HUB.tracks.filter(t => items.some(f => f.loc.track === t.id));

  function shownItems() {
    return items.filter(f =>
      (filter.status === 'all' || fbStatus(f) === filter.status)
      && (filter.track === 'all' || f.loc.track === filter.track)
      && (filter.type === 'all' || f.type === filter.type));
  }

  function cardHTML(f) {
    const st = fbStatus(f);
    const done = st !== 'new';
    const { track, module, lesson } = locParts(f);
    const lvl = HUB.levels[track.level];
    return `<div class="fb-card${done ? ' done' : ''}">
      <div class="fb-head">
        <span class="user-cell"><span class="avatar">${initials(f.user)}</span>
          <span><span class="name">${f.user}</span>${showProject ? `<br><span class="email" title="${orgFull(projById(f.projectId))}">${orgShort(projById(f.projectId))}</span>` : ''}</span></span>
        <span class="chip ${f.type === 'Content error' ? 'bad' : f.type === 'Suggestion' ? 'info' : 'warn'}">${f.type}</span>
        ${done ? `<span class="chip ${st === 'accepted' ? 'good' : 'neutral'}">${st}</span>` : ''}
        <span class="when">${f.date}</span>
      </div>
      <div class="fb-loc">
        <button class="loc-chip track" data-loc-track="${track.id}" title="Filter on this track">
          <span class="loc-label">Track</span><span class="lvl-dot" style="background:${lvl.color}"></span>${track.name}</button>
        <span class="loc-chip"><span class="loc-label">Module</span>${module.name}</span>
        <span class="loc-chip"><span class="loc-label">Lesson</span>${lesson.name}</span>
        <button class="btn subtle sm" style="margin-left:2px" onclick="toast('Opens the lesson in the learner app')">${icon('external', 12)} open lesson</button>
      </div>
      <p class="fb-quote">“${f.quote}”</p>
      <div class="fb-foot">
        <div class="ai-box">
          <span class="ai-tag">${icon('sparkle', 12)} AI triage</span>
          <span class="metric">Feasibility <b>${f.ai.feasibility}</b></span>
          <span class="metric">Rework effort <b>${f.ai.effort}</b></span>
          <span class="note">${f.ai.note}</span>
        </div>
        ${st === 'new' ? `<div class="fb-actions">
          <button class="btn ghost sm" data-fb-dismiss="${f.id}">Dismiss</button>
          <button class="btn primary sm" data-fb-accept="${f.id}">${icon('check', 13)} Accept</button>
        </div>` : ''}
      </div>
    </div>`;
  }

  function draw() {
    const counts = fbCounts(items);
    const shown = shownItems();
    const trackOpts = [`<option value="all">All tracks</option>`]
      .concat(tracksInData.map(t => `<option value="${t.id}"${filter.track === t.id ? ' selected' : ''}>${t.name}</option>`));
    const typeOpts = [`<option value="all">All types</option>`]
      .concat(types.map(t => `<option value="${t}"${filter.type === t ? ' selected' : ''}>${t}</option>`));

    container.innerHTML = `
      <div class="toolbar">
        <div class="pills" id="fb-pills">
          <button class="pill${filter.status === 'new' ? ' active' : ''}" data-f="new">New <span class="n">${counts.new}</span></button>
          <button class="pill${filter.status === 'accepted' ? ' active' : ''}" data-f="accepted">Accepted <span class="n">${counts.accepted}</span></button>
          <button class="pill${filter.status === 'dismissed' ? ' active' : ''}" data-f="dismissed">Dismissed <span class="n">${counts.dismissed}</span></button>
          <button class="pill${filter.status === 'all' ? ' active' : ''}" data-f="all">All</button>
        </div>
      </div>
      <div class="toolbar filter-row">
        <span class="filter-label">${icon('search', 12)} Filter</span>
        <span class="select-look">${icon('grid', 13)}<select id="fb-track" style="border:none;outline:none;background:none;font:inherit;color:inherit">${trackOpts.join('')}</select></span>
        <span class="select-look"><select id="fb-type" style="border:none;outline:none;background:none;font:inherit;color:inherit">${typeOpts.join('')}</select></span>
        <span class="subtext" style="margin-left:auto">${shown.length} item${shown.length === 1 ? '' : 's'}</span>
      </div>
      ${shown.length ? shown.map(cardHTML).join('') : '<div class="empty">Nothing matches these filters.</div>'}`;

    container.querySelectorAll('#fb-pills .pill').forEach(pb =>
      pb.addEventListener('click', () => { filter.status = pb.dataset.f; draw(); }));
    const trackSel = container.querySelector('#fb-track');
    trackSel.addEventListener('change', () => { filter.track = trackSel.value; draw(); });
    const typeSel = container.querySelector('#fb-type');
    typeSel.addEventListener('change', () => { filter.type = typeSel.value; draw(); });
    container.querySelectorAll('[data-loc-track]').forEach(b =>
      b.addEventListener('click', () => { filter.track = b.dataset.locTrack; draw(); }));
    container.querySelectorAll('[data-fb-accept]').forEach(b =>
      b.addEventListener('click', () => { MOCK_STATE.fbStatus[b.dataset.fbAccept] = 'accepted'; toast('Accepted — lands on the content backlog'); draw(); }));
    container.querySelectorAll('[data-fb-dismiss]').forEach(b =>
      b.addEventListener('click', () => { MOCK_STATE.fbStatus[b.dataset.fbDismiss] = 'dismissed'; draw(); }));
  }
  draw();
}

// ── assessment rung pills (palette mirrors the live app's adminHelpers) ──
const RUNGS = [
  { label: 'Not yet',  bg: '#F5F5F5', text: '#8A8A8A' },
  { label: 'Partial',  bg: '#EEF2FF', text: '#4B5CC4' },
  { label: 'Has it',   bg: '#FFF8EC', text: '#B45309' },
  { label: 'Advanced', bg: '#EDFAF4', text: '#1D7A52' },
];
function rungPill(i) {
  const r = RUNGS[i];
  return `<span class="chip" style="background:${r.bg};color:${r.text}">${r.label}</span>`;
}

// ── settings pieces ──────────────────────────────────────────────────────
function componentsHTML(project) {
  return project.components.map(c => `
    <div class="comp-row">
      <span class="name">${c.label}</span>
      <span class="toggle"><button class="switch ${c.visible ? 'on' : ''}" onclick="toast('Toggling visibility — not wired in this mock')"></button> visible to learners</span>
      <span class="toggle"><button class="switch ${!c.locked ? 'on' : ''}" onclick="toast('Toggling lock — not wired in this mock')"></button> unlocked</span>
      <span class="subtext" style="margin-left:auto">${c.visible ? (c.locked ? 'Shown as locked tile' : 'Fully available') : 'Hidden from journey page'}</span>
    </div>`).join('');
}
