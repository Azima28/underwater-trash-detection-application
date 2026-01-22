// Components
const form = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const fileInfo = document.getElementById('fileInfo');
const fileNameDisplay = document.getElementById('fileNameDisplay');
const submitBtn = document.getElementById('submitBtn');
const loading = document.getElementById('loading');
const resultArea = document.getElementById('resultArea');
const mainDisplay = document.getElementById('mainDisplay');
const errorDiv = document.getElementById('error');

let chartInstance = null;

// Interaction
dropZone.onclick = () => fileInput.click();
fileInput.onchange = () => {
    if (fileInput.files[0]) {
        fileNameDisplay.innerText = fileInput.files[0].name;
        fileInfo.style.display = 'flex';
        errorDiv.style.display = 'none';
    }
};

// UI Logic
function renderChart(counts) {
    const ctx = document.getElementById('chart').getContext('2d');
    if (chartInstance) chartInstance.destroy();
    Chart.defaults.font.family = 'Outfit';
    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(counts),
            datasets: [{
                label: 'Impact Frequency',
                data: Object.values(counts),
                backgroundColor: '#15803d',
                borderRadius: 4,
                barThickness: 30
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                x: { grid: { display: false } }
            }
        }
    });
}

function formatCounts(counts) {
    if (!counts) return "-";
    return Object.entries(counts)
        .map(([k, v]) => `• ${k.toUpperCase()}: <span style="color:#15803d">${v}</span>`)
        .join('<br>');
}

function assessPollution(trash, dur = 1) {
    let eff = trash / (dur / 60);
    let lvl, title, desc, recs, statusTag;

    if (eff < 50) {
        lvl = 'low'; title = 'Environmental Status: STABLE'; statusTag = 'OPTIMAL';
        desc = 'The neural assessment indicates a well-maintained environment with minimal detectable debris. Current ecological stability is high.';
        recs = ['Conduct routine bi-weekly scans', 'Implement localized awareness campaigns', 'Monitor seasonal waste fluctuations'];
    } else if (eff < 150) {
        lvl = 'medium'; title = 'Environmental Status: AT RISK'; statusTag = 'CAUTION';
        desc = 'Moderate debris accumulation detected. If left unmanaged, the area may face significant environmental degradation over the next scan cycle.';
        recs = ['Schedule an immediate cleanup operation', 'Increase waste bin density in hotspots', 'Analyze the source of plastic migration'];
    } else {
        lvl = 'high'; title = 'Environmental Status: CRITICAL'; statusTag = 'EMERGENCY';
        desc = 'Severe plastic pollution detected. The neural count exceeded safety thresholds, indicating a high risk to local biodiversity and ecological health.';
        recs = ['Deploy emergency cleanup task force', 'Coordinate with local environmental authorities', 'Conduct a deep-dive origin investigation'];
    }

    const div = document.getElementById('pollutionReport');
    div.className = `assessment-report ${lvl}`;
    document.getElementById('pollTitle').innerText = title;
    document.getElementById('pollDesc').innerText = desc;
    document.getElementById('pollScore').innerText = Math.round(eff);
    document.getElementById('pollStatusTag').innerText = statusTag;
    document.getElementById('recList').innerHTML = recs.map(r => `<li>${r}</li>`).join('');
    div.style.display = 'block';
}

// Global Stats Fetcher
async function fetchGlobalStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        // Update specific categories from persistent global stats
        document.getElementById('globalDetections').innerText = data.total_detections.toLocaleString();

        if (data.category_stats) {
            document.getElementById('stat-trash').innerText = data.category_stats.trash.toLocaleString();
            document.getElementById('stat-bio').innerText = data.category_stats.bio.toLocaleString();
            document.getElementById('stat-rov').innerText = data.category_stats.rov.toLocaleString();
        } else {
            // Pelapis jika server belum di-restart: asumsikan semua deteksi adalah trash
            document.getElementById('stat-trash').innerText = data.total_detections.toLocaleString();
        }

        const lb = document.getElementById('leaderboard');
        lb.innerHTML = data.leaderboard.map(([name, count]) => `
            <div class="leaderboard-item">
                <span>${name}</span>
                <b>${count.toLocaleString()} detected</b>
            </div>
        `).join('') || '<p style="font-size:0.8rem; opacity:0.5;">No contributors yet.</p>';
    } catch (e) {
        console.error("Stats fetch error", e);
    }
}

