#!/usr/bin/env python3
"""
Generates a visual summary HTML from review_content.json for the web (with Supabase auth).

Applies the Pareto principle: topics covering 80% of total questions
get rich treatment (analogies, mnemonics, opposing concepts).
All other topics get a complete but standard summary.

Wraps the entire resumo in a Supabase auth gate (same pattern as gerar_html_web.py).

Usage:
    python gerar_resumo_web.py <review_json> <output_html> <aula> <materia> <total_questions>

Output goes to revisao-site/materias/<materia-slug>/resumo-aula-XX.html
"""

import sys
import json
import re
from typing import Dict, Any, Set


def esc(t: str) -> str:
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def bold(t: str) -> str:
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)

def nl2br(t: str) -> str:
    return t.replace('\n', '<br>')


def compute_pareto_topics(data: Dict[str, Any]) -> Set[str]:
    """Return set of topic names that cover 80% of total questions."""
    sorted_topics = sorted(data.items(), key=lambda x: x[1].get('total_questions', 0), reverse=True)
    total_q = sum(v.get('total_questions', 0) for _, v in sorted_topics)
    if total_q == 0:
        return set()
    threshold = total_q * 0.8
    cumulative = 0
    pareto = set()
    for name, td in sorted_topics:
        cumulative += td.get('total_questions', 0)
        pareto.add(name)
        if cumulative >= threshold:
            break
    return pareto


