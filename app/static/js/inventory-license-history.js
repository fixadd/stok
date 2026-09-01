(() => {
  function init() {
    const inventoryDetailModal = document.getElementById("inventoryDetailModal");
    const licenseList = document.getElementById("inventoryLicenseList");
    const licenseDetailModal = document.getElementById("inventoryLicenseDetailModal");
    const historyList = document.getElementById("inventoryLicenseHistoryList");
    const historyEmpty = document.getElementById("inventoryLicenseHistoryEmpty");

    if (!inventoryDetailModal || !licenseList || !licenseDetailModal || !historyList) {
      return;
    }

    const bootstrapLib = window.bootstrap;
    let activeLicenseId = null;

    const statusLabels = {
      aktif: "Aktif",
      pasif: "Pasif",
      beklemede: "Beklemede",
    };

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "'": "&#39;",
        '"': "&quot;",
      })[char]);
    }

    function setHistory(history) {
      historyList.innerHTML = "";
      if (!Array.isArray(history) || history.length === 0) {
        historyList.classList.add("d-none");
        if (historyEmpty) {
          historyEmpty.classList.remove("d-none");
          historyEmpty.textContent = "Kayıt bulunamadı.";
        }
        return;
      }

      historyList.classList.remove("d-none");
      historyEmpty?.classList.add("d-none");
      history.forEach((entry) => {
        const li = document.createElement("li");
        li.className = "list-group-item license-history-item";
        li.innerHTML = `
          <div class="d-flex justify-content-between align-items-start gap-3">
            <div>
              <div class="fw-semibold">${escapeHtml(entry.title)}</div>
              ${entry.note ? `<div class="text-muted small mt-1">${escapeHtml(entry.note)}</div>` : ""}
            </div>
            <div class="text-end flex-shrink-0">
              <div class="text-muted small">${escapeHtml(entry.performed_at)}</div>
              ${entry.actor ? `<div class="text-muted small">${escapeHtml(entry.actor)}</div>` : ""}
            </div>
          </div>`;
        historyList.appendChild(li);
      });
    }

    function fillLicenseDetail(record) {
      const fields = {
        title: licenseDetailModal.querySelector('[data-license-detail-field="title"]'),
        subtitle: licenseDetailModal.querySelector('[data-license-detail-field="subtitle"]'),
        name: licenseDetailModal.querySelector('[data-license-detail-field="name"]'),
        key: licenseDetailModal.querySelector('[data-license-detail-field="key"]'),
        status: licenseDetailModal.querySelector('[data-license-detail-field="status"]'),
        responsible: licenseDetailModal.querySelector('[data-license-detail-field="responsible"]'),
        department: licenseDetailModal.querySelector('[data-license-detail-field="department"]'),
        email: licenseDetailModal.querySelector('[data-license-detail-field="email"]'),
        inventory: licenseDetailModal.querySelector('[data-license-detail-field="inventory"]'),
        factory: licenseDetailModal.querySelector('[data-license-detail-field="factory"]'),
        ifs: licenseDetailModal.querySelector('[data-license-detail-field="ifs"]'),
      };

      if (fields.title) fields.title.textContent = record.display_name || record.raw_name || "Lisans Detayı";
      if (fields.subtitle) fields.subtitle.textContent = [record.inventory_label || record.inventory_no, record.responsible_name].filter(Boolean).join(" • ") || "Bağlı envanter bilgileri";
      if (fields.name) fields.name.textContent = record.display_name || record.raw_name || "—";
      if (fields.key) fields.key.textContent = record.key || "—";
      if (fields.status) {
        const status = (record.status || "aktif").toLowerCase();
        fields.status.textContent = statusLabels[status] || status;
        fields.status.className = `license-status-badge status-${status}`;
      }
      if (fields.responsible) fields.responsible.textContent = record.responsible_name || "—";
      if (fields.department) fields.department.textContent = record.responsible_department || record.department || "—";
      if (fields.email) fields.email.textContent = record.email || "—";
      if (fields.inventory) fields.inventory.textContent = record.inventory_label || record.inventory_no || "—";
      if (fields.factory) fields.factory.textContent = record.factory || "—";
      if (fields.ifs) fields.ifs.textContent = record.ifs_no || "—";
    }

    async function openLicense(licenseId) {
      activeLicenseId = String(licenseId);
      try {
        const response = await fetch(`/api/licenses/${encodeURIComponent(activeLicenseId)}/history`, {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.error || "Lisans geçmişi alınamadı.");
        }

        const licenseResponse = await fetch("/api/licenses", {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        });
        const licensePayload = await licenseResponse.json().catch(() => ({}));
        const record = Array.isArray(licensePayload.items)
          ? licensePayload.items.find((item) => String(item.id) === activeLicenseId)
          : null;

        if (record) {
          fillLicenseDetail(record);
        }
        setHistory(payload.history);
        bootstrapLib?.Modal.getOrCreateInstance(licenseDetailModal).show();
      } catch (error) {
        historyList.innerHTML = "";
        historyList.classList.add("d-none");
        if (historyEmpty) {
          historyEmpty.classList.remove("d-none");
          historyEmpty.textContent = error.message || "Lisans geçmişi alınamadı.";
        }
      }
    }

    async function refreshInventoryLicenses(itemId) {
      try {
        const response = await fetch(`/api/inventory/${Number(itemId)}/licenses`, {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.error || "Bağlı lisanslar alınamadı.");
        }

        const items = Array.isArray(payload.items) ? payload.items : [];
        licenseList.innerHTML = "";

        if (!items.length) {
          const empty = document.createElement("li");
          empty.className = "list-group-item text-muted fst-italic";
          empty.textContent = "Bu envantere bağlı lisans bulunmuyor.";
          licenseList.appendChild(empty);
          return;
        }

        items.forEach((record) => {
          const li = document.createElement("li");
          li.className = "list-group-item d-flex align-items-center gap-3";

          const button = document.createElement("button");
          button.type = "button";
          button.className = "inventory-license-link flex-grow-1 text-start";
          button.dataset.licenseId = String(record.id);
          button.textContent = record.display_name || record.raw_name || "Lisans";

          const badge = document.createElement("span");
          badge.className = "badge rounded-pill inventory-license-badge";
          const status = (record.status || "aktif").toLowerCase();
          badge.textContent = statusLabels[status] || status;

          li.append(button, badge);
          licenseList.appendChild(li);
        });
      } catch (error) {
        // Existing inventory detail rendering remains visible if this refresh fails.
      }
    }

    inventoryDetailModal.addEventListener("shown.bs.modal", () => {
      const itemId = inventoryDetailModal.dataset.itemId;
      if (itemId) {
        refreshInventoryLicenses(itemId);
      }
    });

    inventoryDetailModal.addEventListener("click", (event) => {
      const trigger = event.target.closest(".inventory-license-link[data-license-id]");
      if (!trigger) {
        return;
      }
      event.preventDefault();
      event.stopImmediatePropagation();
      openLicense(trigger.dataset.licenseId);
    }, true);

    licenseDetailModal.addEventListener("hidden.bs.modal", () => {
      activeLicenseId = null;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
