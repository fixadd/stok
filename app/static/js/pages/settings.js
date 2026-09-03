(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || document.querySelector('input[name="csrf_token"]')?.value || '';
  const feedback = document.getElementById('settingsFeedback');

  function showError(message) {
    if (!feedback) return;
    feedback.textContent = message;
    feedback.classList.remove('d-none');
    window.setTimeout(() => feedback.classList.add('d-none'), 3500);
  }

  async function requestJson(url, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('X-CSRF-Token', csrf);
    headers.set('Accept', 'application/json');
    if (options.body && typeof options.body !== 'string') {
      headers.set('Content-Type', 'application/json');
      options.body = JSON.stringify(options.body);
    }
    const response = await fetch(url, {...options, headers});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'İşlem başarısız.');
    return data;
  }

  document.querySelectorAll('[data-add-option]').forEach((button) => {
    button.addEventListener('click', async () => {
      const list = button.closest('[data-setting-list]');
      const input = list?.querySelector('[data-new-option-label]');
      const label = input?.value.trim();
      if (!label) return;
      button.disabled = true;
      try {
        await requestJson(`/api/settings/lists/${button.dataset.listId}/options`, {method: 'POST', body: {label}});
        window.location.reload();
      } catch (error) {
        showError(error.message);
        button.disabled = false;
      }
    });
  });

  document.querySelectorAll('[data-toggle-option]').forEach((button) => {
    button.addEventListener('click', async () => {
      try {
        await requestJson(`/api/settings/options/${button.dataset.optionId}`, {
          method: 'PATCH',
          body: {active: button.dataset.active === 'true'},
        });
        window.location.reload();
      } catch (error) {
        showError(error.message);
      }
    });
  });

  const fieldForm = document.getElementById('newFieldForm');
  fieldForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(fieldForm).entries());
    for (const key of ['required', 'visible_form', 'visible_list', 'searchable']) data[key] = data[key] === 'true';
    try {
      await requestJson('/api/settings/fields', {method: 'POST', body: data});
      window.location.reload();
    } catch (error) {
      showError(error.message);
    }
  });
})();
