(() => {
  "use strict";

  function init() {
    const form = document.getElementById("repairForm");
    if (!form || form.dataset.qaSlaReady === "1") return;
    form.dataset.qaSlaReady = "1";

    const body = form.querySelector(".modal-body .row.g-3");
    if (!body) return;

    const makeField = (html) => {
      const wrapper = document.createElement("div");
      wrapper.innerHTML = html.trim();
      return wrapper.firstElementChild;
    };

    const qaHeader = makeField(`
      <div class="col-12 mt-2"><hr class="my-2"><div class="fw-semibold"><i class="bi bi-clipboard-check me-1"></i>Sonrası Kalite Kontrol / Onay</div></div>
    `);
    const testing = makeField(`
      <div class="col-md-4"><label class="form-label">Test Sonucu</label><select class="form-select" name="testing_status"><option value="bekliyor">Test Bekliyor</option><option value="basarili">Test Başarılı</option><option value="basarisiz">Test Başarısız</option></select></div>
    `);
    const testedAt = makeField(`
      <div class="col-md-4"><label class="form-label">Test Tarihi</label><input class="form-control" name="tested_at" type="datetime-local"></div>
    `);
    const testedBy = makeField(`
      <div class="col-md-4"><label class="form-label">Test Eden</label><input class="form-control" name="tested_by" maxlength="128"></div>
    `);
    const approval = makeField(`
      <div class="col-md-4"><label class="form-label">Onay Durumu</label><select class="form-select" name="approval_status"><option value="bekliyor">Onay Bekliyor</option><option value="onaylandi">Onaylandı</option><option value="reddedildi">Reddedildi</option></select></div>
    `);
    const approvedAt = makeField(`
      <div class="col-md-4"><label class="form-label">Onay Tarihi</label><input class="form-control" name="approved_at" type="datetime-local"></div>
    `);
    const approvedBy = makeField(`
      <div class="col-md-4"><label class="form-label">Onaylayan</label><input class="form-control" name="approved_by" maxlength="128"></div>
    `);
    const slaHeader = makeField(`
      <div class="col-12 mt-2"><hr class="my-2"><div class="fw-semibold"><i class="bi bi-stopwatch me-1"></i>SLA / Gecikme</div></div>
    `);
    const slaDue = makeField(`
      <div class="col-md-6"><label class="form-label">SLA Son Tarihi</label><input class="form-control" name="sla_due_at" type="datetime-local"></div>
    `);
    const delayReason = makeField(`
      <div class="col-md-6"><label class="form-label">Gecikme Nedeni</label><input class="form-control" name="delay_reason" maxlength="5000" placeholder="SLA aşıldıysa nedenini belirtin"></div>
    `);

    [qaHeader, testing, testedAt, testedBy, approval, approvedAt, approvedBy, slaHeader, slaDue, delayReason]
      .forEach((el) => body.appendChild(el));

    const status = form.elements.status;
    const sent = form.elements.sent_to_service;
    const sentAt = form.elements.sent_at;
    const expected = form.elements.expected_return_at;
    const returned = form.elements.returned_at;
    const sla = form.elements.sla_due_at;
    const delay = form.elements.delay_reason;

    function setDisabled(input, disabled) {
      if (!input) return;
      input.disabled = disabled;
      if (disabled) input.closest(".col-md-4, .col-md-6")?.classList.add("opacity-50");
      else input.closest(".col-md-4, .col-md-6")?.classList.remove("opacity-50");
    }

    function sync() {
      const external = Boolean(sent?.checked);
      [sentAt, expected, returned].forEach((el) => setDisabled(el, !external));

      if (status?.value === "geri_geldi" || status?.value === "tamir_edildi") {
        form.elements.testing_status.value = form.elements.testing_status.value || "bekliyor";
      }

      if (form.elements.approval_status.value === "onaylandi") {
        form.elements.testing_status.value = "basarili";
      }

      if (sla?.value && new Date(sla.value) < new Date()) {
        sla.closest(".col-md-6")?.classList.add("border", "border-danger", "rounded", "p-2");
      } else {
        sla?.closest(".col-md-6")?.classList.remove("border", "border-danger", "rounded", "p-2");
      }
    }

    sent?.addEventListener("change", sync);
    status?.addEventListener("change", sync);
    sla?.addEventListener("change", sync);
    form.elements.approval_status.addEventListener("change", sync);
    form.elements.testing_status.addEventListener("change", sync);

    form.addEventListener("reset", () => window.setTimeout(sync, 0));
    sync();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
