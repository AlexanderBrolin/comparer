document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const uploadZone = document.getElementById('uploadZone');
    const uploadContent = document.getElementById('uploadContent');
    const uploadFile = document.getElementById('uploadFile');
    const fileName = document.getElementById('fileName');
    const clearFile = document.getElementById('clearFile');
    const dateFrom = document.getElementById('dateFrom');
    const dateTo = document.getElementById('dateTo');
    const startBtn = document.getElementById('startBtn');
    const btnText = startBtn.querySelector('.btn-text');
    const spinner = startBtn.querySelector('.spinner');
    const errorBlock = document.getElementById('errorBlock');
    const errorText = document.getElementById('errorText');
    const results = document.getElementById('results');

    let selectedFile = null;

    // File upload handling
    uploadZone.addEventListener('click', () => fileInput.click());
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleFile(fileInput.files[0]);
        }
    });

    clearFile.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedFile = null;
        fileInput.value = '';
        uploadContent.style.display = '';
        uploadFile.style.display = 'none';
        updateStartBtn();
    });

    function handleFile(file) {
        if (!file.name.endsWith('.xlsx')) {
            showError('Please select an .xlsx file');
            return;
        }
        selectedFile = file;
        fileName.textContent = file.name;
        uploadContent.style.display = 'none';
        uploadFile.style.display = '';
        updateStartBtn();
    }

    function updateStartBtn() {
        startBtn.disabled = !selectedFile || !dateFrom.value || !dateTo.value;
    }

    dateFrom.addEventListener('change', updateStartBtn);
    dateTo.addEventListener('change', updateStartBtn);

    // Start comparison
    startBtn.addEventListener('click', async () => {
        if (!selectedFile) return;
        hideError();
        results.style.display = 'none';

        btnText.textContent = 'Processing...';
        spinner.style.display = '';
        startBtn.classList.add('loading');
        startBtn.disabled = true;

        const formData = new FormData();
        formData.append('xlsx_file', selectedFile);
        formData.append('date_from', dateFrom.value);
        formData.append('date_to', dateTo.value);

        try {
            const resp = await fetch('/api/compare', {
                method: 'POST',
                body: formData,
            });
            const data = await resp.json();

            if (!resp.ok) {
                showError(data.error || 'Server error');
                return;
            }

            renderResults(data);
        } catch (err) {
            showError('Network error: ' + err.message);
        } finally {
            btnText.textContent = 'Start';
            spinner.style.display = 'none';
            startBtn.classList.remove('loading');
            updateStartBtn();
        }
    });

    function showError(msg) {
        errorText.textContent = msg;
        errorBlock.style.display = '';
    }
    function hideError() {
        errorBlock.style.display = 'none';
    }

    function renderResults(data) {
        results.style.display = '';
        renderSummary(data.summary);
        renderBroken(data.broken_shifts);
        renderMatrix(data.comparison, data.summary.date_range);
    }

    function renderSummary(summary) {
        const grid = document.getElementById('summaryGrid');
        grid.innerHTML = '';
        const items = [
            { value: summary.total_employees_tabell, label: 'Employees (Tabell)' },
            { value: summary.total_employees_skud, label: 'Employees (SKUD)' },
            { value: summary.matched_employees, label: 'Matched' },
            { value: summary.broken_count, label: 'Broken Shifts' },
        ];
        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'summary-card';
            card.innerHTML = `
                <div class="summary-value">${item.value}</div>
                <div class="summary-label">${item.label}</div>
            `;
            grid.appendChild(card);
        });
    }

    function renderBroken(brokenShifts) {
        const panel = document.getElementById('brokenPanel');
        const toggle = document.getElementById('brokenToggle');
        const content = document.getElementById('brokenContent');
        const count = document.getElementById('brokenCount');
        const tbody = document.querySelector('#brokenTable tbody');

        if (!brokenShifts || brokenShifts.length === 0) {
            panel.style.display = 'none';
            return;
        }

        panel.style.display = '';
        count.textContent = brokenShifts.length;
        tbody.innerHTML = '';

        brokenShifts.forEach(s => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${esc(s.employee_id)}</td>
                <td>${esc(s.name)}</td>
                <td>${esc(s.attributed_date)}</td>
                <td>${esc(s.punch_time)}</td>
                <td>${esc(s.estimated_type)}</td>
            `;
            tbody.appendChild(tr);
        });

        // Toggle collapse
        toggle.onclick = () => {
            const open = content.style.display !== 'none';
            content.style.display = open ? 'none' : '';
            toggle.classList.toggle('open', !open);
        };
    }

    function renderMatrix(comparison, dateRange) {
        const thead = document.querySelector('#matrixTable thead');
        const tbody = document.querySelector('#matrixTable tbody');
        thead.innerHTML = '';
        tbody.innerHTML = '';

        if (!comparison || comparison.length === 0) return;

        // Generate date columns
        const dates = [];
        const from = new Date(dateRange[0] + 'T00:00:00');
        const to = new Date(dateRange[1] + 'T00:00:00');
        for (let d = new Date(from); d <= to; d.setDate(d.getDate() + 1)) {
            dates.push(d.toISOString().split('T')[0]);
        }

        // Header row
        const headerRow = document.createElement('tr');
        headerRow.innerHTML = '<th>ID</th><th>Name</th><th>Position</th>';
        dates.forEach(d => {
            const th = document.createElement('th');
            const parts = d.split('-');
            th.textContent = `${parts[2]}.${parts[1]}`;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);

        // Data rows
        comparison.forEach(row => {
            const tr = document.createElement('tr');

            // Fixed columns
            const tdId = document.createElement('td');
            tdId.textContent = row.employee_id;
            tr.appendChild(tdId);

            const tdName = document.createElement('td');
            tdName.textContent = row.name;
            tdName.title = row.name;
            tr.appendChild(tdName);

            const tdJob = document.createElement('td');
            tdJob.textContent = row.job_title;
            tdJob.title = row.job_title;
            tr.appendChild(tdJob);

            // Date cells
            dates.forEach(d => {
                const td = document.createElement('td');
                td.className = 'matrix-cell';
                const day = row.days[d];

                if (!day) {
                    td.classList.add('cell-grey');
                    td.innerHTML = '<div class="cell-inner"><div class="cell-diff">-</div></div>';
                } else if (day.broken) {
                    td.classList.add('cell-yellow');
                    td.innerHTML = `
                        <div class="cell-inner">
                            <div class="cell-hours">${day.tabell} / ?</div>
                            <div class="cell-diff">B</div>
                        </div>`;
                } else if (day.tabell === 0 && day.skud === 0) {
                    td.classList.add('cell-grey');
                    td.innerHTML = '<div class="cell-inner"><div class="cell-diff">-</div></div>';
                } else {
                    const colorClass = day.diff === 0 ? 'cell-green'
                        : day.diff > 0 ? 'cell-red'
                        : 'cell-orange';
                    td.classList.add(colorClass);
                    const diffSign = day.diff > 0 ? '+' : '';
                    td.innerHTML = `
                        <div class="cell-inner">
                            <div class="cell-hours">${day.tabell} / ${day.skud}</div>
                            <div class="cell-diff">${diffSign}${day.diff}</div>
                        </div>`;
                }
                tr.appendChild(td);
            });

            tbody.appendChild(tr);
        });
    }

    function esc(str) {
        if (!str) return '';
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    updateStartBtn();
});
