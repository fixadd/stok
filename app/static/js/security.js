(() => {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (!meta) return;
  const token = meta.getAttribute('content');

  document.querySelectorAll('form').forEach((form) => {
    if ((form.method || 'get').toLowerCase() !== 'post') return;
    if (form.querySelector('input[name="csrf_token"]')) return;
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'csrf_token';
    input.value = token;
    form.appendChild(input);
  });

  const originalFetch = window.fetch;
  window.fetch = (input, init = {}) => {
    const options = { ...init, headers: new Headers(init.headers || {}) };
    const url = typeof input === 'string' ? input : input.url;
    const method = (options.method || (typeof input !== 'string' && input.method) || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
      options.headers.set('X-CSRF-Token', token);
    }
    return originalFetch(input, options);
  };
})();
