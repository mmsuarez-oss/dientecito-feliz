// Dientecito Feliz - interacciones de la interfaz (sin librerias externas)
const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];

// Confirmar acciones destructivas
$$('form[data-confirmar]').forEach(f =>
  f.addEventListener('submit', e => { if (!confirm(f.dataset.confirmar)) e.preventDefault(); }));

// Listas desplegables que se guardan al cambiar
$$('select[data-autoenviar]').forEach(s => s.addEventListener('change', () => s.form.submit()));

// Busqueda mientras se escribe
$$('input[data-buscar]').forEach(input => {
  let espera;
  input.addEventListener('input', () => { clearTimeout(espera); espera = setTimeout(() => input.form.submit(), 400); });
  if (input.value) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
});

// Precio automatico desde el tarifario
$$('input[data-tarifario]').forEach(input => input.addEventListener('input', () => {
  const op = $$('#' + input.getAttribute('list') + ' option').find(o => o.value === input.value);
  const costo = input.form.elements.costo;
  if (op && costo && !costo.value) costo.value = op.dataset.precio;
}));

// Secciones del expediente (sincronizadas con la direccion #seccion)
const pestanas = $('[data-pestanas]');
if (pestanas) {
  const enlaces = $$('a', pestanas);
  const mostrar = id => {
    if (!enlaces.some(a => a.hash === '#' + id)) id = enlaces[0].hash.slice(1);
    enlaces.forEach(a => a.classList.toggle('activa', a.hash === '#' + id));
    $$('.seccion').forEach(s => { s.hidden = s.id !== id; });
  };
  enlaces.forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    history.replaceState(null, '', a.hash);
    mostrar(a.hash.slice(1));
  }));
  mostrar(location.hash.slice(1));
}

// Odontograma: tocar un diente lo elige para el registro
const odonto = $('[data-odontograma]');
if (odonto) {
  const campo = $('[data-diente-elegido]', odonto);
  $$('.diente', odonto).forEach(d => d.addEventListener('click', () => {
    $$('.diente', odonto).forEach(x => x.classList.remove('elegido'));
    d.classList.add('elegido');
    campo.value = d.dataset.diente;
    campo.form.elements.estado.focus({ preventScroll: true });
  }));
  campo.form.addEventListener('submit', e => {  // un campo de solo lectura no se valida solo
    if (!campo.value) {
      e.preventDefault();
      e.stopImmediatePropagation();
      alert('Primero toque en el odontograma el diente que trabajó.');
    }
  });
}

// Vista previa de la foto elegida
$$('input[data-vista-previa]').forEach(input => input.addEventListener('change', () => {
  const img = input.nextElementSibling;
  if (img.src) URL.revokeObjectURL(img.src);
  img.hidden = !input.files[0];
  if (input.files[0]) img.src = URL.createObjectURL(input.files[0]);
}));

// Subida de fotos: se reducen a 1600 px antes de enviarlas (las del telefono pesan varios MB)
$$('form[data-foto]').forEach(form => form.addEventListener('submit', async e => {
  const input = $('input[type=file]', form);
  const archivo = input.files[0];
  if (!archivo || !form.checkValidity()) return;
  e.preventDefault();
  const boton = $('.acciones .btn', form);
  boton.disabled = true;
  boton.textContent = 'Subiendo foto…';
  const datos = new FormData(form);
  try {
    const imagen = await createImageBitmap(archivo);
    const escala = Math.min(1, 1600 / Math.max(imagen.width, imagen.height));
    const lienzo = document.createElement('canvas');
    lienzo.width = Math.round(imagen.width * escala);
    lienzo.height = Math.round(imagen.height * escala);
    lienzo.getContext('2d').drawImage(imagen, 0, 0, lienzo.width, lienzo.height);
    const reducida = await new Promise(listo => lienzo.toBlob(listo, 'image/jpeg', 0.85));
    if (reducida) datos.set(input.name, reducida, 'foto.jpg');
  } catch { /* si el navegador no puede leer la imagen, se envia la original */ }
  try {
    const r = await fetch(form.action, { method: 'POST', body: datos });
    history.replaceState(null, '', r.url + (form.dataset.foto || ''));
    location.reload();
  } catch {
    boton.disabled = false;
    boton.textContent = 'Guardar registro';
    alert('No se pudo subir la foto. Revise la conexión e intente de nuevo.');
  }
}));

// Firma del consentimiento (dedo, lapiz o mouse)
$$('form[data-firma]').forEach(form => {
  const lienzo = $('canvas', form);
  const ctx = lienzo.getContext('2d');
  let dibujando = false, hayTrazo = false;

  const preparar = () => {
    const r = lienzo.getBoundingClientRect();
    if (!r.width) return;
    const escala = window.devicePixelRatio || 1;
    lienzo.width = r.width * escala;
    lienzo.height = r.height * escala;
    ctx.scale(escala, escala);
    ctx.lineWidth = 2.5; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#1e1e1e';
    hayTrazo = false;
  };
  const punto = e => { const r = lienzo.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };

  lienzo.addEventListener('pointerdown', e => {
    dibujando = true;
    lienzo.setPointerCapture(e.pointerId);
    ctx.beginPath();
    ctx.moveTo(...punto(e));
  });
  lienzo.addEventListener('pointermove', e => { if (dibujando) { ctx.lineTo(...punto(e)); ctx.stroke(); hayTrazo = true; } });
  ['pointerup', 'pointercancel'].forEach(ev => lienzo.addEventListener(ev, () => { dibujando = false; }));

  $('[data-limpiar]', form).addEventListener('click', preparar);
  form.addEventListener('submit', e => {
    if (!hayTrazo) { e.preventDefault(); alert('Falta la firma del paciente.'); return; }
    form.elements.firma.value = lienzo.toDataURL('image/png');
  });
  // El recuadro puede estar oculto al cargar (otra seccion); se prepara cuando se muestra
  new ResizeObserver(() => { if (!hayTrazo) preparar(); }).observe(lienzo);
});