# Resumo CSS (dark theme with Pareto badges, analogias, mnemonics, conceitos_opostos, collapsible sections)
RESUMO_CSS = r'''
:root{--bg:#0c0e13;--bg2:#13161e;--bg3:#1a1e2a;--accent:#f59e0b;--accent-soft:rgba(245,158,11,.1);--green:#34d399;--green-soft:rgba(52,211,153,.08);--blue:#60a5fa;--blue-soft:rgba(96,165,250,.08);--red:#f87171;--red-soft:rgba(248,113,113,.07);--purple:#a78bfa;--purple-soft:rgba(167,139,250,.08);--text:#e4e6ec;--dim:#8a8fa4;--faint:#4e5268;--border:#252937;--r:14px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);line-height:1.8;padding:2.5rem 1.2rem}
.wrap{max-width:720px;margin:0 auto}
header{text-align:center;margin-bottom:2.5rem}
.badge{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:.62rem;text-transform:uppercase;letter-spacing:3px;color:var(--accent);background:var(--accent-soft);padding:5px 16px;border-radius:20px;margin-bottom:1rem}
header h1{font-family:'DM Serif Display',serif;font-size:2rem;font-weight:400;line-height:1.3;margin-bottom:.4rem}
header .sub{color:var(--dim);font-size:.9rem}
.stats{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-bottom:2rem}
.st{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:10px 16px;font-size:.8rem;text-align:center}
.st strong{color:var(--accent);font-size:1.2rem;display:block}
.sec{margin-bottom:2.5rem}
.sec-tag{font-family:'JetBrains Mono',monospace;font-size:.6rem;text-transform:uppercase;letter-spacing:3px;color:var(--faint);margin-bottom:.6rem}
.sec h2{font-family:'DM Serif Display',serif;font-size:1.3rem;font-weight:400;margin-bottom:1rem}
hr.div{border:none;height:1px;background:var(--border);margin:2rem 0}

/* TOPIC CARD */
.tc{background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);padding:1.5rem;margin-bottom:1.5rem;transition:border-color .2s}
.tc.pareto{border-color:rgba(245,158,11,.25)}
.tc-hdr{display:flex;align-items:center;margin-bottom:.8rem;flex-wrap:wrap;gap:8px}
.rk{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:var(--accent);color:#000;font-weight:700;font-size:.8rem;flex-shrink:0}
.tn{font-weight:700;font-size:1.05rem;flex:1}
.pareto-badge{display:inline-flex;align-items:center;gap:4px;font-family:'JetBrains Mono',monospace;font-size:.6rem;text-transform:uppercase;letter-spacing:2px;color:var(--accent);background:var(--accent-soft);padding:4px 12px;border-radius:20px;flex-shrink:0}
.tc-meta{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:1rem}
.mt{font-size:.68rem;padding:3px 10px;border-radius:20px;background:var(--bg3);color:var(--dim);font-family:'JetBrains Mono',monospace}
.mt.ceb{border:1px solid rgba(96,165,250,.3);color:var(--blue)}
.mt.ot{border:1px solid rgba(245,158,11,.3);color:var(--accent)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:1rem}
.ch{font-size:.73rem;padding:4px 12px;border-radius:20px;background:var(--bg3);color:var(--dim);border:1px solid var(--border)}

/* ANALOGIA */
.an{background:var(--bg2);border-radius:var(--r);padding:1.3rem;margin-bottom:1rem;border:1px solid var(--border)}
.an .icon{font-size:1.6rem;margin-bottom:.4rem}
.an p{font-size:.9rem;color:var(--dim);line-height:1.75}
.an p strong{color:var(--text);font-weight:600}

/* MNEMONIC */
.mn{background:var(--bg3);border:1px dashed var(--accent);border-radius:var(--r);padding:1rem 1.3rem;margin-bottom:1rem;text-align:center}
.mn .ms{font-family:'JetBrains Mono',monospace;font-size:.95rem;color:var(--accent);font-weight:600;letter-spacing:1px}
.mn .me{font-size:.8rem;color:var(--dim);margin-top:.3rem}

/* PAIR */
.pair{display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin-bottom:1rem}
.bx{padding:1.1rem;border-radius:var(--r);border:1px solid var(--border)}
.bx.g{background:var(--green-soft);border-color:rgba(52,211,153,.15)}
.bx.b{background:var(--blue-soft);border-color:rgba(96,165,250,.15)}
.bx .bl{font-family:'JetBrains Mono',monospace;font-size:.6rem;text-transform:uppercase;letter-spacing:2px;margin-bottom:.4rem}
.bx.g .bl{color:var(--green)}
.bx.b .bl{color:var(--blue)}
.bx .bt{font-weight:700;font-size:.95rem;margin-bottom:.3rem}
.bx p{font-size:.85rem;color:var(--dim);line-height:1.7}
.bx p strong{color:var(--text);font-weight:600}

/* RESUMO & PEGADINHAS */
.rt{font-size:.9rem;line-height:1.8;color:var(--dim);margin-bottom:1rem}
.rt strong{color:var(--text);font-weight:600}
.pg{background:var(--red-soft);border-left:3px solid var(--red);padding:.8rem 1rem;margin-bottom:.6rem;border-radius:0 8px 8px 0;font-size:.85rem;color:var(--dim);line-height:1.7}
.pg::before{content:"⚠ ";color:var(--red);font-weight:700}
.pl{font-family:'JetBrains Mono',monospace;font-size:.6rem;text-transform:uppercase;letter-spacing:2px;color:var(--red);margin-bottom:.5rem;margin-top:1rem}

/* COLLAPSE */
.cb{width:100%;text-align:left;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:10px 16px;border-radius:8px;cursor:pointer;font-family:'DM Sans',sans-serif;font-size:.88rem;display:flex;align-items:center;gap:8px;transition:border-color .2s;margin-top:.5rem}
.cb:hover{border-color:var(--accent)}
.cb .ar{transition:transform .2s;color:var(--accent);font-size:.75rem}
.cb.open .ar{transform:rotate(90deg)}
.cbd{display:none;padding:1rem 0 0;animation:fi .25s ease}
.cbd.show{display:block}
@keyframes fi{from{opacity:0}to{opacity:1}}

/* PARETO INFO */
.pareto-info{background:var(--accent-soft);border:1px solid rgba(245,158,11,.15);border-radius:var(--r);padding:1.2rem 1.5rem;margin-bottom:2rem;font-size:.88rem;color:var(--dim);line-height:1.7}
.pareto-info strong{color:var(--accent)}

footer{text-align:center;margin-top:2rem;color:var(--faint);font-size:.72rem;font-family:'JetBrains Mono',monospace}

/* Auth gate */
#auth-gate{display:none;position:fixed;inset:0;z-index:9999;background:var(--bg);justify-content:center;align-items:center;flex-direction:column}
.login-box{background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);padding:40px 36px;max-width:380px;width:90%;text-align:center}
.login-box h1{font-size:1.4rem;margin-bottom:6px}
.login-box .subtitle{color:var(--dim);font-size:.85rem;margin-bottom:28px}
.login-box input{display:block;width:100%;padding:10px 14px;margin-bottom:12px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:.95rem;font-family:inherit}
.login-box input:focus{outline:none;border-color:var(--accent)}
.login-box button[type=submit]{width:100%;padding:10px;background:#238636;color:#fff;border:none;border-radius:6px;font-size:.95rem;font-weight:600;cursor:pointer;margin-top:4px}
.login-box button[type=submit]:hover{background:#2ea043}
#login-error{color:#f87171;font-size:.85rem;margin-top:10px;min-height:1.2em}

.top-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem}
#logout-btn{background:var(--bg2);border:1px solid var(--border);color:var(--dim);padding:6px 14px;border-radius:6px;font-size:.75rem;cursor:pointer;font-family:inherit}
#logout-btn:hover{border-color:var(--red);color:var(--red)}

@media(max-width:580px){
  header h1{font-size:1.5rem}
  body{padding:1.5rem .8rem}
  .pair{grid-template-columns:1fr}
  .tc-hdr{flex-direction:column;align-items:flex-start}
}
'''


