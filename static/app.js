// Dientecito Feliz - interacciones de la interfaz (sin librerias externas)
const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];

// Pedir confirmacion antes de acciones destructivas
$$('form[data-confirmar]').forEach(f =>
  f.addEventListener('submit', e => { if (!confirm(f.dataset.confirmar)) e.preventDefault(); }));

// Selects que se guardan al cambiar (estado de cita, estado de tratamiento)
$$('select[data-autoenviar]').forEach(s => s.addEventListener('change', () => s.form.submit()));

// Busqueda de pacientes mientras se escribe
$$('input[data-buscar]').forEach(input => {
  let t;
  input.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => input.form.submit(), 400); });
  if (input.value) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
});

// Filtro local (inventario)
$$('input[data-filtrar]').forEach(input => input.addEventListener('input', () => {
  const texto = input.value.trim().toLowerCase();
  $$(input.dataset.filtrar).forEach(el => { el.hidden = !el.dataset.texto.includes(texto); });
}));

// Recordar el nombre del estudiante en este dispositivo
$$('input[data-recordar]').forEach(input => {
  const clave = 'dientecito.' + input.dataset.recordar;
  try { input.value ||= localStorage.getItem(clave) || ''; } catch {}
  input.form.addEventListener('submit', () => { try { localStorage.setItem(clave, input.value); } catch {} });
});

// Precio automatico desde el tarifario
$$('input[data-tarifario]').forEach(input => input.addEventListener('input', () => {
  const op = $$('#' + input.getAttribute('list') + ' option').find(o => o.value === input.value);
  const costo = input.form.elements.costo;
  if (op && costo && !costo.value) costo.value = op.dataset.precio;
}));

// Pestanas del expediente (sincronizadas con la direccion #seccion)
const pestanas = $('[data-pestanas]');
if (pestanas) {
  const enlaces = $$('a', pestanas);
  const mostrar = id => {
    if (!enlaces.some(a => a.hash === '#' + id)) id = enlaces[0].hash.slice(1);
    enlaces.forEach(a => a.classList.toggle('activo', a.hash === '#' + id));
    $$('.panel').forEach(p => { p.hidden = p.id !== id; });
  };
  enlaces.forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    history.replaceState(null, '', a.hash);
    mostrar(a.hash.slice(1));
  }));
  mostrar(location.hash.slice(1));
}

// Odontograma: elegir estado y tocar dientes
const odonto = $('[data-odontograma]');
if (odonto) {
  let estado = $('.paleta .activo', odonto).dataset;
  $$('.paleta button', odonto).forEach(b => b.addEventListener('click', () => {
    $$('.paleta button', odonto).forEach(x => x.classList.remove('activo'));
    b.classList.add('activo');
    estado = b.dataset;
  }));

  const resumir = () => {
    const cuenta = {};
    $$('.diente', odonto).forEach(d => { if (d.dataset.actual !== 'Sano') cuenta[d.dataset.actual] = (cuenta[d.dataset.actual] || 0) + 1; });
    const partes = Object.entries(cuenta).map(([e, n]) => `${e}: ${n}`);
    $('[data-resumen]', odonto).textContent = partes.length ? 'Resumen · ' + partes.join(' · ') : 'Todos los dientes están sanos.';
  };

  $$('.diente', odonto).forEach(d => d.addEventListener('click', async () => {
    const anterior = { actual: d.dataset.actual, color: d.style.getPropertyValue('--color') };
    // Tocar de nuevo con el mismo estado lo regresa a "Sano"
    const nuevo = d.dataset.actual === estado.estado ? $('.paleta [data-estado="Sano"]', odonto).dataset : estado;
    d.dataset.actual = nuevo.estado;
    d.style.setProperty('--color', nuevo.color);
    d.title = `Diente ${d.dataset.diente}: ${nuevo.estado}`;
    resumir();
    const r = await fetch(odonto.dataset.odontograma, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diente: +d.dataset.diente, estado: nuevo.estado }),
    }).catch(() => null);
    if (!r || !r.ok) {  // si falla la red, deshacer
      d.dataset.actual = anterior.actual;
      d.style.setProperty('--color', anterior.color);
      resumir();
      alert('No se pudo guardar. Revisa la conexión.');
    }
  }));
  resumir();
}

// Firma del consentimiento (dedo, lapiz o mouse)
$$('form[data-firma]').forEach(form => {
  const canvas = $('canvas', form);
  const ctx = canvas.getContext('2d');
  let dibujando = false, hayTrazo = false;

  const ajustar = () => {
    const r = canvas.getBoundingClientRect();
    if (!r.width) return;
    const escala = window.devicePixelRatio || 1;
    canvas.width = r.width * escala;
    canvas.height = r.height * escala;
    ctx.scale(escala, escala);
    ctx.lineWidth = 2.5; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#1d2b2a';
    hayTrazo = false;
  };
  const punto = e => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };

  canvas.addEventListener('pointerdown', e => {
    if (!canvas.width || canvas.width < 10) ajustar();
    dibujando = true; canvas.setPointerCapture(e.pointerId);
    ctx.beginPath(); ctx.moveTo(...punto(e));
  });
  canvas.addEventListener('pointermove', e => { if (dibujando) { ctx.lineTo(...punto(e)); ctx.stroke(); hayTrazo = true; } });
  ['pointerup', 'pointercancel'].forEach(ev => canvas.addEventListener(ev, () => { dibujando = false; }));

  $('[data-limpiar]', form).addEventListener('click', ajustar);
  form.addEventListener('submit', e => {
    if (!hayTrazo) { e.preventDefault(); alert('Primero el paciente debe firmar en el recuadro.'); return; }
    form.elements.firma.value = canvas.toDataURL('image/png');
  });
  // El lienzo puede estar oculto (otra pestana o "Volver a firmar"); se ajusta al mostrarse
  new ResizeObserver(() => { if (!hayTrazo) ajustar(); }).observe(canvas);
});
