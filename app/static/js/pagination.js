(function () {
  const instances = new Map();

  function toElement(target) {
    if (!target) {
      return null;
    }
    if (target instanceof Element) {
      return target;
    }
    if (typeof target === 'string') {
      return document.querySelector(target);
    }
    return null;
  }

  function getContainer(target) {
    const element = toElement(target);
    if (!element) {
      return null;
    }
    if (element.hasAttribute('data-paginate')) {
      return element;
    }
    return element.closest('[data-paginate]');
  }

  function readPageSize(element) {
    const value = Number.parseInt(element.getAttribute('data-page-size') || '', 10);
    return Number.isFinite(value) && value > 0 ? value : 20;
  }

  function getItems(element, selector) {
    if (selector) {
      return Array.from(element.querySelectorAll(selector));
    }
    return Array.from(element.children || []);
  }

  function ensureOriginalDisplay(item) {
    if (!item.dataset.paginationOriginalDisplay) {
      item.dataset.paginationOriginalDisplay = item.style.display || '';
    }
    return item.dataset.paginationOriginalDisplay;
  }

  function showItem(item) {
    const original = ensureOriginalDisplay(item);
    item.style.display = original;
    item.removeAttribute('data-pagination-hidden');
  }

  function hideItem(item) {
    ensureOriginalDisplay(item);
    item.style.display = 'none';
    item.setAttribute('data-pagination-hidden', 'true');
  }

  function createControls(element) {
    const controls = document.createElement('div');
    controls.className = 'pagination-controls d-flex flex-column flex-md-row align-items-md-center justify-content-between gap-2 mt-3';

    const info = document.createElement('div');
    info.className = 'pagination-info text-muted small';
    controls.appendChild(info);

    const nav = document.createElement('nav');
    nav.setAttribute('aria-label', 'Sayfalama');
    const list = document.createElement('ul');
    list.className = 'pagination pagination-sm mb-0';
    nav.appendChild(list);
    controls.appendChild(nav);

    if (element.tagName === 'TABLE') {
      element.insertAdjacentElement('afterend', controls);
    } else {
      element.appendChild(controls);
    }

    return { controls, info, list, nav };
  }

  function renderPageButtons(state, totalPages) {
    const { list, nav } = state;
    list.innerHTML = '';

    const { currentPage } = state;

    function createPageItem({ label, page, disabled = false, active = false, ariaLabel = null }) {
      const li = document.createElement('li');
      li.className = 'page-item';
      if (disabled) {
        li.classList.add('disabled');
      }
      if (active) {
        li.classList.add('active');
      }
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'page-link';
      button.textContent = label;
      if (ariaLabel) {
        button.setAttribute('aria-label', ariaLabel);
      }
      if (!disabled) {
        button.addEventListener('click', () => {
          state.goto(page);
        });
      }
      li.appendChild(button);
      list.appendChild(li);
    }

    const prevDisabled = currentPage <= 1;
    createPageItem({ label: '‹', page: currentPage - 1, disabled: prevDisabled, ariaLabel: 'Önceki sayfa' });

    const pagesToRender = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i += 1) {
        pagesToRender.push(i);
      }
    } else {
      const dynamicPages = new Set([1, 2, totalPages, totalPages - 1, currentPage, currentPage - 1, currentPage + 1]);
      const filtered = Array.from(dynamicPages)
        .filter((page) => page >= 1 && page <= totalPages)
        .sort((a, b) => a - b);
      for (const page of filtered) {
        pagesToRender.push(page);
      }
    }

    let lastPageRendered = 0;
    pagesToRender.forEach((page) => {
      if (page - lastPageRendered > 1) {
        const ellipsisItem = document.createElement('li');
        ellipsisItem.className = 'page-item disabled';
        const span = document.createElement('span');
        span.className = 'page-link';
        span.textContent = '…';
        ellipsisItem.appendChild(span);
        list.appendChild(ellipsisItem);
      }
      createPageItem({ label: String(page), page, active: page === currentPage });
      lastPageRendered = page;
    });

    const nextDisabled = currentPage >= totalPages;
    createPageItem({ label: '›', page: currentPage + 1, disabled: nextDisabled, ariaLabel: 'Sonraki sayfa' });

    if (totalPages <= 1) {
      nav.classList.add('d-none');
    } else {
      nav.classList.remove('d-none');
    }
  }

  function apply(state) {
    const { element, selector } = state;
    const items = getItems(element, selector);

    const availableItems = [];
    const filteredItems = [];

    items.forEach((item) => {
      const isFiltered =
        item.classList.contains('d-none') ||
        item.dataset.searchHidden === 'true' ||
        item.hidden === true;
      if (isFiltered) {
        filteredItems.push(item);
      } else {
        availableItems.push(item);
      }
    });

    const totalItems = availableItems.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / state.pageSize));

    if (totalItems === 0) {
      state.currentPage = 1;
    } else if (state.currentPage > totalPages) {
      state.currentPage = totalPages;
    } else if (state.currentPage < 1) {
      state.currentPage = 1;
    }

    const startIndex = totalItems === 0 ? 0 : (state.currentPage - 1) * state.pageSize;
    const endIndex = Math.min(startIndex + state.pageSize, totalItems);

    availableItems.forEach((item, index) => {
      if (index >= startIndex && index < endIndex) {
        showItem(item);
      } else {
        hideItem(item);
      }
    });

    filteredItems.forEach((item) => {
      showItem(item);
    });

    if (totalItems === 0) {
      state.info.textContent = 'Kayıt bulunamadı.';
    } else {
      const startDisplay = startIndex + 1;
      const endDisplay = endIndex;
      state.info.textContent = `${startDisplay}–${endDisplay} / ${totalItems} kayıt`;
    }

    if (totalItems > 0) {
      renderPageButtons(state, totalPages);
      state.controls.classList.remove('d-none');
    } else {
      state.controls.classList.add('d-none');
    }
  }

  function createInstance(element) {
    const selector = element.getAttribute('data-paginate-items');
    const pageSize = readPageSize(element);
    const { controls, info, list, nav } = createControls(element);

    const state = {
      element,
      selector,
      pageSize,
      currentPage: 1,
      controls,
      info,
      list,
      nav,
      goto(page) {
        if (Number.isFinite(page)) {
          this.currentPage = page;
          apply(this);
        }
      },
      refresh() {
        apply(this);
      },
    };

    apply(state);
    return state;
  }

  function initElement(element) {
    if (!element || !(element instanceof Element)) {
      return null;
    }
    let instance = instances.get(element);
    if (!instance) {
      instance = createInstance(element);
      instances.set(element, instance);
    }
    return instance;
  }

  function initAll(root = document) {
    const elements = Array.from(root.querySelectorAll('[data-paginate]'));
    elements.forEach((element) => {
      initElement(element);
    });
  }

  function refresh(target = null) {
    if (!target) {
      instances.forEach((instance) => {
        instance.refresh();
      });
      return;
    }
    const container = getContainer(target);
    if (!container) {
      return;
    }
    const instance = initElement(container);
    if (instance) {
      instance.refresh();
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    initAll();
  });

  window.Pagination = {
    init: initAll,
    refresh,
    register: initElement,
  };
})();