def build_analogia(a: Dict) -> str:
    icon = a.get('icon', '💡')
    texto = bold(esc(a.get('texto', '')))
    return f'<div class="an"><div class="icon">{icon}</div><p>{texto}</p></div>'

def build_mnemonico(m: Dict) -> str:
    return f'<div class="mn"><div class="ms">{esc(m.get("sigla",""))}</div><div class="me">{esc(m.get("explicacao",""))}</div></div>'

def build_par(p: Dict) -> str:
    la, ta, da = esc(p.get('label_a','')), esc(p.get('titulo_a','')), bold(esc(p.get('desc_a','')))
    lb, tb, db = esc(p.get('label_b','')), esc(p.get('titulo_b','')), bold(esc(p.get('desc_b','')))
    return f'''<div class="pair">
<div class="bx g"><div class="bl">{la}</div><div class="bt">{ta}</div><p>{da}</p></div>
<div class="bx b"><div class="bl">{lb}</div><div class="bt">{tb}</div><p>{db}</p></div>
</div>'''


def build_topic(name: str, td: Dict, is_pareto: bool) -> str:
    rank = td['rank']
    total = td.get('total_questions', 0)
    ceb = td.get('cebraspe', 0)
    subtopics = td.get('subtopics', [])
    resumo = td.get('resumo', '')
    pegadinhas = td.get('pegadinhas', [])
    analogia = td.get('analogia')
    mnemonicos = td.get('mnemonicos', [])
    conceitos_opostos = td.get('conceitos_opostos', [])

    # Meta badges
    meta = f'<span class="mt">{total}q</span>'
    if ceb > 0:
        meta += f'<span class="mt ceb">CEBRASPE {ceb}</span>'
    for bk in ['fgv', 'fcc', 'vunesp']:
        v = td.get(bk, 0)
        if v > 0:
            meta += f'<span class="mt ot">{bk.upper()} {v}</span>'

    chips = ''.join(f'<span class="ch">{esc(s)}</span>' for s in subtopics)

    # Pareto badge
    pareto_html = '<span class="pareto-badge">⭐ Personalizado</span>' if is_pareto else ''
    card_class = 'tc pareto' if is_pareto else 'tc'

    # Rich content
    rich = ''
    has_rich = is_pareto and (analogia or mnemonicos or conceitos_opostos)
    if has_rich:
        if analogia:
            rich += build_analogia(analogia)
        for p in conceitos_opostos:
            rich += build_par(p)
        for m in mnemonicos:
            rich += build_mnemonico(m)

    # Resumo + pegadinhas
    resumo_html = nl2br(bold(esc(resumo)))
    pegs = ''
    if pegadinhas:
        pegs = '<div class="pl">Pegadinhas da banca</div>'
        for p in pegadinhas:
            pegs += f'<div class="pg">{esc(p)}</div>'

    # Layout depends on whether rich content exists
    if has_rich:
        body = f'''{rich}
<button class="cb" onclick="tgl(this)"><span class="ar">▶</span> Resumo completo + Pegadinhas</button>
<div class="cbd"><div class="rt">{resumo_html}</div>{pegs}</div>'''
    else:
        body = f'''<button class="cb" onclick="tgl(this)"><span class="ar">▶</span> Ver resumo e pegadinhas</button>
<div class="cbd"><div class="rt">{resumo_html}</div>{pegs}</div>'''

    return f'''<div class="{card_class}">
<div class="tc-hdr"><span class="rk">{rank}</span><span class="tn">{esc(name)}</span>{pareto_html}</div>
<div class="tc-meta">{meta}</div>
<div class="chips">{chips}</div>
{body}
</div>'''


def generate(data: Dict, aula: str, materia: str, total_q: int) -> str:
    pareto_set = compute_pareto_topics(data)
    pareto_count = len(pareto_set)
    total_ceb = sum(v.get('cebraspe', 0) for v in data.values())
    num_topics = len(data)

    other_stats = ''
    for k in ['fgv', 'fcc', 'vunesp']:
        tb = sum(v.get(k, 0) for v in data.values())
        if tb > 0:
            other_stats += f'<div class="st"><strong>{tb}</strong>{k.upper()}</div>'

    # Pareto info
    pareto_q = sum(v.get('total_questions', 0) for n, v in data.items() if n in pareto_set)
    pareto_pct = round(pareto_q / total_q * 100) if total_q > 0 else 0
    pareto_names = [n for n, v in sorted(data.items(), key=lambda x: x[1].get('rank', 99)) if n in pareto_set]

    pareto_info = f'''<div class="pareto-info">
<strong>Princípio de Pareto:</strong> {pareto_count} de {num_topics} tópicos concentram <strong>{pareto_pct}%</strong> das questões ({pareto_q} de {total_q}).
Esses tópicos receberam tratamento personalizado com analogias, mnemônicos e comparações visuais — marcados com ⭐.
</div>'''

    topics_html = ''.join(build_topic(n, d, n in pareto_set) for n, d in data.items())

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Resumo — {esc(aula)} · {esc(materia)}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script src="/assets/config.js"></script>
<style>{RESUMO_CSS}</style>
</head>
<body>

