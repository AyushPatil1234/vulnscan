// Theme management
const themeToggle = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');
const themeText = document.getElementById('themeText');
const body = document.body;

// Load saved theme or default to light
const savedTheme = localStorage.getItem('theme') || 'light';
body.setAttribute('data-theme', savedTheme);
updateThemeToggleText(savedTheme);

themeToggle.addEventListener('click', () => {
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeToggleText(newTheme);
});

// Window Controls Functionality
const closeBtn = document.querySelector('.close');
const minimizeBtn = document.querySelector('.minimize');
const maximizeBtn = document.querySelector('.maximize');

// Red Dot: Reset Scanner
closeBtn.addEventListener('click', () => {
    if (confirm('Are you sure you want to reset the scanner? This will clear all inputs and results.')) {
        // Clear inputs
        document.getElementById('targetUrl').value = 'http://testphp.vulnweb.com';
        document.getElementById('loginUrl').value = '';
        document.getElementById('username').value = '';
        document.getElementById('password').value = '';
        document.getElementById('proxyUrl').value = '';

        // Clear results
        document.getElementById('scanOutput').innerHTML = `AI-Powered Scanner Ready
                                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                                Enhanced Security Analysis Engine
                                • Machine Learning-based vulnerability detection
                                • Real-time threat assessment
                                • Automated penetration testing
                                • OWASP Top 10 compliance checking

                                Ready to scan your target...
                                Click "Start Scan" to begin comprehensive security analysis.`;

        // Reset stats
        updateStats(0, 0, 0, '0s', '0%', 0, 0, 0);

        // Reset heatmap
        document.getElementById('vulnerabilityChart').innerHTML = `
            <div style="text-align: center; color: var(--text-muted);">
                <div style="font-size: 32px; margin-bottom: 15px;">📊</div>
                <div style="font-size: 16px; font-weight: 500;">No scan data available</div>
                <div style="font-size: 14px; margin-top: 8px;">Run a security scan to see vulnerability distribution</div>
            </div>
        `;

        allVulnerabilities = [];
        showNotification('Scanner Reset', 'All settings and results have been cleared.');
    }
});

// Yellow Dot: Compact Mode
minimizeBtn.addEventListener('click', () => {
    const settingsSection = document.querySelector('.section.active .card:first-child');
    const resultsArea = document.getElementById('resultsArea');

    if (settingsSection) {
        if (settingsSection.style.display === 'none') {
            settingsSection.style.display = 'block';
            resultsArea.classList.remove('expanded');
            minimizeBtn.title = 'Compact Mode';
        } else {
            settingsSection.style.display = 'none';
            resultsArea.classList.add('expanded');
            minimizeBtn.title = 'Restore View';
        }
    }
});

// Green Dot: Fullscreen
maximizeBtn.addEventListener('click', () => {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            console.log(`Error attempting to enable fullscreen: ${err.message}`);
        });
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
});
const aiProviderSelect = document.getElementById('aiProvider');
const aiModelSelect = document.getElementById('aiModel');

