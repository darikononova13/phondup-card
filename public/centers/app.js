'use strict';
(() => {
  const query = document.getElementById('search');
  const clear = document.getElementById('clear');
  const cards = [...document.querySelectorAll('.center-card')];
  const countries = [...document.querySelectorAll('.country[data-country]')];
  const providers = [...document.querySelectorAll('[data-provider]')];
  let country = 'all', provider = 'all';
  const normalize = text => text.toLocaleLowerCase('ru').replace(/ё/g, 'е').trim();
  function plural(n, forms) { return n % 10 === 1 && n % 100 !== 11 ? forms[0] : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? forms[1] : forms[2]; }
  function update() {
    const text = normalize(query.value), cities = new Set();
    let count = 0;
    for (const card of cards) {
      const maps = [...card.querySelectorAll('[data-map-provider]')];
      for (const link of maps) link.hidden = provider !== 'all' && link.dataset.mapProvider !== provider;
      const visible = (country === 'all' || card.dataset.country === country) && normalize(card.dataset.search).includes(text) && maps.some(link => !link.hidden);
      card.hidden = !visible;
      if (visible) { count++; cities.add(card.dataset.city); }
    }
    document.getElementById('empty').hidden = count !== 0;
    document.getElementById('result-count').textContent = count + ' ' + plural(count, ['адрес', 'адреса', 'адресов']) + ' · ' + cities.size + ' ' + plural(cities.size, ['город', 'города', 'городов']);
    clear.hidden = query.value.length === 0;
    providers.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.provider === provider)));
    countries.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.country === country)));
  }
  query.addEventListener('input', update);
  clear.addEventListener('click', () => { query.value = ''; update(); query.focus(); });
  countries.forEach(button => button.addEventListener('click', () => { country = button.dataset.country; update(); }));
  providers.forEach(button => button.addEventListener('click', () => { provider = button.dataset.provider; update(); }));
  document.getElementById('reset').addEventListener('click', () => { query.value = ''; country = 'all'; provider = 'all'; update(); query.focus(); });
  const SHARE_URL = location.href.split('#')[0].split('?')[0];
  const shareDialog = document.getElementById('share-dialog');
  document.getElementById('share').addEventListener('click', async () => {
    if (location.protocol === 'file:') { alert('Ссылка станет доступна после публикации страницы'); return; }
    if (navigator.share) {
      try { await navigator.share({title: 'Центры PHONDÜP на картах', text: 'Выберите город и откройте PHONDÜP в Яндекс Картах или 2ГИС.', url: SHARE_URL}); return; }
      catch (error) { if (error.name === 'AbortError') return; }
    }
    document.getElementById('copy-status').textContent = '';
    document.getElementById('share-url').value = SHARE_URL;
    shareDialog.showModal();
  });
  document.getElementById('copy').addEventListener('click', async () => {
    let copied = false;
    try { await navigator.clipboard.writeText(SHARE_URL); copied = true; }
    catch { const input = document.getElementById('share-url'); input.focus(); input.select(); copied = document.execCommand('copy'); }
    document.getElementById('copy-status').textContent = copied ? 'Ссылка скопирована — отправьте её в мессенджер.' : 'Выделите и скопируйте ссылку вручную.';
  });
  for (const dialog of document.querySelectorAll('dialog')) {
    dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target !== dialog) return; const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); });
  }
  update();
})();
