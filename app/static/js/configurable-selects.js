(() => {
  const body = document.body;
  if (body?.dataset.isAdmin !== '1') return;
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const map = {
    status: 'inventory_status',
    inventory_status: 'inventory_status',
    license_status: 'license_status',
    stock_status: 'stock_status',
    unit: 'stock_unit',
    stock_unit: 'stock_unit',
    maintenance_type: 'maintenance_type',
    maintenance_status: 'maintenance_status',
    maintenance_result: 'maintenance_result',
    priority: 'priority',
    request_priority: 'request_priority',
    request_status: 'request_status',
    request_type: 'request_type',
    license_type: 'license_type',
    stock_source: 'stock_source',
  };

  async function addOption(key, select) {
    const label = window.prompt('Yeni seçenek adı:');
    if (!label?.trim()) return;
    const response = await fetch(`/api/settings/lists/by-key/${encodeURIComponent(key)}/options`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-CSRF-Token': csrf},
      body: JSON.stringify({label: label.trim()}),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Seçenek eklenemedi.');
    const option = new Option(data.label, data.value, true, true);
    select.add(option);
    select.dispatchEvent(new Event('change', {bubbles: true}));
  }

  document.querySelectorAll('select').forEach((select) => {
    const key = select.dataset.settingKey || map[select.name] || map[select.id];
    if (!key || select.dataset.configGear === '1') return;
    select.dataset.configGear = '1';
    const wrapper = document.createElement('div');
    wrapper.className = 'configurable-select-wrap';
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(select);
    const gear = document.createElement('button');
    gear.type = 'button';
    gear.className = 'btn btn-sm btn-outline-secondary configurable-select-gear';
    gear.title = 'Seçenek ekle';
    gear.setAttribute('aria-label', 'Seçenek ekle');
    gear.innerHTML = '<i class="ti ti-settings"></i>';
    gear.addEventListener('click', async () => {
      gear.disabled = true;
      try { await addOption(key, select); } catch (error) { window.alert(error.message); } finally { gear.disabled = false; }
    });
    wrapper.appendChild(gear);
  });
})();