const aiModels = {
    openai: [
        { value: 'gpt-4o', label: 'GPT-4o (Flagship - Best Overall)' },
        { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Fast & Cost-Effective)' },
        { value: 'o1-preview', label: 'o1-preview (Advanced Reasoning)' },
        { value: 'o1-mini', label: 'o1-mini (Fast Reasoning)' },
        { value: 'gpt-4-turbo', label: 'GPT-4 Turbo (High Capability)' },
        { value: 'gpt-4', label: 'GPT-4 (Legacy)' },
        { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo (Fast)' }
    ],
    gemini: [
        { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro (Advanced Reasoning)' },
        { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash (High Speed & Efficiency)' },
        { value: 'gemini-2.0-flash-exp', label: 'Gemini 2.0 Flash (Experimental - Newest)' },
        { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro (Best for Complex Tasks)' },
        { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash (Fast & Versatile)' },
        { value: 'gemini-1.5-flash-8b', label: 'Gemini 1.5 Flash-8B (High Volume)' },
        { value: 'gemini-1.0-pro', label: 'Gemini 1.0 Pro (Standard)' }
    ]
};

function updateModelOptions() {
    const provider = aiProviderSelect.value;
    const models = aiModels[provider] || [];

    aiModelSelect.innerHTML = models.map(model =>
        `<option value="${model.value}">${model.label}</option>`
    ).join('');
}

aiProviderSelect.addEventListener('change', updateModelOptions);
// Initialize on load
updateModelOptions();

themeToggle.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        themeToggle.click();
    }
});

function updateThemeToggleText(theme) {
    if (theme === 'light') {
        themeIcon.textContent = '🌙';
        themeText.textContent = 'Dark';
        themeToggle.setAttribute('aria-label', 'Switch to dark theme');
    } else {
        themeIcon.textContent = '☀️';
        themeText.textContent = 'Light';
        themeToggle.setAttribute('aria-label', 'Switch to light theme');
    }
}

// Tab switching functionality
const tabs = document.querySelectorAll('.tab');
const sections = document.querySelectorAll('.section');

tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const targetSection = tab.getAttribute('data-section');

        // Remove active class from all tabs and sections
        tabs.forEach(t => t.classList.remove('active'));
        sections.forEach(s => s.classList.remove('active'));

        // Add active class to clicked tab and corresponding section
        tab.classList.add('active');
        document.getElementById(targetSection).classList.add('active');
    });
});

// Scan functionality
const startBtn = document.getElementById('startScan');
const stopBtn = document.getElementById('stopScan');
const progressBar = document.getElementById('progressBar');
const progressFill = document.getElementById('progressFill');
const scanningMessage = document.getElementById('scanningMessage');
const statusText = document.getElementById('statusText');
const scanOutput = document.getElementById('scanOutput');

let abortController = null;
let scanStartTime;
let allVulnerabilities = [];

startBtn.addEventListener('click', startScan);
stopBtn.addEventListener('click', stopScan);

async function startScan() {
    const targetUrl = document.getElementById('targetUrl').value;
    const crawlDepth = document.getElementById('crawlDepth').value;
    const aiProvider = document.getElementById('aiProvider').value;
    const apiKey = document.getElementById('apiKey').value;
    const aiModel = document.getElementById('aiModel').value;

    // Auth & Proxy
    const loginUrl = document.getElementById('loginUrl').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const basicAuth = document.getElementById('basicAuth').checked;
    const formAuth = document.getElementById('formAuth').checked;
    const cookieAuth = document.getElementById('cookieAuth').checked;
    const proxyUrl = document.getElementById('proxyUrl').value;
    const userAgent = document.getElementById('userAgent').value;
    const enableJS = document.getElementById('enableJS').checked;
    const followRedirects = document.getElementById('followRedirects').checked;
    const activeScan = document.getElementById('activeScan').checked;
    const deepJsScan = document.getElementById('deepJsScan').checked;
    const stealthMode = document.getElementById('stealthMode').checked;

    if (!targetUrl) {
        alert('Please enter a target URL to begin scanning');
        return;
    }

    // UI updates
    startBtn.disabled = true;
    stopBtn.disabled = false;
    progressBar.style.display = 'block';
    scanningMessage.style.display = 'block';
    statusText.innerHTML = 'Scanning in progress...';
    scanStartTime = Date.now();

    // Clear previous results
    scanOutput.innerHTML = '';
    progressFill.style.width = '0%';
    allVulnerabilities = [];

    // Reset stats
    updateStats(0, 0, 0, 0, 0, 0, '0s', '0%');

    // Reset heatmap
    document.getElementById('vulnerabilityChart').innerHTML = `
        <div style="text-align: center; color: var(--text-muted);">
            <div style="font-size: 32px; margin-bottom: 15px;">📊</div>
            <div style="font-size: 16px; font-weight: 500;">Scanning...</div>
            <div style="font-size: 14px; margin-top: 8px;">Gathering data for vulnerability distribution</div>
        </div>
    `;

    abortController = new AbortController();

    try {
        const response = await fetch('/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                target_url: targetUrl,
                crawl_depth: parseInt(crawlDepth),
                ai_provider: aiProvider,
                api_key: apiKey,
                ai_model: aiModel,
                // Add new fields
                login_url: loginUrl,
                username: username,
                password: password,
                basic_auth: basicAuth,
                form_auth: formAuth,
                cookie_auth: cookieAuth,
                proxy_url: proxyUrl,
                user_agent: userAgent,
                enable_js: enableJS,
                follow_redirects: followRedirects,
                active_scan: activeScan,
                deep_js_scan: deepJsScan,
                stealth_mode: stealthMode
            }),
            signal: abortController.signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep the last incomplete line in buffer

            for (const line of lines) {
                if (line.trim()) {
                    try {
                        const data = JSON.parse(line);
                        handleScanUpdate(data);
                    } catch (e) {
                        console.error('Error parsing JSON:', e, line);
                        // Fallback for plain text logs if any
                        logMessage(line);
                    }
                }
            }
        }

        completeScan();

    } catch (error) {
        if (error.name === 'AbortError') {
            logMessage('Scan stopped by user.', 'error');
        } else {
            logMessage(`Error: ${error.message}`, 'error');
            completeScan(true);
        }
    } finally {
        abortController = null;
    }
}

