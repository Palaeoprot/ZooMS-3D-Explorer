
// ZooMS Explorer - Main Application Logic

let tableData = [];
let visibleCols = [];
let encodings = {};
let spectraData = {};
let projectId = null;

// Global State
let currentSort = { column: null, direction: 'asc' };

// Initialize the application
async function init() {
    console.log("Initializing ZooMS Explorer...");

    // 1. Get Project ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    projectId = urlParams.get('project');

    if (!projectId) {
        alert("No project specified. Redirecting to project selection.");
        window.location.href = 'index.html';
        return;
    }

    // Update Header
    document.title = `ZooMS Explorer - ${projectId}`;
    const subtitle = document.querySelector('.subtitle');
    if (subtitle) subtitle.textContent = `Project: ${projectId} | Interactive Analysis`;

    // 2. Load Project Data
    try {
        await loadProjectData(projectId);
    } catch (error) {
        console.error("Failed to load project data:", error);
        alert(`Error loading project '${projectId}': ${error.message}`);
        return;
    }

    // 3. Initialize Interface
    populateColorDropdown();
    renderTableHeaders();
    renderTableRows(tableData);
    setupPlotEvents();
    setupColorDropdown();

    // Render Initial Plot
    render3DPlot(tableData);

    // 4. Initial Plot Coloring (default to first option)
    const colorSelect = document.getElementById('color-select');
    if (colorSelect && colorSelect.options.length > 0) {
        updatePlotColor(colorSelect.value);
    }
}

// Data Loading
async function loadProjectData(id) {
    const url = `projects/${id}/web_payload.json`;
    console.log(`Fetching data from ${url}...`);

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const payload = await response.json();

    // Assign to globals
    tableData = payload.tableData;
    visibleCols = payload.visibleCols;
    encodings = payload.encodings;

    // Spectra data
    if (payload.spectraData) {
        spectraData = payload.spectraData;
    }

    console.log("Data loaded successfully.", {
        samples: tableData.length,
        cols: visibleCols.length,
        spectra: Object.keys(spectraData).length
    });
}

// --- UI Rendering ---

function populateColorDropdown() {
    const select = document.getElementById('color-select');
    select.innerHTML = '';

    Object.keys(encodings).forEach(key => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = encodings[key].label || key;
        select.appendChild(option);
    });

    // Default select action
    select.addEventListener('change', (e) => {
        updatePlotColor(e.target.value);
    });
}

function renderTableHeaders() {
    const thead = document.querySelector('#data-table thead');
    thead.innerHTML = '';
    const tr = document.createElement('tr');

    visibleCols.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        th.onclick = () => sortColumn(col);
        tr.appendChild(th);
    });
    thead.appendChild(tr);
}

