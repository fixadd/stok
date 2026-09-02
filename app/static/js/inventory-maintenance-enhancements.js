(function () {
  "use strict";

  function init() {
    const detailModalEl = document.getElementById("inventoryDetailModal");
    const maintenanceModalEl = document.getElementById("inventoryMaintenanceModal");
    const maintenanceButton = document.getElementById("inventoryMaintenanceButton");
    const refreshButton = document.getElementById("inventoryRefreshDetailButton");
    const maintenanceList = document.getElementById("inventoryMaintenanceList");
    const maintenanceEmpty = document.getElementById("inventoryMaintenanceEmpty");
    const maintenanceCount = document.getElementById("inventoryMaintenanceCount");
    const maintenanceTitle = document.getElementById("inventoryMaintenanceTitle");
    const maintenanceSubtitle = document.getElementById("inventoryMaintenanceSubtitle");
    const maintenanceAlert = document.getElementById("inventoryMaintenanceAlert");

    if (!detailModalEl || !maintenanceModalEl) {
      return;
    }

    const bootstrapLib = window.bootstrap;
    const detailModal = bootstrapLib
      ? bootstrapLib.Modal.getOrCreateInstance(detailModalEl)
      : null;
    const maintenanceModal = bootstrapLib
      ? bootstrapLib.Modal.getOrCreateInstance(maintenanceModalEl)
      : null;

    let activeItemId = null;
    let alertTimer = null;

    function currentItemId() {
      return Number(
        activeItemId ||
        detailModalEl.dataset.itemId ||
        maintenanceModalEl.dataset.itemId ||
        0
      );
    }

    function inventoryRow(itemId) {
      return document.querySelector(`tr[data-item-id="${Number(itemId)}"]`);
    }

    function rowValue(row, field) {
      const el = row?.querySelector(`[data-field="${field}"]`);
      return el?.textContent?.trim() || "";
    }

    function formatDate(value) {
      if (!value) return "—";
      const raw = String(value);
      if (raw.includes("T")) {
        const [date, timePart] = raw.split("T");
        if (/^\d{4}-\d{2}-\d{2}$/.test(date)) {
          const [year, month, day] = date.split("-");
          return `${day}.${month}.${year}${timePart ? ` ${timePart.slice(0, 5)}` : ""}`;
        }
      }
      return raw;
    }

    function inputDate(value) {
      if (!value) return "";
      const raw = String(value);
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(raw)) return raw.slice(0, 16);
      if (/^\d{2}\.\d{2}\.\d{4}( \d{2}:\d{2})?$/.test(raw)) {
        const [date, time = "00:00"] = raw.split(" ");
        const [day, month, year] = date.split(".");
        return `${year}-${month}-${day}T${time}`;
      }
      return "";
    }

    function showAlert(message, variant = "success") {
      if (!maintenanceAlert) return;
      maintenanceAlert.textContent = message;
      maintenanceAlert.className = `alert alert-${variant}`;
      maintenanceAlert.classList.remove("d-none");
      if (alertTimer) window.clearTimeout(alertTimer);
      alertTimer = window.setTimeout(() => maintenanceAlert.classList.add("d-none"), 3500);
    }

    function renderMaintenance(records) {
      if (!maintenanceList || !maintenanceEmpty) return;
      const list = Array.isArray(records) ? [...records] : [];
      list.sort((a, b) => String(b.performed_at || "").localeCompare(String(a.performed_at || "")));
      maintenanceList.innerHTML = "";
      if (maintenanceCount) maintenanceCount.textContent = String(list.length);

      if (!list.length) {
        maintenanceEmpty.classList.remove("d-none");
        return;
      }
      maintenanceEmpty.classList.add("d-none");

      list.forEach((record) => {
        const card = document.createElement("div");
        card.className = "card border-0 shadow-sm mb-3 maintenance-history-card";

        const body = document.createElement("div");
        body.className = "card-body";

        const header = document.createElement("div");
        header.className = "d-flex justify-content-between align-items-start gap-3";

        const left = document.createElement("div");
        const date = document.createElement("div");
        date.className = "fw-semibold";
        date.textContent = formatDate(record.performed_at);
        const actor = document.createElement("div");
        actor.className = "text-muted small mt-1";
        actor.textContent = record.performed_by || "Belirtilmemiş";
        left.append(date, actor);

        const actions = document.createElement("div");
        actions.className = "d-flex gap-1 flex-shrink-0";

        const edit = document.createElement("button");
        edit.type = "button";
        edit.className = "btn btn-sm btn-outline-secondary";
        edit.title = "Düzenle";
        edit.innerHTML = '<i class="bi bi-pencil"></i>';
        edit.addEventListener("click", () => openForm(record));

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn-sm btn-outline-danger";
        remove.title = "Sil";
        remove.innerHTML = '<i class="bi bi-trash"></i>';
        remove.addEventListener("click", () => deleteRecord(record));

        actions.append(edit, remove);
        header.append(left, actions);
        body.append(header);

        if (record.note) {
          const note = document.createElement("div");
          note.className = "mt-3 p-3 rounded bg-light";
          note.textContent = record.note;
          body.append(note);
        }

        card.append(body);
        maintenanceList.append(card);
      });
    }

    async function loadRecords(itemId) {
      const response = await fetch(`/api/inventory/${Number(itemId)}/maintenance`, {
        method: "GET",
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || "Bakım kayıtları alınamadı.");

      const records = Array.isArray(payload)
        ? payload
        : (payload.maintenances || payload.records || payload.items || []);

      renderMaintenance(records);
      return records;
    }

    function openForm(record = null) {
      const formModalEl = document.getElementById("inventoryMaintenanceFormModal");
      const form = document.getElementById("inventoryMaintenanceForm");
      const editId = document.getElementById("inventoryMaintenanceEditId");
      const performedAt = document.getElementById("inventoryMaintenancePerformedAt");
      const performedBy = document.getElementById("inventoryMaintenancePerformedBy");
      const note = document.getElementById("inventoryMaintenanceNote");
      const title = document.getElementById("inventoryMaintenanceFormTitle");
      const submit = document.getElementById("inventoryMaintenanceSubmitButton");
      if (!formModalEl) return;

      const itemId = currentItemId();
      if (!itemId) {
        showAlert("Envanter bilgisi bulunamadı.", "danger");
        return;
      }
      activeItemId = itemId;
      detailModalEl.dataset.itemId = String(itemId);

      form?.reset();
      const now = new Date();
      const pad = (v) => String(v).padStart(2, "0");

      if (editId) editId.value = record?.id ? String(record.id) : "";
      if (performedAt) {
        performedAt.value = record?.performed_at
          ? inputDate(record.performed_at)
          : `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
      }
      if (performedBy) performedBy.value = record?.performed_by || "";
      if (note) note.value = record?.note || "";
      if (title) title.textContent = record ? "Bakım Kaydını Düzenle" : "Yeni Bakım Kaydı";
      if (submit) submit.innerHTML = record
        ? '<i class="bi bi-check-lg me-1"></i> Güncelle'
        : '<i class="bi bi-check-lg me-1"></i> Kaydet';

      if (bootstrapLib) bootstrapLib.Modal.getOrCreateInstance(formModalEl).show();
      else formModalEl.classList.add("show");
    }

    async function deleteRecord(record) {
      const itemId = currentItemId();
      if (!itemId || !record?.id) return;
      if (!window.confirm("Bu bakım kaydını silmek istediğinize emin misiniz?")) return;

      try {
        const response = await fetch(`/api/inventory/${itemId}/maintenance/${Number(record.id)}`, {
          method: "DELETE",
          credentials: "same-origin",
          headers: { Accept: "application/json" }
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || "Bakım kaydı silinemedi.");
        await loadRecords(itemId);
        showAlert("Bakım kaydı silindi.", "success");
      } catch (error) {
        showAlert(error.message || "Sunucuya ulaşılamadı.", "danger");
      }
    }

    async function openMaintenance() {
      const itemId = Number(detailModalEl.dataset.itemId || activeItemId || 0);
      if (!itemId) return;
      activeItemId = itemId;
      detailModalEl.dataset.itemId = String(itemId);
      maintenanceModalEl.dataset.itemId = String(itemId);

      const row = inventoryRow(itemId);
      const inventoryNo = rowValue(row, "inventory_no") || `#${itemId}`;
      const computer = rowValue(row, "computer_name");
      const responsible = rowValue(row, "responsible");
      const factory = rowValue(row, "factory");

      if (maintenanceTitle) maintenanceTitle.textContent = `${inventoryNo} - Bakım Geçmişi`;
      if (maintenanceSubtitle) {
        maintenanceSubtitle.textContent = [computer, responsible, factory].filter(Boolean).join(" • ") || "Envantere ait bakım kayıtları.";
      }

      if (detailModal) detailModal.hide();
      window.setTimeout(() => {
        // Keep the selected inventory available for the existing CRUD handlers.
        detailModalEl.dataset.itemId = String(itemId);
        activeItemId = itemId;
        if (maintenanceModal) maintenanceModal.show();
        else maintenanceModalEl.classList.add("show");
        loadRecords(itemId).catch((error) => showAlert(error.message || "Bakım kayıtları alınamadı.", "danger"));
      }, 180);
    }

    if (maintenanceButton) {
      maintenanceButton.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopImmediatePropagation();
        openMaintenance();
      }, true);
    }

    const newButton = document.getElementById("inventoryMaintenanceNewButton");
    if (newButton) {
      newButton.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopImmediatePropagation();
        openForm();
      }, true);
    }

    if (refreshButton) {
      refreshButton.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopImmediatePropagation();
        const itemId = currentItemId();
        if (!itemId) return;
        refreshButton.disabled = true;
        refreshButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Yenileniyor...';
        window.location.reload();
      }, true);
    }

    if (maintenanceModalEl) {
      maintenanceModalEl.addEventListener("hidden.bs.modal", () => {
        if (activeItemId) detailModalEl.dataset.itemId = String(activeItemId);
      });
    }

    detailModalEl.addEventListener("show.bs.modal", () => {
      const id = Number(detailModalEl.dataset.itemId || 0);
      if (id) activeItemId = id;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
