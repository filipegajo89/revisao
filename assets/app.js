/* ============================================================
   Revisão Ativa — Auth + Highlights + Notes (Supabase)
   ============================================================ */

// ---------- Supabase client ----------
let supabase = null;
let currentUser = null;
const PAGE_KEY = location.pathname;

function initSupabase() {
  if (typeof SUPABASE_URL === 'undefined' || SUPABASE_URL.includes('SEU-PROJETO')) {
    console.warn('Supabase not configured — running in local-only mode');
    return false;
  }
  const { createClient } = window.supabase;
  supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  return true;
}

// ---------- Auth ----------
async function checkAuth() {
  if (!supabase) { showContent(); return; }
  const { data: { session } } = await supabase.auth.getSession();
  if (session) {
    currentUser = session.user;
    showContent();
    loadAnnotations();
  } else {
    showLogin();
  }
}

function showLogin() {
  document.getElementById('auth-gate').style.display = 'flex';
  document.getElementById('main-content').style.display = 'none';
}

function showContent() {
  const gate = document.getElementById('auth-gate');
  if (gate) gate.style.display = 'none';
  document.getElementById('main-content').style.display = 'block';
  initHighlighter();
  initNotes();
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value;
  const pass = document.getElementById('login-pass').value;
  const errEl = document.getElementById('login-error');
  errEl.textContent = '';

  const { data, error } = await supabase.auth.signInWithPassword({ email, password: pass });
  if (error) {
    errEl.textContent = 'Email ou senha incorretos.';
    return;
  }
  currentUser = data.user;
  showContent();
  loadAnnotations();
}

async function handleLogout() {
  if (supabase) await supabase.auth.signOut();
  currentUser = null;
  showLogin();
}

// ---------- Highlights ----------
let highlighterActive = false;
const COLORS = ['#ffe066', '#a8e6cf', '#ff8b94', '#c3aed6'];
let selectedColor = COLORS[0];

function initHighlighter() {
  // Toolbar
  const toolbar = document.createElement('div');
  toolbar.id = 'hl-toolbar';
  toolbar.innerHTML = `
    <div class="hl-bar">
      ${COLORS.map((c, i) => `<button class="hl-color${i === 0 ? ' active' : ''}" data-color="${c}" style="background:${c}" title="Cor ${i + 1}"></button>`).join('')}
      <button class="hl-eraser" title="Borracha">&#9986;</button>
      <span class="hl-sep">|</span>
      <button class="hl-close" title="Fechar">&times;</button>
    </div>`;
  document.body.appendChild(toolbar);

  // Toggle button
  const toggleBtn = document.createElement('button');
  toggleBtn.id = 'hl-toggle';
  toggleBtn.innerHTML = '&#9998;';
  toggleBtn.title = 'Marca-texto';
  toggleBtn.onclick = () => toggleHighlighter();
  document.body.appendChild(toggleBtn);

  // Color selection
  toolbar.querySelectorAll('.hl-color').forEach(btn => {
    btn.onclick = () => {
      selectedColor = btn.dataset.color;
      toolbar.querySelectorAll('.hl-color').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    };
  });

  // Eraser
  toolbar.querySelector('.hl-eraser').onclick = () => {
    selectedColor = null;
    toolbar.querySelectorAll('.hl-color').forEach(b => b.classList.remove('active'));
  };

  toolbar.querySelector('.hl-close').onclick = () => toggleHighlighter(false);

  // Mouseup handler for highlighting
  document.addEventListener('mouseup', onTextSelected);
}

function toggleHighlighter(force) {
  highlighterActive = force !== undefined ? force : !highlighterActive;
  document.getElementById('hl-toolbar').classList.toggle('visible', highlighterActive);
  document.getElementById('hl-toggle').classList.toggle('active', highlighterActive);
  document.body.classList.toggle('hl-mode', highlighterActive);
}

function onTextSelected() {
  if (!highlighterActive) return;
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || !sel.toString().trim()) return;

  const range = sel.getRangeAt(0);
  // Only highlight inside main-content
  const main = document.getElementById('main-content');
  if (!main.contains(range.commonAncestorContainer)) return;

  if (selectedColor === null) {
    // Eraser mode — remove highlights in selection
    removeHighlightsInRange(range);
  } else {
    applyHighlight(range, selectedColor);
  }
  sel.removeAllRanges();
  saveHighlights();
}

function applyHighlight(range, color) {
  // Handle case where selection spans multiple elements
  const mark = document.createElement('mark');
  mark.className = 'user-hl';
  mark.style.backgroundColor = color;
  mark.style.padding = '0 1px';
  mark.style.borderRadius = '2px';
  try {
    range.surroundContents(mark);
  } catch (e) {
    // If surroundContents fails (spans multiple elements), use extractContents
    const fragment = range.extractContents();
    mark.appendChild(fragment);
    range.insertNode(mark);
  }
}

function removeHighlightsInRange(range) {
  const marks = document.querySelectorAll('#main-content mark.user-hl');
  marks.forEach(m => {
    if (range.intersectsNode(m)) {
      const parent = m.parentNode;
      while (m.firstChild) parent.insertBefore(m.firstChild, m);
      parent.removeChild(m);
      parent.normalize();
    }
  });
}