function stopScan() {
    if (abortController) {
        abortController.abort();
    }
    startBtn.disabled = false;
    stopBtn.disabled = true;
    progressBar.style.display = 'none';
    scanningMessage.style.display = 'none';
    statusText.innerHTML = 'Scan stopped by user';
}

function handleScanUpdate(data) {
    if (data.type === 'log') {
        logMessage(data.message);
        if (data.step) {
            scanningMessage.textContent = data.step;
        }
    } else if (data.type === 'progress') {
        progressFill.style.width = data.percent + '%';
        // Update generic stats
        const duration = Math.floor((Date.now() - scanStartTime) / 1000) + 's';
        updateStats(data.stats.total, data.stats.pages, data.stats.requests, duration, data.stats.risk, data.stats.high, data.stats.medium, data.stats.low);
    } else if (data.type === 'vulnerability') {
        allVulnerabilities.push(data);
        logVulnerability(data);
    } else if (data.type === 'heatmap') {
        renderHeatmap(data.data);
    }
}

function logMessage(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    let color = '#ef4444'; // success/info
    if (type === 'error') color = '#ef4444';
    if (type === 'warning') color = '#f59e0b';

    const logEntry = document.createElement('div');
    logEntry.style.cssText = `color: ${color}; margin: 8px 0; padding: 8px 0; border-bottom: 1px solid rgba(239,68,68,0.2);`;

    const timeSpan = document.createElement('span');
    timeSpan.style.color = '#f59e0b';
    timeSpan.textContent = `[${timestamp}] `;

    const msgSpan = document.createElement('span');
    msgSpan.textContent = message;

    logEntry.appendChild(timeSpan);
    logEntry.appendChild(msgSpan);

    scanOutput.appendChild(logEntry);
    document.getElementById('resultsArea').scrollTop = document.getElementById('resultsArea').scrollHeight;
}

function logVulnerability(vuln) {
    const color = vuln.severity === 'High' ? '#ef4444' : (vuln.severity === 'Medium' ? '#f59e0b' : '#10b981');
    const logEntry = document.createElement('div');
    logEntry.style.cssText = `color: ${color}; margin: 8px 0; padding: 8px; background: ${color}1a; border-radius: 4px;`;

    const title = document.createElement('strong');
    title.textContent = `[${vuln.severity}] ${vuln.name}`;

    const desc = document.createElement('div');
    desc.textContent = vuln.description;

    logEntry.appendChild(title);
    logEntry.appendChild(document.createElement('br'));
    logEntry.appendChild(desc);

    scanOutput.appendChild(logEntry);
    document.getElementById('resultsArea').scrollTop = document.getElementById('resultsArea').scrollHeight;
}

