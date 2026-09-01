(() => {
  const detailModal = document.getElementById("licenseDetailModal");
  const historyList = document.getElementById("licenseHistoryList");
  const historyEmpty = document.getElementById("licenseHistoryEmpty");

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

  function renderHistory(history) {
    historyList.innerHTML = "";

    if (!Array.isArray(history) || history.length === 0) {
      historyList.classList.add("d-none");
      historyEmpty?.classList.remove("d-none");
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
      const response = await fetch(`/api/licenses/${activeLicenseId}/history`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.error || "Lisans geçmişi alınamadı.");
      }

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

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".license-detail-trigger[data-license-id]");
    if (trigger) {
      activeLicenseId = trigger.dataset.licenseId || null;
      window.setTimeout(refreshHistory, 0);
    }
  });

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