<!-- Auth Gate -->
<div id="auth-gate">
<div class="login-box">
<h1>Resumo de Memorização</h1>
<p class="subtitle">Faça login para acessar o material</p>
<form id="login-form">
<input type="email" id="login-email" placeholder="Email" required autocomplete="email">
<input type="password" id="login-pass" placeholder="Senha" required autocomplete="current-password">
<button type="submit">Entrar</button>
</form>
<p id="login-error"></p>
</div>
</div>

<!-- Main Content -->
<div id="main-content" style="display:none">
<div class="top-bar">
<a href="/index.html" class="back-link">&#8592; Painel de Estudos</a>
<button id="logout-btn" onclick="handleLogout()">Sair</button>
</div>
<div class="wrap">
<header>
<div class="badge">Resumo de Memorização</div>
<h1>{esc(aula)} — {esc(materia)}</h1>
<p class="sub">{total_q} questões analisadas · {num_topics} tópicos</p>
</header>
<div class="stats">
<div class="st"><strong>{total_q}</strong>Questões</div>
<div class="st"><strong>{total_ceb}</strong>CEBRASPE</div>
{other_stats}
<div class="st"><strong>{num_topics}</strong>Tópicos</div>
</div>
{pareto_info}
<div class="sec">
<div class="sec-tag">Tópicos rankeados por cobrança</div>
<h2>Do mais cobrado ao menos cobrado</h2>
{topics_html}
</div>
<footer>{esc(materia)} · {esc(aula)} · Gerado a partir de {total_q} questões</footer>
</div>
</div><!-- /main-content -->

<script>
// ===== Resumo interactions =====
function tgl(b){{b.classList.toggle('open');b.nextElementSibling.classList.toggle('show')}}

// ===== Supabase Auth =====
let sb=null, currentUser=null;

function initSB(){{
  if(typeof SUPABASE_URL==='undefined'||SUPABASE_URL.includes('SEU-PROJETO'))return false;
  sb=window.supabase.createClient(SUPABASE_URL,SUPABASE_ANON_KEY);return true;
}}

async function checkAuth(){{
  const{{data:{{session}}}}=await sb.auth.getSession();
  if(session){{currentUser=session.user;showContent();}}
  else{{document.getElementById('auth-gate').style.display='flex';}}
}}

function showContent(){{
  document.getElementById('auth-gate').style.display='none';
  document.getElementById('main-content').style.display='block';
}}

async function handleLogout(){{if(sb)await sb.auth.signOut();location.href='/index.html';}}

document.getElementById('login-form').addEventListener('submit',async e=>{{
  e.preventDefault();
  const em=document.getElementById('login-email').value;
  const pw=document.getElementById('login-pass').value;
  const er=document.getElementById('login-error');er.textContent='';
  const{{data,error}}=await sb.auth.signInWithPassword({{email:em,password:pw}});
  if(error){{er.textContent='Email ou senha incorretos.';return;}}
  currentUser=data.user;showContent();
}});

// ===== Init =====
document.addEventListener('DOMContentLoaded',()=>{{
  if(initSB()){{checkAuth();}}
  else{{showContent();}}
}});
</script>
</body>
</html>'''


def main():
    if len(sys.argv) != 6:
        print("Usage: python gerar_resumo_web.py <review_json> <output_html> <aula> <materia> <total_questions>", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        data = json.load(f)
    html = generate(data, sys.argv[3], sys.argv[4], int(sys.argv[5]))
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        f.write(html)

    # Report Pareto calculation
    pareto = compute_pareto_topics(data)
    total = sum(v.get('total_questions', 0) for v in data.values())
    pareto_q = sum(v.get('total_questions', 0) for n, v in data.items() if n in pareto)
    pct = round(pareto_q / total * 100) if total > 0 else 0
    print(f"Resumo web generated: {sys.argv[2]} ({len(html):,} bytes)", file=sys.stderr)
    print(f"Pareto: {len(pareto)}/{len(data)} topics = {pct}% of questions personalized", file=sys.stderr)


if __name__ == "__main__":
    main()