function completeScan(error = false) {
    startBtn.disabled = false;
    stopBtn.disabled = true;
    progressBar.style.display = 'none';
    scanningMessage.style.display = 'none';
    statusText.innerHTML = error ? 'Scan failed' : 'Scan completed successfully!';

    if (!error) {
        const timestamp = new Date().toLocaleTimeString();
        scanOutput.innerHTML += `
            <div style="color: #ef4444; margin: 15px 0; padding: 15px; background: rgba(239,68,68,0.1); border-radius: 8px; border-left: 3px solid #ef4444;">
                <div style="font-size: 16px; font-weight: 600; margin-bottom: 10px;">
                    [${timestamp}] Scan completed!
                </div>
                <div>Check the dashboard for detailed analysis. Click on the risk cards to see repair instructions.</div>
            </div>
        `;
    }
}

function updateStats(total = 0, pages = 0, requests = 0, time = '0s', risk = '0%', high = 0, medium = 0, low = 0) {
    document.getElementById('totalVulns').textContent = total;
    document.getElementById('pagesScanned').textContent = pages;
    document.getElementById('requestsSent').textContent = requests;
    document.getElementById('scanTime').textContent = time;
    document.getElementById('riskScore').textContent = risk;
    document.getElementById('highRisk').textContent = high;
    document.getElementById('mediumRisk').textContent = medium;
    document.getElementById('lowRisk').textContent = low;
}

function renderHeatmap(data) {
    // data is expected to be { high: 2, medium: 3, low: 1, recommendations: [...] }
    const chartHtml = `
        <div style="text-align: left; width: 100%;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                <div style="background: rgba(239,68,68,0.1); padding: 20px; border-radius: 8px; border-left: 3px solid #ef4444;">
                    <div style="color: #ef4444; font-size: 24px; font-weight: 600;">High Risk</div>
                    <div style="color: var(--text-secondary); margin-top: 8px;">${data.high} Critical vulnerabilities</div>
                    <div style="font-size: 12px; margin-top: 8px; color: var(--text-tertiary);">Immediate attention required</div>
                </div>
                <div style="background: rgba(245,158,11,0.1); padding: 20px; border-radius: 8px; border-left: 3px solid #f59e0b;">
                    <div style="color: #f59e0b; font-size: 24px; font-weight: 600;">Medium Risk</div>
                    <div style="color: var(--text-secondary); margin-top: 8px;">${data.medium} Moderate vulnerabilities</div>
                    <div style="font-size: 12px; margin-top: 8px; color: var(--text-tertiary);">Should be addressed soon</div>
                </div>
                <div style="background: rgba(16,185,129,0.1); padding: 20px; border-radius: 8px; border-left: 3px solid #10b981;">
                    <div style="color: #10b981; font-size: 24px; font-weight: 600;">Low Risk</div>
                    <div style="color: var(--text-secondary); margin-top: 8px;">${data.low} Minor vulnerability</div>
                    <div style="font-size: 12px; margin-top: 8px; color: var(--text-tertiary);">Monitor and fix when convenient</div>
                </div>
            </div>
            <div style="margin-top: 25px; padding: 20px; background: var(--bg-accent); border-radius: 8px;">
                <div style="color: var(--accent-color); font-weight: 500; margin-bottom: 10px;">AI Security Recommendations:</div>
                <div style="font-size: 14px; line-height: 1.6; color: var(--text-secondary);">
                    ${data.recommendations.map(rec => {
        const div = document.createElement('div');
        div.textContent = '• ' + rec;
        return div.innerHTML + '<br>';
    }).join('')}
                </div>
            </div>
        </div>
    `;
    document.getElementById('vulnerabilityChart').innerHTML = chartHtml;
}

// Modal Functionality
const modal = document.getElementById('vulnModal');
const closeModal = document.getElementById('closeModal');
const modalTitle = document.getElementById('modalTitle');
const modalBody = document.getElementById('modalBody');

closeModal.addEventListener('click', () => {
    modal.classList.remove('active');
});

modal.addEventListener('click', (e) => {
    if (e.target === modal) {
        modal.classList.remove('active');
    }
});

