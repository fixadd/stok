(() => {
  'use strict';

  const root = document.documentElement;
  const storageKey = 'stok-theme';

  const applyTheme = (theme) => {
    const normalized = theme === 'light' ? 'light' : 'dark';
    root.setAttribute('data-bs-theme', normalized);
    root.style.colorScheme = normalized;
    try { localStorage.setItem(storageKey, normalized); } catch (_) {}

    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      const icon = button.querySelector('i');
      if (icon) icon.className = normalized === 'dark' ? 'ti ti-sun' : 'ti ti-moon';
      button.setAttribute('aria-label', normalized === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç');
      button.setAttribute('title', normalized === 'dark' ? 'Açık tema' : 'Koyu tema');
    });
  };

  const savedTheme = (() => {
    try { return localStorage.getItem(storageKey); } catch (_) { return null; }
  })();
  applyTheme(savedTheme || root.getAttribute('data-bs-theme') || 'dark');

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-theme-toggle]');
    if (!button) return;
    event.preventDefault();
    applyTheme(root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark');
  });

  const input = document.querySelector('.topbar-search-input');
  const links = [...document.querySelectorAll('.sidebar-nav a.nav-link[href]')]
    .filter((link) => link.textContent.trim());

  let palette;
  let list;
  let selected = 0;

  const closePalette = () => {
    if (!palette) return;
    palette.hidden = true;
    if (input) input.value = '';
  };

  const render = (query = '') => {
    if (!list) return;
    const term = query.trim().toLocaleLowerCase('tr-TR');
    const matches = links.filter((link) => link.textContent.toLocaleLowerCase('tr-TR').includes(term));
    list.innerHTML = '';
    selected = 0;

    if (!matches.length) {
      const empty = document.createElement('div');
      empty.className = 'app-search-empty';
      empty.textContent = 'Eşleşen sayfa bulunamadı.';
      list.appendChild(empty);
      return;
    }

    matches.forEach((link, index) => {
      const item = document.createElement('a');
      item.href = link.href;
      item.className = 'app-search-item' + (index === 0 ? ' is-selected' : '');
      item.innerHTML = '<i class="ti ti-arrow-right"></i><span>' + link.textContent.trim() + '</span>';
      item.addEventListener('mouseenter', () => {
        selected = index;
        [...list.children].forEach((node, i) => node.classList.toggle('is-selected', i === selected));
      });
      list.appendChild(item);
    });
  };

  const ensurePalette = () => {
    if (palette) return;
    palette = document.createElement('div');
    palette.className = 'app-search-palette';
    palette.hidden = true;
    palette.innerHTML = '<div class="app-search-backdrop" data-search-close></div>' +
      '<div class="app-search-dialog" role="dialog" aria-modal="true" aria-label="Sayfa ara">' +
      '<div class="app-search-dialog-head"><i class="ti ti-search"></i><input type="search" aria-label="Sayfa ara" placeholder="Sayfa veya modül ara..."><kbd>ESC</kbd></div>' +
      '<div class="app-search-list"></div></div>';
    document.body.appendChild(palette);
    const dialogInput = palette.querySelector('input');
    list = palette.querySelector('.app-search-list');

    palette.addEventListener('click', (event) => {
      if (event.target.matches('[data-search-close]')) closePalette();
    });
    dialogInput.addEventListener('input', () => render(dialogInput.value));
    dialogInput.addEventListener('keydown', (event) => {
      const items = [...list.querySelectorAll('.app-search-item')];
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        if (!items.length) return;
        selected = (selected + 1) % items.length;
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        if (!items.length) return;
        selected = (selected - 1 + items.length) % items.length;
      } else if (event.key === 'Enter' && items[selected]) {
        items[selected].click();
        return;
      } else if (event.key === 'Escape') {
        closePalette();
        return;
      } else {
        return;
      }
      items.forEach((item, i) => item.classList.toggle('is-selected', i === selected));
    });
  };

  const openPalette = (query = '') => {
    ensurePalette();
    palette.hidden = false;
    const dialogInput = palette.querySelector('input');
    dialogInput.value = query;
    render(query);
    requestAnimationFrame(() => dialogInput.focus());
  };

  input?.addEventListener('focus', () => openPalette(input.value));
  input?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      openPalette(input.value);
    }
    if (event.key === 'Escape') closePalette();
  });

  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      openPalette();
    }
    if (event.key === 'Escape' && palette && !palette.hidden) closePalette();
  });
})();