function renderTableRows(data) {
    const tbody = document.querySelector('#data-table tbody');
    tbody.innerHTML = '';

    data.forEach(row => {
        const tr = document.createElement('tr');
        tr.id = `row-${row.id}`; // Assuming 'id' is a unique filename/identifier
        tr.onclick = () => highlightPoint(row.id);

        visibleCols.forEach(col => {
            const td = document.createElement('td');

            // Special handling for 'id' column to make it a clickable link to spectrum
            if (col === 'id' || col === 'Sample_Name') {
                td.classList.add('clickable-cell');
                td.onclick = (e) => {
                    e.stopPropagation(); // Prevent row selection
                    showSpectrum(row.id);
                };
            }

            let val = row[col];
            // Formatting numbers
            if (typeof val === 'number' && !Number.isInteger(val)) {
                val = val.toFixed(2);
            }
            td.textContent = val;
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });
}

// --- Interaction & Plotting ---

function setupColorDropdown() {
    // Already handled in populateColorDropdown
}

function render3DPlot(data) {
    const plotDiv = document.getElementById('3d-plot');
    if (!plotDiv) {
        console.error("3d-plot container not found!");
        return;
    }

    const trace = {
        x: data.map(d => d.UMAP1 || d.x || 0),
        y: data.map(d => d.UMAP2 || d.y || 0),
        z: data.map(d => d.UMAP3 || d.z || 0),
        mode: 'markers',
        marker: {
            size: 5,
            color: data.map(d => d.Species || 0), // Default color
            colorscale: 'Viridis',
            line: { color: 'rgba(217, 217, 217, 0.14)', width: 0.5 },
            opacity: 0.8
        },
        type: 'scatter3d',
        text: data.map(d => d.Sample_Name || d.id),
        hoverinfo: 'text'
    };

    const layout = {
        margin: { l: 0, r: 0, b: 0, t: 0 },
        scene: {
            xaxis: { title: 'UMAP 1' },
            yaxis: { title: 'UMAP 2' },
            zaxis: { title: 'UMAP 3' }
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)'
    };

    const config = { responsive: true };

    Plotly.newPlot(plotDiv, [trace], layout, config);

    // Re-attach events because newPlot might clear them
    plotDiv.on('plotly_click', function (data) {
        const point = data.points[0];
        // Find ID from point index or text
        // data.points[0].pointNumber corresponds to index in arrays
        const rowIndex = point.pointNumber;
        if (tableData[rowIndex]) {
            const id = tableData[rowIndex].id;
            highlightPoint(id);
            if (data.event.shiftKey) {
                showSpectrum(id);
            }
        }
    });
}

function updatePlotColor(column) {
    const encoding = encodings[column];
    if (!encoding) return;

    const plotDiv = document.querySelector('.plotly-graph-div');
    if (!plotDiv) return;

    const colors = tableData.map(row => {
        const val = row[column];
        if (encoding.type === 'categorical') {
            return encoding.mapping[val] !== undefined ? encoding.mapping[val] : -1;
        } else {
            return val;
        }
    });

    const update = {
        'marker.color': [colors],
        'marker.colorscale': encoding.colorscale || 'Viridis',
        'marker.colorbar.title.text': encoding.label || column
    };

    Plotly.restyle(plotDiv, update);
}

function setupPlotEvents() {
    // Handled in render3DPlot because Plotly specific events need the element
}

function highlightPoint(id) {
    // Highlight table row
    highlightRow(id);
}

function highlightRow(id) {
    // Remove existing highlights
    document.querySelectorAll('tr.selected').forEach(tr => tr.classList.remove('selected'));

    // Add new
    const row = document.getElementById(`row-${id}`);
    if (row) {
        row.classList.add('selected');
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// --- Spectrum Viewer ---

function showSpectrum(id) {
    const modal = document.getElementById('spectrum-modal');
    const title = document.getElementById('spectrum-title');
    const plotDiv = document.getElementById('spectrum-plot');

    if (!spectraData[id]) {
        alert("No spectrum data found for " + id);
        return;
    }

    const spec = spectraData[id];

    modal.classList.add('active');
    title.textContent = `Spectrum: ${id}`;

    // Render Stick Plot
    const trace = {
        x: spec.mz,
        y: spec.intensity,
        type: 'bar', // 'bar' gives a stick-like appearance for discrete MS centers
        width: 1 // thin bars
    };

    const layout = {
        title: id,
        xaxis: { title: 'm/z' },
        yaxis: { title: 'Intensity' },
        margin: { t: 40, r: 20, l: 50, b: 50 }
    };

    Plotly.newPlot(plotDiv, [trace], layout);
}

function closeSpectrum() {
    const modal = document.getElementById('spectrum-modal');
    modal.classList.remove('active');
}

// --- Sorting & Filtering ---

function sortColumn(column) {
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }

    tableData.sort((a, b) => {
        let valA = a[column];
        let valB = b[column];

        // Handle nulls
        if (valA == null) valA = "";
        if (valB == null) valB = "";

        // Use string comparison if not numbers
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();

        if (valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
        if (valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });

    renderTableRows(tableData);
}

function filterTable(searchTerm) {
    if (!searchTerm) {
        renderTableRows(tableData);
        return;
    }

    const lowerTerm = searchTerm.toLowerCase();
    const filtered = tableData.filter(row => {
        return Object.values(row).some(val =>
            String(val).toLowerCase().includes(lowerTerm)
        );
    });

    renderTableRows(filtered);
}

// --- Initial Launch ---
window.onload = init;