// Interactive Stat Cards
document.getElementById('highRiskCard').addEventListener('click', () => openVulnerabilityModal('High'));
document.getElementById('mediumRiskCard').addEventListener('click', () => openVulnerabilityModal('Medium'));
document.getElementById('lowRiskCard').addEventListener('click', () => openVulnerabilityModal('Low'));

function openVulnerabilityModal(severity) {
    const filteredVulns = allVulnerabilities.filter(v => v.severity === severity);

    modalTitle.textContent = `${severity} Risk Vulnerabilities`;
    modalBody.innerHTML = '';

    if (filteredVulns.length === 0) {
        modalBody.innerHTML = `
            <div class="empty-state">
                <div style="font-size: 48px; margin-bottom: 16px;">✓</div>
                <div>No ${severity.toLowerCase()} risk vulnerabilities found.</div>
            </div>
        `;
    } else {
        filteredVulns.forEach(vuln => {
            const card = document.createElement('div');
            card.className = 'vuln-detail-card';

            const severityClass = `severity-${severity.toLowerCase()}`;

            card.innerHTML = `
                <div class="vuln-detail-header">
                    <div class="vuln-name"></div>
                    <div class="vuln-severity ${severityClass}"></div>
                </div>
                <div class="vuln-section-title">Description</div>
                <div class="vuln-description"></div>
                <div class="vuln-section-title">How to Repair</div>
                <div class="vuln-remediation"></div>
            `;

            card.querySelector('.vuln-name').textContent = vuln.name;
            card.querySelector('.vuln-severity').textContent = vuln.severity;
            card.querySelector('.vuln-description').textContent = vuln.description;
            card.querySelector('.vuln-remediation').textContent = vuln.remediation || 'No specific remediation instructions available.';
            modalBody.appendChild(card);
        });
    }

    modal.classList.add('active');
}

// Bottom button functionality
document.getElementById('aiAnalysis').addEventListener('click', () => generateAIReport('analysis', 'AI Security Analysis'));
document.getElementById('generatePlan').addEventListener('click', () => generateAIReport('mitigation', 'Mitigation Plan'));
document.getElementById('predictVectors').addEventListener('click', () => generateAIReport('vectors', 'Attack Vector Analysis'));

async function generateAIReport(type, title) {
    if (allVulnerabilities.length === 0) {
        showNotification('No Data', 'Please run a scan first to generate a report.');
        return;
    }

    modalTitle.textContent = title;
    modalBody.innerHTML = '<div style="text-align:center; padding: 40px;">Generating detailed AI report...<br>Please wait.</div>';
    modal.classList.add('active');

    const aiProvider = document.getElementById('aiProvider').value;
    const apiKey = document.getElementById('apiKey').value;
    const aiModel = document.getElementById('aiModel').value;

    try {
        const response = await fetch('/generate_report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vulnerabilities: allVulnerabilities,
                type: type,
                ai_provider: aiProvider,
                api_key: apiKey,
                ai_model: aiModel
            })
        });

        const data = await response.json();
        modalBody.innerHTML = `<div style="padding: 20px; line-height: 1.6;">${data.content}</div>`;

    } catch (error) {
        modalBody.innerHTML = '<div style="color: red; text-align:center; padding: 20px;">Failed to generate report.</div>';
    }
}

document.getElementById('saveReport').addEventListener('click', () => {
    if (allVulnerabilities.length === 0) {
        showNotification('No Data', 'Please run a scan first to save a report.');
        return;
    }

    // Create a simple format selection modal content
    modalTitle.textContent = 'Export Security Report';
    modalBody.innerHTML = `
        <div style="padding: 20px; text-align: center;">
            <p style="margin-bottom: 20px;">Select report format:</p>
            <div style="display: flex; gap: 10px; justify-content: center;">
                <button class="btn" onclick="downloadReport('html')">HTML Report</button>
                <button class="btn" onclick="downloadReport('json')">JSON Data</button>
                <button class="btn" onclick="downloadReport('md')">Markdown</button>
            </div>
        </div>
    `;
    modal.classList.add('active');
});

