(() => {
  const detailModal = document.getElementById("licenseDetailModal");
  const historyList = document.getElementById("licenseHistoryList");
  const historyEmpty = document.getElementById("licenseHistoryEmpty");
  const createModal = document.getElementById("licenseCreateModal");
  const createSubmit = document.getElementById("licenseCreateSubmit");
  const assignSubmit = document.getElementById("licenseAssignSubmit");
  const editSubmit = document.getElementById("licenseEditSubmit");

  if (!detailModal || !historyList) {
    return;
  }

  let activeLicenseId = null;

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    })[char]);
  }

  async function apiRequest(url, method, body) {
    const response = await fetch(url, {
      method,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || "İşlem gerçekleştirilemedi.");
    }
    return payload;
  }

  function renderHistory(history) {
    historyList.innerHTML = "";

    if (!Array.isArray(history) || history.length === 0) {
      historyList.classList.add("d-none");
      historyEmpty?.classList.remove("d-none");
      if (historyEmpty) {
        historyEmpty.textContent = "Kayıt yok.";
      }
      return;
    }

    historyList.classList.remove("d-none");
    historyEmpty?.classList.add("d-none");

    history.forEach((entry) => {
      const row = document.createElement("li");
      row.className = "list-group-item license-history-item";
      row.innerHTML = `
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
      historyList.appendChild(row);
    });
  }

  async function refreshHistory() {
    if (!activeLicenseId) {
      return;
    }

    try {
      const payload = await apiRequest(`/api/licenses/${activeLicenseId}/history`, "GET");
      renderHistory(payload.history);
    } catch (error) {
      historyList.innerHTML = "";
      historyList.classList.add("d-none");
      if (historyEmpty) {
        historyEmpty.classList.remove("d-none");
        historyEmpty.textContent = error.message || "Lisans geçmişi alınamadı.";
      }
    }
  }

  async function createLicense() {
    const nameInput = document.getElementById("licenseCreateName");
    const keyInput = document.getElementById("licenseCreateKey");
    const name = nameInput?.value?.trim() || "";
    const key = keyInput?.value?.trim() || "";

    if (!name || !key) {
      nameInput?.reportValidity();
      keyInput?.reportValidity();
      return;
    }

    try {
      await apiRequest("/api/licenses", "POST", { name, key });
      window.location.reload();
    } catch (error) {
      window.alert(error.message || "Lisans oluşturulamadı.");
    }
  }

  async function assignLicense() {
    if (!activeLicenseId) {
      return;
    }

    const inventoryId = document.getElementById("assignInventorySelect")?.value || "";
    if (!inventoryId) {
      window.alert("Lisans ataması için envanter seçilmelidir.");
      return;
    }

    try {
      await apiRequest(`/api/licenses/${activeLicenseId}/assign`, "POST", {
        inventory_id: inventoryId,
      });
      window.location.reload();
    } catch (error) {
      window.alert(error.message || "Lisans atanamadı.");
    }
  }

  async function editLicense() {
    if (!activeLicenseId) {
      return;
    }

    const name = document.getElementById("editNameSelect")?.value?.trim() || "";
    const key = document.getElementById("editKeyInput")?.value?.trim() || "";
    const status = document.getElementById("editStatusSelect")?.value || "aktif";
    const inventoryId = document.getElementById("editInventorySelect")?.value || "";

    if (!name || !key) {
      document.getElementById("editNameSelect")?.reportValidity();
      document.getElementById("editKeyInput")?.reportValidity();
      return;
    }

    try {
      await apiRequest(`/api/licenses/${activeLicenseId}`, "PATCH", {
        name,
        key,
        status,
        inventory_id: inventoryId || null,
      });
      window.location.reload();
    } catch (error) {
      window.alert(error.message || "Lisans güncellenemedi.");
    }
  }

  async function passiveLicense(licenseId) {
    try {
      await apiRequest(`/api/licenses/${licenseId}/passive`, "POST");
      window.location.reload();
    } catch (error) {
      window.alert(error.message || "Lisans pasife alınamadı.");
    }
  }

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".license-detail-trigger[data-license-id]");
    if (trigger) {
      activeLicenseId = trigger.dataset.licenseId || null;
      window.setTimeout(refreshHistory, 0);
    }
  });

  // The legacy page script keeps its local-state handlers. These capture
  // handlers replace them for mutations so changes are actually persisted.
  document.addEventListener("click", (event) => {
    const action = event.target.closest(".license-action[data-action][data-license-id]");
    if (!action) {
      return;
    }

    const actionType = action.dataset.action;
    const licenseId = action.dataset.licenseId;
    activeLicenseId = licenseId || activeLicenseId;

    if (actionType === "passive") {
      event.preventDefault();
      event.stopImmediatePropagation();
      passiveLicense(licenseId);
      return;
    }

    if (actionType === "assign") {
      activeLicenseId = licenseId;
    }
  }, true);

  createSubmit?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    createLicense();
  }, true);

  assignSubmit?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    assignLicense();
  }, true);

  editSubmit?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    editLicense();
  }, true);

  detailModal.addEventListener("show.bs.modal", (event) => {
    const trigger = event.relatedTarget;
    const id = trigger?.dataset?.licenseId;
    if (id) {
      activeLicenseId = id;
    }
  });

  detailModal.addEventListener("shown.bs.modal", refreshHistory);

  detailModal.addEventListener("hidden.bs.modal", () => {
    activeLicenseId = null;
  });
})();
