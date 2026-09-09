function toggleSidebar() {

    const sidebar =
        document.getElementById("sidebar");

    if (!sidebar) {
        return;
    }

    sidebar.classList.toggle("open");
}


document.addEventListener(
    "DOMContentLoaded",
    function () {

        /*
         * FILE PICKER
         */

        const fileInput =
            document.querySelector(
                'input[type="file"]'
            );

        const fileName =
            document.getElementById(
                "file-name"
            );


        if (
            fileInput
            &&
            fileName
        ) {

            fileInput.addEventListener(
                "change",
                function () {

                    if (
                        fileInput.files
                        &&
                        fileInput.files.length
                    ) {

                        fileName.textContent =
                            fileInput.files[0].name;

                    } else {

                        fileName.textContent =
                            "Choose CSV / Excel";
                    }

                }
            );

        }


        /*
         * PWA SERVICE WORKER
         */

        if (
            "serviceWorker"
            in navigator
        ) {

            navigator.serviceWorker
                .register(
                    "/service-worker.js"
                )
                .catch(
                    function () {
                        console.log(
                            "Service worker registration failed."
                        );
                    }
                );

        }

    }
);


/*
 * DATASET SEARCH
 */

function filterTable() {

    const searchInput =
        document.getElementById(
            "datasetSearch"
        );

    const table =
        document.getElementById(
            "datasetTable"
        );

    if (
        !searchInput
        ||
        !table
    ) {
        return;
    }

    const query =
        searchInput.value
            .toLowerCase();


    const rows =
        table.querySelectorAll(
            "tbody tr"
        );


    rows.forEach(
        function (row) {

            const text =
                row.innerText
                    .toLowerCase();


            row.style.display =
                text.includes(query)
                    ? ""
                    : "none";

        }
    );
}


/*
 * COLUMN SEARCH
 */

function filterColumns() {

    const searchInput =
        document.getElementById(
            "columnSearch"
        );

    const table =
        document.getElementById(
            "columnTable"
        );

    if (
        !searchInput
        ||
        !table
    ) {
        return;
    }

    const query =
        searchInput.value
            .toLowerCase();


    const rows =
        table.querySelectorAll(
            "tbody tr"
        );


    rows.forEach(
        function (row) {

            const text =
                row.innerText
                    .toLowerCase();


            row.style.display =
                text.includes(query)
                    ? ""
                    : "none";

        }
    );
}
function filterTableById(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;
    const query = input.value.toLowerCase().trim();
    table.querySelectorAll('tbody tr').forEach(function(row) {
        row.style.display = row.innerText.toLowerCase().includes(query) ? '' : 'none';
    });
}
