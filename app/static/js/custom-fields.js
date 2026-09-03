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

  function setCustomValues(form, values) {
    if (!form || !values || typeof values !== 'object') return;
    form.querySelectorAll('[data-custom-field-key]').forEach((container) => {
      const input = container.querySelector('[name]');
      if (!input || !(input.name in values)) return;
      const value = values[input.name];
      if (input.type === 'checkbox') {
        input.checked = value === true || value === 'true' || value === '1' || value === 'on';
      } else if (input.multiple && Array.isArray(value)) {
        const selected = new Set(value.map(String));
        Array.from(input.options).forEach(option => { option.selected = selected.has(option.value); });
      } else if (value !== null && value !== undefined) {
        input.value = String(value);
      }
    });
  }

  async function loadCustomValues(form) {
    const entityId = form?.dataset.customEntityId;
    if (!form || !entityId) return;
    try {
      const response = await originalFetch(`/api/custom-fields/inventory/${entityId}`, {
        headers: {'Accept': 'application/json', 'X-CSRF-Token': csrf},
      });
      if (response.ok) setCustomValues(form, await response.json());
    } catch (_) {
      // Core inventory editing must continue even if optional custom data is unavailable.
    }
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
    if (!(method === 'POST' || method === 'PATCH') || !response.ok) return response;

    let data = {};
    try { data = await response.clone().json(); } catch (_) { return response; }
    const itemId = data?.item?.id || url.match(/\/api\/inventory\/(\d+)/)?.[1];
    if (!itemId) return response;

    const form = method === 'POST'
      ? customFormForInventory()
      : document.querySelector('#inventoryEditForm[data-custom-entity="inventory"]');
    const values = readCustomValues(form);
    if (!Object.keys(values).length) return response;

    const headers = new Headers({
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-CSRF-Token': csrf,
      'X-Custom-Fields-Sync': '1',
    });
    const customResponse = await originalFetch(`/api/custom-fields/inventory/${itemId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(values),
    });
    if (!customResponse.ok) {
      try { console.warn('Özel alanlar kaydedilemedi:', (await customResponse.json()).error); } catch (_) {}
    }
    return response;
  };

  document.addEventListener('shown.bs.modal', (event) => {
    const modal = event.target;
    const form = modal?.querySelector('#inventoryEditForm[data-custom-entity="inventory"]');
    if (form) loadCustomValues(form);
  });
})();