// Helper to update specific category boxes
function updateCategoryStats(classCounts) {
    if (!classCounts) return;

    // Map common model classes to our 3 categories
    let trash = 0, bio = 0, rov = 0;

    Object.entries(classCounts).forEach(([name, count]) => {
        const n = name.toLowerCase();
        if (n.includes('trash') || n.includes('plastic') || n.includes('waste') || n.includes('bottle') || n.includes('can')) {
            trash += count;
        } else if (n.includes('bio') || n.includes('fish') || n.includes('plant') || n.includes('coral') || n.includes('biology')) {
            bio += count;
        } else if (n.includes('rov') || n.includes('robot') || n.includes('vehicle')) {
            rov += count;
        } else {
            // Default to trash if unknown for this specific app's purpose
            trash += count;
        }
    });

    document.getElementById('stat-trash').innerText = trash;
    document.getElementById('stat-bio').innerText = bio;
    document.getElementById('stat-rov').innerText = rov;
}

// Global variables for session management
let activePollInterval = null;

// Init stats
fetchGlobalStats();

// Processing
form.onsubmit = async (e) => {
    e.preventDefault();
    if (!fileInput.files.length) return;

    // 1. Reset Global State & Clear Polling
    if (activePollInterval) {
        clearInterval(activePollInterval);
        activePollInterval = null;
    }

    loading.style.display = 'block';
    resultArea.style.display = 'none';
    submitBtn.disabled = true;
    errorDiv.style.display = 'none';

    // 2. HARD RESET UI Counters
    document.getElementById('objCount').innerText = "0";
    document.getElementById('stat-trash').innerText = "0";
    document.getElementById('stat-bio').innerText = "0";
    document.getElementById('stat-rov').innerText = "0";
    document.getElementById('classDetails').innerHTML = "Initializing neural analysis...";

    const fd = new FormData(form);
    try {
        const res = await fetch('/upload', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        loading.style.display = 'none';
        submitBtn.disabled = false;
        resultArea.style.display = 'flex';
        document.getElementById('reportDate').innerText = "ASSESSMENT COMPLETED • " + new Date().toLocaleDateString();

        if (data.type === 'image') {
            mainDisplay.src = `/image/${data.filename}`;
            document.getElementById('objCount').innerText = data.detections;
            document.getElementById('classDetails').innerHTML = formatCounts(data.class_counts);
            document.getElementById('fpsBlock').style.display = 'none';
            assessPollution(data.detections, 1);
            renderChart(data.class_counts || {});
            updateCategoryStats(data.class_counts);
            document.getElementById('dlBtn').href = `/download/${data.filename}`;

            setTimeout(() => {
                fetchGlobalStats();
            }, 1000);
        } else {
            mainDisplay.src = `/stream/${data.stream_id}?t=${Date.now()}&model=${data.model}&contributor=${encodeURIComponent(data.contributor)}`;
            document.getElementById('fpsBlock').style.display = 'block';

            activePollInterval = setInterval(async () => {
                try {
                    const r = await fetch(`/status/${data.stream_id}`);
                    const s = await r.json();

                    // Update counts
                    document.getElementById('objCount').innerText = s.detections;
                    updateCategoryStats(s.class_counts);
                    document.getElementById('classDetails').innerHTML = formatCounts(s.class_counts);

                    if (s.ready) {
                        clearInterval(activePollInterval);
                        activePollInterval = null;
                        assessPollution(s.detections, s.frames / 30);
                        renderChart(s.class_counts || {});
                        document.getElementById('dlBtn').href = `/download/${s.filename}`;
                        fetchGlobalStats();
                    }
                } catch (err) {
                    console.error("Polling error:", err);
                }
            }, 500);
        }
        window.scrollTo({ top: resultArea.offsetTop - 100, behavior: 'smooth' });
    } catch (e) {
        loading.style.display = 'none';
        submitBtn.disabled = false;
        errorDiv.innerText = "Assessment Error: " + e.message;
        errorDiv.style.display = 'block';
    }
};
