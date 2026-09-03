(() => {
  function stockEscapeHtml(value) {
    return String(value ?? "")
      .replace(/[&<>'"]/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "'": "&#39;",
        '"': "&quot;"
      }[char]));
  }

  function stockNormalize(value) {
    return String(value ?? "")
      .trim()
      .toLocaleLowerCase("tr-TR");
  }

  function stockRows() {
    return Array.from(
      document.querySelectorAll("#stockTable tbody tr.stock-row")
    );
  }

  function applyStockFilters() {
    const searchInput =
      document.getElementById("stockSearchInput");

    const searchTerm =
      stockNormalize(searchInput?.value);

    const selectedCategory =
      document.querySelector(
        "#stockCategoryFilters input[name='stockCategory']:checked"
      )?.value || "all";

    const rows = stockRows();

    let visible = 0;

    rows.forEach((row) => {
      const searchText =
        stockNormalize(
          row.dataset.search || row.textContent
        );

      const category =
        row.dataset.category || "";

      const searchMatch =
        !searchTerm ||
        searchText.includes(searchTerm);

      const categoryMatch =
        selectedCategory === "all" ||
        category === selectedCategory;

      const shouldShow =
        searchMatch && categoryMatch;

      row.classList.toggle(
        "d-none",
        !shouldShow
      );

      if (shouldShow) {
        visible += 1;
      }
    });

    const emptyState =
      document.getElementById("stockEmptyState");

    if (emptyState) {
      emptyState.classList.toggle(
        "d-none",
        visible !== 0
      );
    }
  }

  window.applyStockFilters = applyStockFilters;

  document
    .getElementById("stockSearchClear")
    ?.addEventListener("click", () => {
      const input =
        document.getElementById("stockSearchInput");

      if (!input) {
        return;
      }

      input.value = "";
      input.focus();

      applyStockFilters();
    });

  document
    .getElementById("stockSearchInput")
    ?.addEventListener(
      "input",
      applyStockFilters
    );

  document
    .querySelectorAll(
      "#stockCategoryFilters input[name='stockCategory']"
    )
    .forEach((input) => {
      input.addEventListener(
        "change",
        applyStockFilters
      );
    });

  stockRows().forEach((row) => {
    row.setAttribute("tabindex", "0");
    row.setAttribute("role", "button");

    row.addEventListener("keydown", (event) => {
      if (
        event.key !== "Enter" &&
        event.key !== " "
      ) {
        return;
      }

      if (
        event.target.closest("button") ||
        event.target.closest("a")
      ) {
        return;
      }

      event.preventDefault();

      const trigger =
        row.querySelector(
          ".stock-detail-trigger"
        );

      trigger?.click();
    });
  });

  applyStockFilters();
})();\n