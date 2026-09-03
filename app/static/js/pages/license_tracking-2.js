(() => {
  const input = document.getElementById("licenseSearch");

  if (!input) {
    return;
  }

  const rows = Array.from(
    document.querySelectorAll(
      "[data-license-row], .license-row, #licenseTable tbody tr"
    )
  );

  const empty = document.getElementById("licenseEmptyState");

  function applyLicenseSearch() {
    const term = input.value.trim().toLocaleLowerCase("tr-TR");
    let visible = 0;

    rows.forEach((row) => {
      const source = (
        row.dataset.search ||
        row.textContent ||
        ""
      ).toLocaleLowerCase("tr-TR");

      const match = !term || source.includes(term);

      row.classList.toggle("d-none", !match);

      if (match) {
        visible += 1;
      }
    });

    if (empty) {
      empty.classList.toggle(
        "d-none",
        visible !== 0
      );
    }
  }

  input.addEventListener("input", applyLicenseSearch);
  applyLicenseSearch();
})();\n