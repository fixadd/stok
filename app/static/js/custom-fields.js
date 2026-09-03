(() => {
  const originalFetch = window.fetch.bind(window);
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';

  function readCustomValues(form) {
    const values = {};
    if (!form) return values;
    form.querySelectorAll('[data-custom-field-key]').forEach((container) => {
      const input = container.querySelector('[name]');
      if (!input) return;
      const key = input.name;
      if (input.type === 'checkbox') {
        values[key] = input.checked;
      } else if (input.multiple) {
        values[key] = Array.from(input.selectedOptions).map(option => option.value);
      } else {
        values[key] = input.value;
      }
    });
    return values;
  }

  function customFormForInventory() {
    return document.querySelector('#inventoryCreateForm[data-custom-entity="inventory"]');
  }

  window.fetch = async function(input, init = {}) {
    const url = typeof input === 'string' ? input : input?.url || '';
    const method = String(init.method || (typeof input !== 'string' && input?.method) || 'GET').toUpperCase();
    const skip = init.headers && new Headers(init.headers).get('X-Custom-Fields-Sync') === '1';
    const response = await originalFetch(input, init);
    if (skip || method === 'GET' || !url.includes('/api/inventory')) return response;
    if (!(method === 'POST' || method === 'PATCH')) return response;
    if (!response.ok) return response;

    let data = {};
    try { data = await response.clone().json(); } catch (_) { return response; }
    const itemId = data?.item?.id || url.match(/\/api\/inventory\/(\d+)/)?.[1];
    if (!itemId) return response;

    const form = method === 'POST' ? customFormForInventory() : document.querySelector('#inventoryEditForm[data-custom-entity="inventory"]');
    const values = readCustomValues(form);
    if (!Object.keys(values).length) return response;

    const headers = new Headers({'Content-Type': 'application/json', 'Accept': 'application/json', 'X-CSRF-Token': csrf, 'X-Custom-Fields-Sync': '1'});
    const customResponse = await originalFetch(`/api/custom-fields/inventory/${itemId}`, {
      method: 'PUT', headers, body: JSON.stringify(values),
    });
    if (!customResponse.ok && method === 'POST') {
      try { console.warn('Özel alanlar kaydedilemedi:', (await customResponse.json()).error); } catch (_) {}
    }
    return response;
  };
})();