window.downloadReport = async (format) => {
    try {
        const response = await fetch('/download_report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vulnerabilities: allVulnerabilities,
                format: format
            })
        });

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `security_report.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        modal.classList.remove('active');
        showNotification('Success', `Report saved as ${format.toUpperCase()}`);
    } catch (error) {
        showNotification('Error', 'Failed to download report');
    }
};

document.getElementById('exportConfig').addEventListener('click', () => {
    const config = {
        targetUrl: document.getElementById('targetUrl').value,
        requestDelay: document.getElementById('requestDelay').value,
        crawlDepth: document.getElementById('crawlDepth').value,
        loginUrl: document.getElementById('loginUrl').value,
        proxyUrl: document.getElementById('proxyUrl').value,
        userAgent: document.getElementById('userAgent').value,
        enableJS: document.getElementById('enableJS').checked,
        followRedirects: document.getElementById('followRedirects').checked,
        activeScan: document.getElementById('activeScan').checked,
        deepJsScan: document.getElementById('deepJsScan').checked,
        stealthMode: document.getElementById('stealthMode').checked,
        basicAuth: document.getElementById('basicAuth').checked,
        formAuth: document.getElementById('formAuth').checked,
        cookieAuth: document.getElementById('cookieAuth').checked
    };

    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ai-scanner-config.json';
    a.click();

    showNotification('Export Success', 'Configuration exported successfully as ai-scanner-config.json');
});

document.getElementById('importConfig').addEventListener('click', () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const config = JSON.parse(e.target.result);
                    document.getElementById('targetUrl').value = config.targetUrl || '';
                    document.getElementById('requestDelay').value = config.requestDelay || '0.5';
                    document.getElementById('crawlDepth').value = config.crawlDepth || '2';
                    document.getElementById('loginUrl').value = config.loginUrl || '';
                    document.getElementById('proxyUrl').value = config.proxyUrl || '';
                    document.getElementById('userAgent').value = config.userAgent || 'Mozilla/5.0 (AI Security Scanner)';
                    document.getElementById('enableJS').checked = config.enableJS || false;
                    document.getElementById('followRedirects').checked = config.followRedirects || false;
                    document.getElementById('activeScan').checked = config.activeScan || false;
                    if(document.getElementById('deepJsScan')) document.getElementById('deepJsScan').checked = config.deepJsScan || false;
                    if(document.getElementById('stealthMode')) document.getElementById('stealthMode').checked = config.stealthMode !== undefined ? config.stealthMode : true;
                    document.getElementById('basicAuth').checked = config.basicAuth || false;
                    document.getElementById('formAuth').checked = config.formAuth || false;
                    document.getElementById('cookieAuth').checked = config.cookieAuth || false;
                    showNotification('Import Success', 'Configuration imported successfully!');
                } catch (err) {
                    showNotification('Import Error', 'Invalid configuration file format!');
                }
            };
            reader.readAsText(file);
        }
    };
    input.click();
});

// Notification system
function showNotification(title, message) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--bg-secondary);
        border: 1px solid var(--border-primary);
        border-radius: 8px;
        padding: 16px;
        max-width: 320px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 1000;
        transform: translateX(350px);
        transition: transform 0.3s ease;
    `;

    const content = document.createElement('div');
    const titleDiv = document.createElement('div');
    titleDiv.style.cssText = 'font-weight: 600; color: var(--accent-color); margin-bottom: 6px;';
    titleDiv.textContent = title;

    const msgDiv = document.createElement('div');
    msgDiv.style.cssText = 'font-size: 14px; color: var(--text-secondary); line-height: 1.4;';
    msgDiv.textContent = message;

    content.appendChild(titleDiv);
    content.appendChild(msgDiv);
    notification.appendChild(content);

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);

    setTimeout(() => {
        notification.style.transform = 'translateX(350px)';
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Initialize with welcome message
setTimeout(() => {
    showNotification('AI Scanner Ready', 'Advanced security scanning system initialized. Ready to protect your applications!');
}, 1000);

