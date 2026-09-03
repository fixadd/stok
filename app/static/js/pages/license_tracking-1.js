document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector('[data-license-table]');
    if (!tableBody) {
      return;
    }
    const pagination = window.Pagination || null;
    const licenseTableEl = tableBody.closest('table');

    const bootstrapLib = window.bootstrap || null;
    const detailModalEl = document.getElementById('licenseDetailModal');
    const detailModal = detailModalEl && bootstrapLib ? new bootstrapLib.Modal(detailModalEl) : null;
    const detailEditButton = document.getElementById('licenseDetailEditButton');
    const historyList = document.getElementById('licenseHistoryList');
    const historyEmpty = document.getElementById('licenseHistoryEmpty');
    const searchInput = document.getElementById('licenseSearch');
    const emptyState = document.getElementById('licenseEmptyState');
    const actionAlert = document.getElementById('licenseActionAlert');

    const assignModalEl = document.getElementById('licenseAssignModal');
    const assignResponsibleSelect = document.getElementById('assignResponsibleSelect');
    const assignInventorySelect = document.getElementById('assignInventorySelect');
    const assignTitle = document.getElementById('assignModalTitle');

    const stockModalEl = document.getElementById('licenseStockModal');
    const stockNoteInput = document.getElementById('licenseStockNote');
    const stockSummary = stockModalEl?.querySelector('[data-license-stock="summary"]');
    const stockTitle = stockModalEl?.querySelector('[data-license-stock="title"]');
    const stockMessage = stockModalEl?.querySelector('[data-license-stock="message"]');
    const stockForm = document.getElementById('licenseStockForm');

    const editModalEl = document.getElementById('licenseEditModal');
    const editForm = document.getElementById('licenseEditForm');
    const editNameSelect = document.getElementById('editLicenseName');
    const editKeyInput = document.getElementById('editLicenseKey');
    const editResponsibleSelect = document.getElementById('editResponsibleSelect');
    const editInventorySelect = document.getElementById('editInventorySelect');
    const editIfsInput = document.getElementById('editIfsInput');
    const editEmailInput = document.getElementById('editEmailInput');
    const editStatusSelect = document.getElementById('editStatusSelect');

    const createModalEl = document.getElementById('licenseCreateModal');
    const createForm = document.getElementById('licenseCreateForm');
    const createNameSelect = document.getElementById('licenseCreateName');
    const createKeyInput = document.getElementById('licenseCreateKey');
    const licenseNameSelects = [createNameSelect, editNameSelect].filter(Boolean);

    let licenseNameOptionsLoaded = false;
    let licenseNameOptions = [];

    const detailFields = {
      title: detailModalEl?.querySelector('[data-detail-field="title"]'),
      subtitle: detailModalEl?.querySelector('[data-detail-field="subtitle"]'),
      number: detailModalEl?.querySelector('[data-detail-field="number"]'),
      name: detailModalEl?.querySelector('[data-detail-field="name"]'),
      key: detailModalEl?.querySelector('[data-detail-field="key"]'),
      status: detailModalEl?.querySelector('[data-detail-field="status"]'),
      responsible: detailModalEl?.querySelector('[data-detail-field="responsible"]'),
      department: detailModalEl?.querySelector('[data-detail-field="department"]'),
      inventory: detailModalEl?.querySelector('[data-detail-field="inventory"]'),
      factory: detailModalEl?.querySelector('[data-detail-field="factory"]'),
      email: detailModalEl?.querySelector('[data-detail-field="email"]'),
      ifs: detailModalEl?.querySelector('[data-detail-field="ifs"]'),
    };

    const counterElements = {
      total: document.querySelector('[data-license-counter="total"]'),
      active: document.querySelector('[data-license-counter="active"]'),
      passive: document.querySelector('[data-license-counter="passive"]'),
    };

    const licenseDataMap = new Map();
    let activeRow = null;
    let currentLicenseId = null;
    let alertTimer = null;

    const rows = () => Array.from(tableBody.querySelectorAll('tr[data-license-id]'));

    if (licenseNameSelects.length) {
      licenseNameOptions = licenseNameSelects
        .reduce((values, select) => {
          Array.from(select.options).forEach((option) => {
            if (option.value) {
              values.push(option.value);
            }
          });
          return values;
        }, [])
        .filter((value, index, array) => array.indexOf(value) === index)
        .sort((a, b) => a.localeCompare(b, 'tr-TR'));
    }

    refreshLicenseNameSelects();

    function escapeHtml(value) {
      if (value === undefined || value === null) {
        return '';
      }
      return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function refreshLicenseNameSelects() {
      if (!licenseNameSelects.length) {
        return;
      }
      licenseNameSelects.forEach((select) => {
        const currentValue = select.value;
        if (currentValue && !licenseNameOptions.includes(currentValue)) {
          licenseNameOptions.push(currentValue);
        }
      });
      licenseNameOptions = licenseNameOptions
        .filter((value, index, array) => value && array.indexOf(value) === index)
        .sort((a, b) => a.localeCompare(b, 'tr-TR'));
      licenseNameSelects.forEach((select) => {
        const currentValue = select.value;
        const fragment = document.createDocumentFragment();
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = 'Seçiniz';
        placeholder.disabled = true;
        placeholder.selected = !currentValue;
        fragment.appendChild(placeholder);
        licenseNameOptions.forEach((name) => {
          const option = document.createElement('option');
          option.value = name;
          option.textContent = name;
          if (name === currentValue) {
            option.selected = true;
          }
          fragment.appendChild(option);
        });
        select.innerHTML = '';
        select.appendChild(fragment);
        if (currentValue && !licenseNameOptions.includes(currentValue)) {
          select.value = '';
        }
      });
    }

    async function ensureLicenseNameOptions() {
      if (licenseNameOptionsLoaded) {
        return;
      }
      try {
        const response = await fetch('/api/license-names');
        if (!response.ok) {
          throw new Error('Yanıt alınamadı');
        }
        const payload = await response.json();
        if (!payload || !Array.isArray(payload.items)) {
          throw new Error('Geçersiz yanıt');
        }
        licenseNameOptions = payload.items
          .map((item) => item?.name)
          .filter((name, index, array) => name && array.indexOf(name) === index);
        licenseNameOptionsLoaded = true;
        refreshLicenseNameSelects();
      } catch (error) {
        console.warn('Lisans adları yüklenemedi.', error);
      }
    }

    function formatDateTime(date) {
      try {
        return new Intl.DateTimeFormat('tr-TR', {
          dateStyle: 'short',
          timeStyle: 'short',
        }).format(date);
      } catch (error) {
        return date.toLocaleString();
      }
    }

    function refreshLicenseRecord(data) {
      data.status_label = licenseStatusLabels[data.status] || data.status;
      const tokens = [
        data.display_name,
        data.key,
        data.responsible_name,
        data.responsible_department,
        data.email,
        data.inventory_no,
        data.inventory_label,
        data.status_label,
        data.raw_name,
      ].filter(Boolean);
      data.search_index = tokens.join(' ').toLowerCase();
      if (!Array.isArray(data.history)) {
        data.history = [];
      }
      return data;
    }

    function updateRow(licenseId) {
      const row = tableBody.querySelector(`[data-license-id="${licenseId}"]`);
      const data = licenseDataMap.get(licenseId);
      if (!row || !data) {
        return;
      }

      refreshLicenseRecord(data);

      row.dataset.searchIndex = data.search_index || '';
      row.dataset.license = JSON.stringify(data);
      row.classList.toggle('table-success', data.status === 'pasif');
      row.classList.toggle('is-passive', data.status === 'pasif');

      const numberField = row.querySelector('[data-field="row-number"]');
      const nameField = row.querySelector('[data-field="license-name"]');
      const keyField = row.querySelector('[data-field="license-key"]');
      const statusField = row.querySelector('[data-field="license-status"]');
      const responsibleField = row.querySelector('[data-field="license-responsible"]');
      const responsibleDeptField = row.querySelector('[data-field="license-responsible-department"]');
      const inventoryField = row.querySelector('[data-field="license-inventory"]');
      const inventoryLabelField = row.querySelector('[data-field="license-inventory-label"]');
      const emailField = row.querySelector('[data-field="license-email"]');

      if (numberField) {
        numberField.textContent = row.dataset.rowIndex || numberField.textContent;
      }
      if (nameField) {
        nameField.textContent = data.display_name || '—';
      }
      if (keyField) {
        keyField.textContent = data.key || '—';
      }
      if (statusField) {
        statusField.textContent = data.status_label || '—';
        statusField.className = `license-status-badge status-${data.status}`;
      }
      if (responsibleField) {
        responsibleField.textContent = data.responsible_name || 'Atama bekliyor';
      }
      if (responsibleDeptField) {
        responsibleDeptField.textContent = data.responsible_department || '—';
      }
      if (inventoryField) {
        inventoryField.textContent = data.inventory_no || '—';
      }
      if (inventoryLabelField) {
        inventoryLabelField.textContent = data.inventory_label || '—';
      }
      if (emailField) {
        emailField.textContent = data.email || '—';
      }

      if (activeRow === row) {
        populateDetail(data, row);
      }
    }

    function populateHistory(data) {
      if (!historyList || !historyEmpty) {
        return;
      }

      historyList.innerHTML = '';
      if (!data.history || !data.history.length) {
        historyList.classList.add('d-none');
        historyEmpty.classList.remove('d-none');
        return;
      }

      historyList.classList.remove('d-none');
      historyEmpty.classList.add('d-none');

      data.history.forEach((entry) => {
        const item = document.createElement('li');
        item.className = 'list-group-item license-history-item';
        item.innerHTML = `
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <div class="fw-semibold">${escapeHtml(entry.title)}</div>
              ${entry.note ? `<div class="text-muted small mt-1">${escapeHtml(entry.note)}</div>` : ''}
            </div>
            <div class="text-end">
              <div class="text-muted small">${escapeHtml(entry.performed_at || '')}</div>
              ${entry.actor ? `<div class="text-muted small">${escapeHtml(entry.actor)}</div>` : ''}
            </div>
          </div>`;
        historyList.appendChild(item);
      });
    }

    function populateDetail(data, row) {
      if (!detailModalEl) {
        return;
      }
      if (detailFields.title) {
        detailFields.title.textContent = data.display_name || 'Lisans Detayı';
      }
      if (detailFields.subtitle) {
        const subtitleParts = [];
        if (data.inventory_label || data.inventory_no) {
          subtitleParts.push(data.inventory_label || data.inventory_no);
        }
        if (data.responsible_name) {
          subtitleParts.push(data.responsible_name);
        }
        detailFields.subtitle.textContent = subtitleParts.length
          ? subtitleParts.join(' • ')
          : 'Seçilen lisansa ait güncel bilgiler';
      }
      if (detailFields.number) {
        detailFields.number.textContent = row?.dataset.rowIndex || '—';
      }
      if (detailFields.name) {
        detailFields.name.textContent = data.display_name || '—';
      }
      if (detailFields.key) {
        detailFields.key.textContent = data.key || '—';
      }
      if (detailFields.status) {
        detailFields.status.textContent = data.status_label || '—';
        detailFields.status.className = `license-status-badge status-${data.status}`;
      }
      if (detailFields.responsible) {
        detailFields.responsible.textContent = data.responsible_name || 'Atama bekliyor';
      }
      if (detailFields.department) {
        detailFields.department.textContent = data.responsible_department || '—';
      }
      if (detailFields.inventory) {
        detailFields.inventory.textContent = data.inventory_label || data.inventory_no || '—';
      }
      if (detailFields.factory) {
        detailFields.factory.textContent = data.factory || '—';
      }
      if (detailFields.email) {
        detailFields.email.textContent = data.email || '—';
      }
      if (detailFields.ifs) {
        detailFields.ifs.textContent = data.ifs_no || '—';
      }
      if (detailEditButton) {
        detailEditButton.dataset.licenseId = String(data.id);
      }
      populateHistory(data);
    }

    function setActiveRow(row) {
      if (activeRow) {
        activeRow.classList.remove('active-license-row');
      }
      activeRow = row || null;
      if (activeRow) {
        activeRow.classList.add('active-license-row');
      }
    }

    function showFeedback(message, type = 'info') {
      if (!actionAlert) {
        return;
      }
      const variantMap = {
        success: 'alert-success',
        info: 'alert-primary',
        warning: 'alert-warning',
      };
      actionAlert.textContent = message;
      actionAlert.classList.remove('d-none', 'alert-success', 'alert-primary', 'alert-warning', 'show');
      const variant = variantMap[type] || 'alert-primary';
      actionAlert.classList.add('show', variant);
      if (alertTimer) {
        clearTimeout(alertTimer);
      }
      alertTimer = window.setTimeout(() => {
        actionAlert.classList.remove('show', variant);
        actionAlert.classList.add('d-none');
      }, 3600);
    }

    function refreshRowNumbers() {
      rows().forEach((row, index) => {
        const numberField = row.querySelector('[data-field="row-number"]');
        row.dataset.rowIndex = String(index + 1);
        if (numberField) {
          numberField.textContent = String(index + 1);
        }
      });
    }

    function refreshCounters() {
      if (!counterElements.total) {
        return;
      }
      let activeCount = 0;
      let passiveCount = 0;
      licenseDataMap.forEach((record) => {
        if (record.status === 'pasif') {
          passiveCount += 1;
        } else if (record.status === 'aktif') {
          activeCount += 1;
        }
      });
      const totalCount = licenseDataMap.size;
      counterElements.total.textContent = String(totalCount);
      if (counterElements.active) {
        counterElements.active.textContent = String(activeCount);
      }
      if (counterElements.passive) {
        counterElements.passive.textContent = String(passiveCount);
      }
    }

    function isDetailModalVisible() {
      if (!detailModalEl) {
        return false;
      }
      return detailModalEl.classList.contains('show');
    }

    function updateDetailIfVisible(licenseId) {
      if (!isDetailModalVisible()) {
        return;
      }
      if (currentLicenseId !== licenseId) {
        return;
      }
      const row = tableBody.querySelector(`[data-license-id="${licenseId}"]`);
      const data = licenseDataMap.get(licenseId);
      if (row && data) {
        populateDetail(data, row);
      }
    }

    function markPassive(licenseId) {
      const data = licenseDataMap.get(licenseId);
      if (!data) {
        return;
      }
      data.status = 'pasif';
      data.history.unshift({
        title: 'Durum güncellendi',
        actor: 'Sistem',
        note: 'Lisans pasif durumuna alındı.',
        performed_at: formatDateTime(new Date()),
      });
      refreshLicenseRecord(data);
      updateRow(licenseId);
      updateDetailIfVisible(licenseId);
      showFeedback('Lisans pasif durumuna alındı. Atama yapılana kadar satır yeşil kalacak.', 'info');
      refreshCounters();
    }

    function applySearch() {
      if (!searchInput) {
        return;
      }
      const query = searchInput.value.trim().toLowerCase();
      let visibleCount = 0;
      rows().forEach((row) => {
        const matches = !query || (row.dataset.searchIndex || '').includes(query);
        if (matches) {
          delete row.dataset.searchHidden;
          visibleCount += 1;
        } else {
          row.dataset.searchHidden = 'true';
        }
        row.classList.toggle('d-none', !matches);
      });
      if (emptyState) {
        emptyState.classList.toggle('d-none', visibleCount > 0);
      }
      if (pagination && licenseTableEl) {
        pagination.refresh(licenseTableEl);
      }
    }

    function attachRowEvents(row) {
      const detailButton = row.querySelector('.license-detail-trigger');
      if (detailButton) {
        detailButton.addEventListener('click', () => {
          const licenseId = Number(row.dataset.licenseId);
          const data = licenseDataMap.get(licenseId);
          if (!data) {
            return;
          }
          currentLicenseId = licenseId;
          setActiveRow(row);
          populateDetail(data, row);
          if (detailModal) {
            detailModal.show();
          } else if (detailModalEl) {
            detailModalEl.classList.add('show');
          }
        });
      }

      row.querySelectorAll('.license-action').forEach((button) => {
        button.addEventListener('click', (event) => {
          const action = button.dataset.action;
          const licenseId = Number(button.dataset.licenseId);
          currentLicenseId = licenseId;
          if (action === 'passive') {
            event.preventDefault();
            markPassive(licenseId);
          } else if (action === 'stock' && !stockModalEl) {
            event.preventDefault();
          }
        });
      });
    }

    function buildRow(data) {
      const row = document.createElement('tr');
      row.classList.add('license-row');
      if (data.status === 'pasif') {
        row.classList.add('table-success', 'is-passive');
      }
      row.dataset.licenseId = String(data.id);
      row.dataset.searchIndex = data.search_index || '';
      row.dataset.license = JSON.stringify(data);

      row.innerHTML = `
        <td><span class="fw-semibold" data-field="row-number"></span></td>
        <td>
          <div class="fw-semibold" data-field="license-name">${escapeHtml(data.display_name || 'Lisans')}</div>
          <div class="small mt-1"><span class="license-status-badge status-${data.status}" data-field="license-status">${escapeHtml(data.status_label || '')}</span></div>
        </td>
        <td><span class="fw-semibold" data-field="license-key">${escapeHtml(data.key || '—')}</span></td>
        <td>
          <div class="fw-semibold" data-field="license-responsible">${escapeHtml(data.responsible_name || 'Atama bekliyor')}</div>
          <div class="text-muted small" data-field="license-responsible-department">${escapeHtml(data.responsible_department || '—')}</div>
        </td>
        <td>
          <div class="fw-semibold" data-field="license-inventory">${escapeHtml(data.inventory_no || '—')}</div>
          <div class="text-muted small" data-field="license-inventory-label">${escapeHtml(data.inventory_label || '—')}</div>
        </td>
        <td><span data-field="license-email">${escapeHtml(data.email || '—')}</span></td>
        <td class="text-end">
          <div class="d-inline-flex align-items-center gap-2">
            <button class="btn btn-outline-secondary btn-sm icon-button license-detail-trigger" type="button" data-license-id="${data.id}">
              <i class="bi bi-eye"></i>
            </button>
            <div class="dropdown">
              <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown" data-bs-display="static" aria-expanded="false">Seçiniz…</button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li><button class="dropdown-item license-action" type="button" data-action="assign" data-license-id="${data.id}" data-bs-toggle="modal" data-bs-target="#licenseAssignModal">Atama Yap</button></li>
                <li><button class="dropdown-item license-action" type="button" data-action="edit" data-license-id="${data.id}" data-bs-toggle="modal" data-bs-target="#licenseEditModal">Düzenle</button></li>
                <li><button class="dropdown-item license-action" type="button" data-action="stock" data-license-id="${data.id}" data-bs-toggle="modal" data-bs-target="#licenseStockModal">Stok Girişi</button></li>
                <li><button class="dropdown-item license-action" type="button" data-action="passive" data-license-id="${data.id}">Pasif</button></li>
              </ul>
            </div>
          </div>
        </td>`;
    tableBody.appendChild(row);
    if (pagination && licenseTableEl) {
      pagination.refresh(licenseTableEl);
    }
      return row;
    }

    rows().forEach((row) => {
      try {
        const data = JSON.parse(row.dataset.license || '{}');
        licenseDataMap.set(data.id, data);
        attachRowEvents(row);
      } catch (error) {
        // ignore malformed rows
      }
    });
    refreshRowNumbers();

    let nextLicenseId = 1;
    if (licenseDataMap.size) {
      nextLicenseId = Math.max(...Array.from(licenseDataMap.keys())) + 1;
    }

    if (searchInput) {
      searchInput.addEventListener('input', applySearch);
    }

    if (detailModalEl && bootstrapLib) {
      detailModalEl.addEventListener('hidden.bs.modal', () => {
        setActiveRow(null);
        currentLicenseId = null;
      });
    }

    if (createModalEl) {
      createModalEl.addEventListener('show.bs.modal', () => {
        ensureLicenseNameOptions();
      });
    }

    if (assignModalEl) {
      assignModalEl.addEventListener('show.bs.modal', (event) => {
        const trigger = event.relatedTarget;
        const licenseId = Number(trigger?.dataset.licenseId || currentLicenseId);
        currentLicenseId = licenseId;
        const data = licenseDataMap.get(licenseId);
        if (!data) {
          return;
        }
        assignTitle.textContent = data.display_name || 'Lisans';
        assignResponsibleSelect.value = data.responsible_id ? String(data.responsible_id) : '';
        assignInventorySelect.value = data.inventory_id ? String(data.inventory_id) : '';
      });
    }

    if (stockModalEl) {
      stockModalEl.addEventListener('show.bs.modal', (event) => {
        const trigger = event.relatedTarget;
        const licenseId = Number(trigger?.dataset.licenseId || currentLicenseId);
        currentLicenseId = licenseId;
        const data = licenseDataMap.get(licenseId);
        if (!data) {
          return;
        }
        if (stockTitle) {
          stockTitle.textContent = `${data.display_name || 'Lisans'} stoğa taşınıyor`;
        }
        if (stockMessage) {
          stockMessage.textContent = 'Bu lisans stok takip sayfasına aktarılacaktır.';
        }
        if (stockSummary) {
          const summaryParts = [];
          if (data.inventory_no) summaryParts.push(data.inventory_no);
          if (data.responsible_name && data.responsible_name !== 'Atama bekliyor') {
            summaryParts.push(data.responsible_name);
          }
          stockSummary.textContent = summaryParts.length ? summaryParts.join(' • ') : 'Herhangi bir atama bulunmuyor.';
        }
        if (stockNoteInput) {
          stockNoteInput.value = '';
        }
      });
    }

    if (editModalEl) {
      editModalEl.addEventListener('show.bs.modal', (event) => {
        ensureLicenseNameOptions();
        const trigger = event.relatedTarget;
        const licenseId = Number(trigger?.dataset.licenseId || currentLicenseId);
        currentLicenseId = licenseId;
        const data = licenseDataMap.get(licenseId);
        if (!data) {
          return;
        }
        if (editNameSelect) {
          refreshLicenseNameSelects();
          editNameSelect.value = data.display_name || '';
        }
        editKeyInput.value = data.key || '';
        editResponsibleSelect.value = data.responsible_id ? String(data.responsible_id) : '';
        editInventorySelect.value = data.inventory_id ? String(data.inventory_id) : '';
        editIfsInput.value = data.ifs_no || '';
        editEmailInput.value = data.email || '';
        editStatusSelect.value = data.status || 'aktif';
      });
      editModalEl.addEventListener('hidden.bs.modal', () => {
        if (editForm) {
          editForm.reset();
        }
        refreshLicenseNameSelects();
        editStatusSelect.value = 'aktif';
      });
    }

    const assignSubmitButton = document.getElementById('licenseAssignSubmit');
    if (assignSubmitButton) {
      assignSubmitButton.addEventListener('click', () => {
        if (!currentLicenseId) {
          return;
        }
        const data = licenseDataMap.get(currentLicenseId);
        if (!data) {
          return;
        }
        const selectedUser = licenseUsers.find((user) => String(user.id) === assignResponsibleSelect.value);
        const selectedInventory = licenseInventories.find((inv) => String(inv.id) === assignInventorySelect.value);

        data.responsible_id = selectedUser ? selectedUser.id : null;
        data.responsible_name = selectedUser ? selectedUser.name : 'Atama bekliyor';
        data.responsible_department = selectedUser ? selectedUser.department : '';
        data.email = selectedUser ? selectedUser.email : '';
        data.inventory_id = selectedInventory ? selectedInventory.id : null;
        data.inventory_no = selectedInventory ? selectedInventory.inventory_no : '';
        data.inventory_label = selectedInventory ? selectedInventory.label : '';
        if (!data.ifs_no && selectedInventory) {
          data.ifs_no = selectedInventory.ifs_no || '';
        }
        data.status = 'aktif';
        refreshLicenseRecord(data);
        data.history.unshift({
          title: 'Atama yapıldı',
          actor: selectedUser ? selectedUser.name : 'Sistem',
          note: selectedInventory ? `${selectedInventory.label} envanterine bağlandı.` : 'Sorumlu güncellendi.',
          performed_at: formatDateTime(new Date()),
        });
        updateRow(currentLicenseId);
        updateDetailIfVisible(currentLicenseId);
        showFeedback('Lisans ataması güncellendi.', 'success');
        const modalInstance = bootstrap.Modal.getInstance(assignModalEl);
        modalInstance?.hide();
        refreshCounters();
      });
    }

    if (stockForm) {
      stockForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!currentLicenseId) {
          return;
        }
        const noteValue = stockNoteInput ? stockNoteInput.value.trim() : '';
        try {
          const response = await fetch(`/api/licenses/${currentLicenseId}/stock`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note: noteValue, performed_by: defaultActor }),
          });
          let payload = {};
          try {
            payload = await response.json();
          } catch (error) {
            payload = {};
          }
          if (!response.ok) {
            showFeedback(payload.error || 'İşlem tamamlanamadı.', 'danger');
            return;
          }

          if (payload.license) {
            refreshLicenseRecord(payload.license);
            updateRow(currentLicenseId);
            updateDetailIfVisible(currentLicenseId);
            refreshCounters();
          }
          showFeedback(payload.message || 'Lisans stok listesine taşındı.', 'success');
          if (stockModalEl && bootstrapLib) {
            bootstrapLib.Modal.getInstance(stockModalEl)?.hide();
          }
        } catch (error) {
          showFeedback('Sunucuya ulaşılamadı.', 'danger');
        }
      });
    }

    const editSubmitButton = document.getElementById('licenseEditSubmit');
    if (editSubmitButton) {
      editSubmitButton.addEventListener('click', () => {
        if (!currentLicenseId) {
          return;
        }
        const data = licenseDataMap.get(currentLicenseId);
        if (!data) {
          return;
        }
        if (!editNameSelect.value) {
          editNameSelect.reportValidity();
          return;
        }
        data.display_name = editNameSelect.value;
        data.key = editKeyInput.value.trim();
        data.raw_name = data.key ? `${data.display_name} - ${data.key}` : data.display_name;

        const selectedUser = licenseUsers.find((user) => String(user.id) === editResponsibleSelect.value);
        const selectedInventory = licenseInventories.find((inv) => String(inv.id) === editInventorySelect.value);

        data.responsible_id = selectedUser ? selectedUser.id : null;
        data.responsible_name = selectedUser ? selectedUser.name : 'Atama bekliyor';
        data.responsible_department = selectedUser ? selectedUser.department : '';
        data.email = editEmailInput.value.trim() || (selectedUser ? selectedUser.email : '');
        data.inventory_id = selectedInventory ? selectedInventory.id : null;
        data.inventory_no = selectedInventory ? selectedInventory.inventory_no : '';
        data.inventory_label = selectedInventory ? selectedInventory.label : '';
        data.ifs_no = editIfsInput.value.trim();
        data.status = editStatusSelect.value || data.status;

        if (data.display_name && !licenseNameOptions.includes(data.display_name)) {
          licenseNameOptions.push(data.display_name);
          licenseNameOptionsLoaded = true;
          refreshLicenseNameSelects();
        }

        refreshLicenseRecord(data);
        data.history.unshift({
          title: 'Lisans düzenlendi',
          actor: selectedUser ? selectedUser.name : 'Sistem',
          note: 'Lisans bilgileri güncellendi.',
          performed_at: formatDateTime(new Date()),
        });
        updateRow(currentLicenseId);
        updateDetailIfVisible(currentLicenseId);
        showFeedback('Lisans bilgileri güncellendi.', 'success');
        const modalInstance = bootstrap.Modal.getInstance(editModalEl);
        modalInstance?.hide();
        refreshCounters();
      });
    }

    const createSubmitButton = document.getElementById('licenseCreateSubmit');
    if (createSubmitButton) {
      createSubmitButton.addEventListener('click', () => {
        if (!createNameSelect.value || !createKeyInput.value.trim()) {
          createNameSelect.reportValidity();
          createKeyInput.reportValidity();
          return;
        }
        const displayName = createNameSelect.value;
        const keyValue = createKeyInput.value.trim();
        const newId = nextLicenseId++;
        const newData = {
          id: newId,
          display_name: displayName,
          key: keyValue,
          raw_name: `${displayName} - ${keyValue}`,
          status: 'pasif',
          status_label: licenseStatusLabels.pasif,
          responsible_id: null,
          responsible_name: 'Atama bekliyor',
          responsible_department: '',
          email: '',
          inventory_id: null,
          inventory_no: '',
          inventory_label: '',
          factory: '',
          department: '',
          ifs_no: '',
          history: [],
        };
        refreshLicenseRecord(newData);
        const newRow = buildRow(newData);
        licenseDataMap.set(newId, newData);
        attachRowEvents(newRow);
        refreshRowNumbers();
        updateRow(newId);
        showFeedback('Yeni lisans kaydı eklendi. Atama yapılana kadar pasif durumdadır.', 'success');
        const modalInstance = bootstrap.Modal.getInstance(createModalEl);
        modalInstance?.hide();
        if (!licenseNameOptions.includes(displayName)) {
          licenseNameOptions.push(displayName);
          licenseNameOptionsLoaded = true;
        }
        createForm.reset();
        refreshLicenseNameSelects();
        applySearch();
        refreshCounters();
      });
    }

    rows().forEach((row) => {
      const data = licenseDataMap.get(Number(row.dataset.licenseId));
      if (!data) {
        return;
      }
      refreshLicenseRecord(data);
      updateRow(data.id);
    });

    refreshCounters();
    applySearch();
  });\n