// ---------- Notes ----------
function initNotes() {
  // Add note button to each topic section
  document.querySelectorAll('.topic').forEach(topic => {
    if (topic.querySelector('.note-area')) return; // already exists
    const topicName = topic.querySelector('h2')?.textContent?.trim() || topic.id;
    const noteArea = document.createElement('div');
    noteArea.className = 'note-area';
    noteArea.innerHTML = `
      <button class="note-toggle" onclick="this.parentElement.classList.toggle('open')">
        &#128221; Minhas Anotações
      </button>
      <div class="note-content">
        <textarea class="note-text" data-topic="${topicName}" placeholder="Escreva suas anotações aqui..." oninput="debounceSaveNotes()"></textarea>
      </div>`;
    // Insert after the topic header area
    const header = topic.querySelector('.topic-header') || topic.querySelector('h2');
    if (header) header.after(noteArea);
    else topic.prepend(noteArea);
  });
}

let saveNotesTimer = null;
function debounceSaveNotes() {
  clearTimeout(saveNotesTimer);
  saveNotesTimer = setTimeout(saveNotes, 1500);
}

// ---------- Persistence ----------
async function saveHighlights() {
  const main = document.getElementById('main-content');
  const highlights = [];
  main.querySelectorAll('mark.user-hl').forEach(m => {
    highlights.push({
      text: m.textContent,
      color: m.style.backgroundColor,
      // Simple position: parent id + text offset
      parentId: findParentId(m),
      context: (m.previousSibling?.textContent || '').slice(-30) + '|||' + (m.nextSibling?.textContent || '').slice(0, 30)
    });
  });

  const payload = { highlights };

  if (supabase && currentUser) {
    await supabase.from('annotations').upsert({
      user_id: currentUser.id,
      page_url: PAGE_KEY,
      type: 'highlights',
      content: JSON.stringify(payload)
    }, { onConflict: 'user_id,page_url,type' });
  }
  // Always save to localStorage as cache
  localStorage.setItem(`hl_${PAGE_KEY}`, JSON.stringify(payload));
}

async function saveNotes() {
  const notes = {};
  document.querySelectorAll('.note-text').forEach(ta => {
    if (ta.value.trim()) notes[ta.dataset.topic] = ta.value;
  });

  if (supabase && currentUser) {
    await supabase.from('annotations').upsert({
      user_id: currentUser.id,
      page_url: PAGE_KEY,
      type: 'notes',
      content: JSON.stringify(notes)
    }, { onConflict: 'user_id,page_url,type' });
  }
  localStorage.setItem(`notes_${PAGE_KEY}`, JSON.stringify(notes));
}

async function loadAnnotations() {
  let hlData = null;
  let notesData = null;

  if (supabase && currentUser) {
    const { data } = await supabase
      .from('annotations')
      .select('type, content')
      .eq('user_id', currentUser.id)
      .eq('page_url', PAGE_KEY);

    if (data) {
      data.forEach(row => {
        if (row.type === 'highlights') hlData = JSON.parse(row.content);
        if (row.type === 'notes') notesData = JSON.parse(row.content);
      });
    }
  }

  // Fallback to localStorage
  if (!hlData) {
    const local = localStorage.getItem(`hl_${PAGE_KEY}`);
    if (local) hlData = JSON.parse(local);
  }
  if (!notesData) {
    const local = localStorage.getItem(`notes_${PAGE_KEY}`);
    if (local) notesData = JSON.parse(local);
  }

  if (hlData) restoreHighlights(hlData);
  if (notesData) restoreNotes(notesData);
}

function restoreHighlights(data) {
  if (!data.highlights || !data.highlights.length) return;
  const main = document.getElementById('main-content');
  const walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT);
  const textNodes = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode);

  data.highlights.forEach(hl => {
    for (const node of textNodes) {
      const idx = node.textContent.indexOf(hl.text);
      if (idx !== -1) {
        const range = document.createRange();
        range.setStart(node, idx);
        range.setEnd(node, idx + hl.text.length);
        const mark = document.createElement('mark');
        mark.className = 'user-hl';
        mark.style.backgroundColor = hl.color;
        mark.style.padding = '0 1px';
        mark.style.borderRadius = '2px';
        try {
          range.surroundContents(mark);
        } catch (e) { /* skip if can't restore */ }
        break;
      }
    }
  });
}

function restoreNotes(data) {
  Object.entries(data).forEach(([topic, text]) => {
    const ta = document.querySelector(`.note-text[data-topic="${topic}"]`);
    if (ta) {
      ta.value = text;
      ta.closest('.note-area')?.classList.add('has-content');
    }
  });
}

function findParentId(el) {
  let p = el.parentElement;
  while (p && !p.id && p.id !== 'main-content') p = p.parentElement;
  return p?.id || '';
}

// ---------- Init ----------
document.addEventListener('DOMContentLoaded', () => {
  const supaOk = initSupabase();
  if (supaOk) {
    checkAuth();
    // Login form handler
    const form = document.getElementById('login-form');
    if (form) form.addEventListener('submit', handleLogin);
  } else {
    showContent();
    // Load from localStorage in offline mode
    const hlLocal = localStorage.getItem(`hl_${PAGE_KEY}`);
    if (hlLocal) restoreHighlights(JSON.parse(hlLocal));
    const notesLocal = localStorage.getItem(`notes_${PAGE_KEY}`);
    if (notesLocal) restoreNotes(JSON.parse(notesLocal));
  }
});
