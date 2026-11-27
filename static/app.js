/* Interfaz de Sembri: misma vista del prototipo del taller, con respuestas de Gemini vía /api/chat. */
(() => {
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let sesion = null, ocupado = false;

/* Markdown mínimo y seguro: párrafos, **negrita**, listas, tablas. */
function inline(s) { return s.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>'); }
function md(texto) {
  const lineas = esc(texto).split('\n');
  let html = '', lista = null, tabla = [];
  const cerrarLista = () => { if (lista) { html += `</${lista}>`; lista = null; } };
  const cerrarTabla = () => {
    if (!tabla.length) return;
    const filas = tabla.map((l) => l.replace(/^\||\|$/g, '').split('|').map((c) => c.trim()));
    const sep = filas.length > 1 && filas[1].every((c) => /^:?-{2,}:?$/.test(c));
    const cuerpo = filas.filter((_, i) => !(sep && i === 1));
    html += '<table>' + cuerpo.map((f, i) => `<tr>${f.map((c) => sep && i === 0 ? `<th>${inline(c)}</th>` : `<td>${inline(c)}</td>`).join('')}</tr>`).join('') + '</table>';
    tabla = [];
  };
  for (const l of lineas) {
    const t = l.trim();
    if (t.startsWith('|')) { cerrarLista(); tabla.push(t); continue; }
    cerrarTabla();
    let m;
    if ((m = t.match(/^[-*•]\s+(.*)/))) { if (lista !== 'ul') { cerrarLista(); html += '<ul>'; lista = 'ul'; } html += `<li>${inline(m[1])}</li>`; }
    else if ((m = t.match(/^\d+[.)]\s+(.*)/))) { if (lista !== 'ol') { cerrarLista(); html += '<ol>'; lista = 'ol'; } html += `<li>${inline(m[1])}</li>`; }
    else { cerrarLista(); if (t) html += `<p>${inline(t)}</p>`; }
  }
  cerrarLista(); cerrarTabla();
  return html;
}

function visual(v) {
  if (v.tipo === 'compatibilidad')
    return `<div class="vis">${v.items.map((x) => `<div>${esc(x.nombre)} · ${x.pct.toFixed(2).replace('.', ',')} %</div><div class="bar"><i style="width:${x.pct}%"></i></div>`).join('')}</div>`;
  return '';
}

function chips(lista) {
  const c = document.createElement('div');
  c.className = 'chips';
  lista.forEach((x) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip';
    b.textContent = x.label;
    b.addEventListener('click', () => enviar(x.texto || x.label));
    c.appendChild(b);
  });
  return c;
}

function pintar(quien, c) {
  const div = document.createElement('div');
  div.className = 'msg ' + quien;
  if (quien === 'user') div.textContent = c;
  else if (quien === 'error') div.textContent = c;
  else {
    div.innerHTML = md(c.texto) + (c.visuales || []).map(visual).join('') +
      (c.reglas && c.reglas.length ? `<span class="rule">Regla${c.reglas.length > 1 ? 's' : ''} ${esc(c.reglas.join(', ').replace(/, (R\d)$/, ' y $1'))}</span>` : '');
    if (c.chips && c.chips.length) div.appendChild(chips(c.chips));
  }
  $('log').appendChild(div);
  $('log').scrollTop = $('log').scrollHeight;
  return div;
}

async function enviar(txt) {
  txt = String(txt).trim();
  if (!txt || ocupado) return;
  ocupado = true; $('enviar').disabled = true;
  pintar('user', txt);
  const espera = document.createElement('div');
  espera.className = 'msg bot';
  espera.innerHTML = '<span class="typing" role="status" aria-label="Sembri está escribiendo"><i></i><i></i><i></i></span>';
  $('log').appendChild(espera); $('log').scrollTop = $('log').scrollHeight;
  try {
    const controlador = new AbortController();
    const temporizador = setTimeout(() => controlador.abort(), 35000);
    let r;
    try {
      r = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mensaje: txt, sesion}),
        signal: controlador.signal,
      });
    } finally {
      clearTimeout(temporizador);
    }
    const d = await r.json().catch(() => ({}));
    espera.remove();
    if (!r.ok) pintar('error', d.error || 'No pude responder. Intenta de nuevo.');
    else { sesion = d.sesion; pintar('bot', d); }
  } catch (e) {
    espera.remove();
    if (e && e.name === 'AbortError')
      pintar('error', 'Sembri tardó demasiado en responder. Intenta de nuevo.');
    else
      pintar('error', 'No hay conexión con el servidor de Sembri. Revisa que esté en ejecución.');
  } finally {
    ocupado = false; $('enviar').disabled = false; $('q').focus();
  }
}

$('f').addEventListener('submit', (e) => { e.preventDefault(); const v = $('q').value; $('q').value = ''; enviar(v); });

fetch('/api/estado').then((r) => r.json()).then((s) => {
  pintar('bot', s.saludo);
  if (!s.configurado) pintar('error', 'Falta configurar GEMINI_API_KEY en el archivo .env para que Sembri pueda responder.');
});
})();
