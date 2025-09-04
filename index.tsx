import { GoogleGenAI } from "@google/genai";

// FIX: Declare Chart to inform TypeScript that it's available in the global scope (likely from a <script> tag).
declare var Chart: any;

// --- UI STATE ---
let selectedMonthIndex = 0;

// --- DATA STORE ---
const APP_STATE = {
    scenarios: {
        "Default Scenario": {
            projectPlan: [
                // Q1: Launch & Foundation
                { task: "SEO Landing Page & Foundational Blogs", quarter: "Q1", status: "Not Started", impact_channel: "Web Traffic", monthly_impact_values: [5000, 7500, 10000, 2500, 2500, 2500, 1000, 1000, 1000, 500, 500, 500] },
                { task: "PR & Media Outreach", quarter: "Q1", status: "Not Started", impact_channel: "Direct Referrals", monthly_impact_values: [100, 150, 200, 50, 50, 0, 0, 0, 0, 0, 0, 0] },
                { task: "Core ASO Assets & App Launch", quarter: "Q1", status: "Not Started", impact_channel: "ASO CVR Boost", monthly_impact_values: [0, 0.01, 0.02, 0.005, 0.005, 0, 0, 0, 0, 0, 0, 0] },
                { task: "Initial Ratings & Reviews Drive", quarter: "Q1", status: "Not Started", impact_channel: "ASO Rank Boost", monthly_impact_values: [0, 0, 10, 10, 5, 5, 3, 3, 2, 2, 1, 1] },
                // Q2: Optimization & Growth
                { task: "A/B Testing Store Creatives", quarter: "Q2", status: "Not Started", impact_channel: "ASO CVR Boost", monthly_impact_values: [0, 0, 0, 0.01, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01] },
                { task: "Publish 2 Data-driven SEO Blogs", quarter: "Q2", status: "Not Started", impact_channel: "Web Traffic", monthly_impact_values: [0, 0, 0, 7000, 10000, 12000, 14000, 15000, 15000, 15000, 15000, 15000] },
                { task: "Backlink Outreach Campaign", quarter: "Q2", status: "Not Started", impact_channel: "Web Traffic", monthly_impact_values: [0, 0, 0, 2000, 3000, 4000, 5000, 5000, 5000, 4000, 4000, 4000] },
                { task: "Keyword Optimization Cycle 1", quarter: "Q2", status: "Not Started", impact_channel: "ASO Rank Boost", monthly_impact_values: [0, 0, 0, 15, 10, 10, 5, 5, 3, 3, 2, 2] },
                // Q3: Scaling & Authority
                { task: "Run 2 In-App Events (Seasonal)", quarter: "Q3", status: "Not Started", impact_channel: "ASO Impressions", monthly_impact_values: [0, 0, 0, 0, 0, 0, 7500, 0, 7500, 0, 0, 0] },
                { task: "Video Content for Social & Web", quarter: "Q3", status: "Not Started", impact_channel: "Direct Referrals", monthly_impact_values: [0, 0, 0, 0, 0, 0, 150, 200, 250, 300, 300, 300] },
                // Q4: Refinement & Planning
                { task: "Advanced Keyword Research (Cycle 2)", quarter: "Q4", status: "Not Started", impact_channel: "ASO Rank Boost", monthly_impact_values: [0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5] },
                { task: "End-of-Year PR Summary", quarter: "Q4", status: "Not Started", impact_channel: "Direct Referrals", monthly_impact_values: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 500] },
            ],
            forecast: {
                assumptions: { webToStoreCTR: 0.01, storeCVR: 0.10, midwayDropOff: 0.80, impressionShare: { 1: 0.3, 2: 0.15, 3: 0.1, 5: 0.05, 10: 0.02, 20: 0.01, 50: 0.005 } },
                months: []
            },
            kpi: { totalInstallsTarget: 0, actualInstalls: 0 }
        }
    },
    activeScenario: "Default Scenario"
};

const getCurrentScenarioData = () => APP_STATE.scenarios[APP_STATE.activeScenario];

// --- INITIALIZATION & DATA GENERATION ---
function generateForecastMonths() {
    const scenario = getCurrentScenarioData();
    if (scenario.forecast.months && scenario.forecast.months.length > 0) return;

    const baseData = [
        { name: "M1", b_sv: 15000, b_rank: 100, b_browse: 500, b_direct: 50 }, { name: "M2", b_sv: 20000, b_rank: 90, b_browse: 600, b_direct: 75 },
        { name: "M3", b_sv: 25000, b_rank: 80, b_browse: 700, b_direct: 100 }, { name: "M4", b_sv: 30000, b_rank: 70, b_browse: 800, b_direct: 125 },
        { name: "M5", b_sv: 35000, b_rank: 60, b_browse: 900, b_direct: 150 }, { name: "M6", b_sv: 40000, b_rank: 50, b_browse: 1000, b_direct: 175 },
        { name: "M7", b_sv: 45000, b_rank: 45, b_browse: 1100, b_direct: 200 }, { name: "M8", b_sv: 50000, b_rank: 40, b_browse: 1200, b_direct: 225 },
        { name: "M9", b_sv: 55000, b_rank: 35, b_browse: 1300, b_direct: 250 }, { name: "M10", b_sv: 60000, b_rank: 30, b_browse: 1400, b_direct: 275 },
        { name: "M11", b_sv: 65000, b_rank: 25, b_browse: 1500, b_direct: 300 }, { name: "M12", b_sv: 70000, b_rank: 20, b_browse: 1600, b_direct: 325 },
    ];
    let months = [];
    baseData.forEach((d, i) => {
        const traffic = (i === 0) ? 26000 : Math.round(months[i-1].drivers.baseWebTraffic * 1.1);
        months.push({
            name: d.name,
            drivers: { baseWebTraffic: traffic, baseKeywordSearchVolume: d.b_sv, baseAvgKeywordRank: d.b_rank, baseBrowseImpressions: d.b_browse, baseDirectReferrals: d.b_direct },
            results: {}
        });
    });
    scenario.forecast.months = months;
}

// --- UTILITY FUNCTIONS ---
const formatNumber = (num, decimals = 0) => new Intl.NumberFormat('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(num);
const getImpressionShare = (rank) => {
    const shareMap = getCurrentScenarioData().forecast.assumptions.impressionShare;
    const ranks = Object.keys(shareMap).map(Number).sort((a, b) => a - b);
    for (const r of ranks) { if (rank <= r) return shareMap[r]; }
    return 0.001; 
};

// --- CALCULATION ENGINE ---
function calculateMonthlyForecasts() {
    const scenario = getCurrentScenarioData();
    let cumulativeInstalls = 0;
    scenario.forecast.months.forEach((month, i) => {
        month.results = {}; // Reset results
        month.results.finalWebTraffic = month.drivers.baseWebTraffic;
        month.results.finalRank = month.drivers.baseAvgKeywordRank;
        month.results.finalCVR = scenario.forecast.assumptions.storeCVR;
        let finalImpressions = month.drivers.baseBrowseImpressions;
        let finalDirect = month.drivers.baseDirectReferrals;

        scenario.projectPlan.forEach(task => {
            const value = task.monthly_impact_values[i];
            if (value === 0) return;
            switch(task.impact_channel) {
                case "Web Traffic": month.results.finalWebTraffic += value; break;
                case "ASO Rank Boost": month.results.finalRank -= value; break;
                case "ASO CVR Boost": month.results.finalCVR += value; break;
                case "ASO Impressions": finalImpressions += value; break;
                case "Direct Referrals": finalDirect += value; break;
            }
        });
        
        month.results.finalRank = Math.max(1, month.results.finalRank);
        
        const clicksFromWeb = month.results.finalWebTraffic * scenario.forecast.assumptions.webToStoreCTR;
        const landedOnStore = clicksFromWeb * scenario.forecast.assumptions.midwayDropOff;
        month.results.installsFromWeb = landedOnStore * month.results.finalCVR;

        const impressionShare = getImpressionShare(month.results.finalRank);
        const impressionsFromKeywords = month.drivers.baseKeywordSearchVolume * impressionShare;
        month.results.totalStoreImpressions = impressionsFromKeywords + finalImpressions;
        month.results.installsFromStoreSearch = month.results.totalStoreImpressions * month.results.finalCVR;
        
        month.results.totalMonthlyInstalls = month.results.installsFromWeb + month.results.installsFromStoreSearch + finalDirect;
        cumulativeInstalls += month.results.totalMonthlyInstalls;
        month.results.cumulativeInstalls = cumulativeInstalls;
    });
    scenario.kpi.totalInstallsTarget = cumulativeInstalls;
}

// --- RENDER FUNCTIONS ---
function renderAll() {
    calculateMonthlyForecasts();
    renderProjectPlan();
    renderForecastTable();
    renderKPIs();
    renderAssumptions();
    renderForecastControls();
    renderScenarioControls();
    renderCalculationsTab();
    updateCharts();
}

function renderProjectPlan() {
    const scenario = getCurrentScenarioData();
    const head = document.getElementById('project-plan-head');
    const body = document.getElementById('project-plan-body');
    if (!head || !body) return;
    let headHTML = `<tr><th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase sticky left-0 bg-gray-50 z-10 min-w-[250px]">Task</th><th class="px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase">QTR</th><th class="px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase min-w-[120px]">Status</th>${scenario.forecast.months.map(m => `<th class="px-2 py-3 text-right text-xs font-medium text-gray-500 uppercase min-w-[60px]">${m.name}</th>`).join('')}<th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase bg-gray-100 min-w-[100px]">Total Impact</th></tr>`;
    head.innerHTML = headHTML;
    
    let bodyHTML = '';
    const monthlyRunningTotals = Array(scenario.forecast.months.length).fill(0).map(() => ({
        webTraffic: 0,
        rankBoost: 0,
        cvrBoost: 0,
        impressions: 0,
        direct: 0,
    }));

    scenario.projectPlan.forEach((task, index) => {
        let totalImpact = 0;
        let monthlyImpactsHTML = '';
        let detailsRowHTML = '';
        
        task.monthly_impact_values.forEach((value, i) => {
            let impact = 0;
            let detailText = '-';
            if (value > 0) {
                const monthData = scenario.forecast.months[i];
                const { webToStoreCTR, midwayDropOff } = scenario.forecast.assumptions;

                switch(task.impact_channel) {
                    case "Web Traffic": {
                        const trafficBefore = monthData.drivers.baseWebTraffic + monthlyRunningTotals[i].webTraffic;
                        const trafficAfter = trafficBefore + value;
                        impact = value * webToStoreCTR * midwayDropOff * monthData.results.finalCVR;
                        detailText = `<div class='text-left text-xs p-1'>
                                        <p class='font-semibold text-gray-700'>Traffic: ${formatNumber(trafficBefore)} → ${formatNumber(trafficAfter)}</p>
                                        <p class='text-gray-500'>&nbsp;&nbsp;↳ +${formatNumber(value)} visitors from task</p>
                                        <p class='font-bold text-indigo-800'>= ${formatNumber(impact)} Installs</p>
                                     </div>`;
                        monthlyRunningTotals[i].webTraffic += value;
                        break;
                    }
                    case "ASO CVR Boost": {
                        const cvrBefore = scenario.forecast.assumptions.storeCVR + monthlyRunningTotals[i].cvrBoost;
                        const cvrAfter = cvrBefore + value;
                        const totalImpressions = monthData.results.totalStoreImpressions;
                        impact = totalImpressions * value; // Marginal impact is the impression base times the CVR delta.
                        detailText = `<div class='text-left text-xs p-1'>
                                        <p class='font-semibold text-gray-700'>Store CVR: ${formatNumber(cvrBefore*100,1)}% → ${formatNumber(cvrAfter*100,1)}%</p>
                                        <p class='text-gray-500'>&nbsp;&nbsp;↳ on ${formatNumber(totalImpressions)} total impressions</p>
                                        <p class='font-bold text-indigo-800'>= +${formatNumber(impact)} Installs</p>
                                     </div>`;
                        monthlyRunningTotals[i].cvrBoost += value;
                        break;
                    }
                    case "ASO Rank Boost": {
                        const rankBefore = monthData.drivers.baseAvgKeywordRank - monthlyRunningTotals[i].rankBoost;
                        const rankAfter = Math.max(1, rankBefore - value);
                        const shareBefore = getImpressionShare(rankBefore);
                        const shareAfter = getImpressionShare(rankAfter);
                        const impBoost = monthData.drivers.baseKeywordSearchVolume * (shareAfter - shareBefore);
                        impact = impBoost * monthData.results.finalCVR;
                         detailText = `<div class='text-left text-xs p-1'>
                                        <p class='font-semibold text-gray-700'>Avg. Rank: ${formatNumber(rankBefore, 0)} → ${formatNumber(rankAfter, 0)}</p>
                                        <p class='text-gray-500'>&nbsp;&nbsp;↳ +${formatNumber(impBoost)} keyword impressions</p>
                                        <p class='font-bold text-indigo-800'>= ${formatNumber(impact)} Installs</p>
                                     </div>`;
                        monthlyRunningTotals[i].rankBoost += value;
                        break;
                    }
                    case "ASO Impressions": {
                         impact = value * monthData.results.finalCVR;
                         detailText = `<div class='text-left text-xs p-1'>
                                        <p class='font-semibold text-gray-700'>+${formatNumber(value)} Impressions</p>
                                        <p class='text-gray-500'>&nbsp;&nbsp;↳ from In-App Event promotion</p>
                                        <p class='font-bold text-indigo-800'>= ${formatNumber(impact)} Installs</p>
                                    </div>`;
                         monthlyRunningTotals[i].impressions += value;
                         break;
                    }
                    case "Direct Referrals": {
                        impact = value;
                        detailText = `<div class='text-left text-xs p-1'>
                                        <p class='font-semibold text-gray-700'>+${formatNumber(value)} Direct Installs</p>
                                        <p class='text-gray-500'>&nbsp;&nbsp;↳ from PR / Social outreach</p>
                                        <p class='font-bold text-indigo-800'>= ${formatNumber(impact)} Installs</p>
                                    </div>`;
                        monthlyRunningTotals[i].direct += value;
                        break;
                    }
                }
            }
            totalImpact += impact;
            monthlyImpactsHTML += `<td class="px-2 py-2 text-right ${impact > 0 ? 'text-gray-700' : 'text-gray-400'}">${impact > 0 ? formatNumber(impact) : '-'}</td>`;
            detailsRowHTML += `<td class="px-2 py-2 align-top text-indigo-900">${detailText}</td>`;
        });
        
        const rowBgClass = index % 2 === 1 ? 'bg-gray-50' : 'bg-white';

        const taskCell = `<td class="px-4 py-2 whitespace-nowrap text-sm font-bold text-gray-800 sticky left-0 z-10 flex items-center min-w-[250px] ${rowBgClass}"><span class="toggle-btn mr-2 p-1 rounded-full hover:bg-gray-200" data-index="${index}"><svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg></span> ${task.task}</td>`;
        const quarterCell = `<td class="px-2 py-2 whitespace-nowrap text-sm text-center"><span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">${task.quarter}</span></td>`;
        const statusCell = `<td class="px-2 py-2 whitespace-nowrap text-sm text-gray-500 min-w-[120px]"><select class="status-select status-${task.status.replace(/\s+/g, '-')}" data-index="${index}"><option value="Not Started" ${task.status === 'Not Started' ? 'selected' : ''}>Not Started</option><option value="In Progress" ${task.status === 'In Progress' ? 'selected' : ''}>In Progress</option><option value="Completed" ${task.status === 'Completed' ? 'selected' : ''}>Completed</option><option value="Blocked" ${task.status === 'Blocked' ? 'selected' : ''}>Blocked</option></select></td>`;
        const totalImpactCell = `<td class="px-4 py-2 text-right text-sm font-bold text-indigo-700 bg-gray-100 min-w-[100px]">${formatNumber(totalImpact)}</td>`;
        
        bodyHTML += `<tr class="border-t ${rowBgClass}">${taskCell}${quarterCell}${statusCell}${monthlyImpactsHTML}${totalImpactCell}</tr>`;
        bodyHTML += `<tr id="details-${index}" class="details-row bg-indigo-50 border-t border-indigo-200"><td class="px-4 py-2 text-xs text-indigo-800 font-semibold sticky left-0 bg-indigo-50 z-10" colspan="3"><span class="pl-8">└─ Calculation Breakdown</span></td>${detailsRowHTML}<td class="bg-indigo-50"></td></tr>`;
    });
    body.innerHTML = bodyHTML;
    
    // Add event listeners for dynamic content
    body.querySelectorAll<HTMLSpanElement>('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', (event) => {
            const button = event.currentTarget as HTMLElement;
            const index = parseInt(button.dataset.index, 10);
            toggleDetails(index);
        });
    });
    body.querySelectorAll<HTMLSelectElement>('.status-select').forEach(select => {
        select.addEventListener('change', (event) => {
            handleStatusUpdate(event.currentTarget as HTMLSelectElement);
        });
    });
}

function renderForecastTable() {
    const scenario = getCurrentScenarioData();
    const table = document.getElementById('forecast-table');
    if (!table) return;
    const head = `<thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase sticky left-0 bg-gray-50 z-10 w-48">Metric</th>${scenario.forecast.months.map(m => `<th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">${m.name}</th>`).join('')}<th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase bg-gray-100">Total</th></tr></thead>`;
    let body = '<tbody class="bg-white divide-y divide-gray-200">';
    
    const totals: { [key: string]: number } = {
        baseWebTraffic: 0, installsFromWeb: 0, baseKeywordSearchVolume: 0, baseAvgKeywordRank: 0,
        baseBrowseImpressions: 0, totalStoreImpressions: 0, installsFromStoreSearch: 0,
        baseDirectReferrals: 0, totalMonthlyInstalls: 0, cumulativeInstalls: 0
    };

    scenario.forecast.months.forEach(m => {
        totals.baseWebTraffic += m.drivers.baseWebTraffic;
        totals.installsFromWeb += m.results.installsFromWeb;
        totals.baseKeywordSearchVolume += m.drivers.baseKeywordSearchVolume;
        totals.baseAvgKeywordRank += m.drivers.baseAvgKeywordRank;
        totals.baseBrowseImpressions += m.drivers.baseBrowseImpressions;
        totals.totalStoreImpressions += m.results.totalStoreImpressions;
        totals.installsFromStoreSearch += m.results.installsFromStoreSearch;
        totals.baseDirectReferrals += m.drivers.baseDirectReferrals;
        totals.totalMonthlyInstalls += m.results.totalMonthlyInstalls;
    });
    totals.baseAvgKeywordRank /= scenario.forecast.months.length;
    totals.cumulativeInstalls = scenario.forecast.months[scenario.forecast.months.length - 1]?.results.cumulativeInstalls || 0;

    const rows = [
        { label: 'Web Traffic (SEO)', tooltip: 'Editable: Base visitors to the app landing page from Google search.', key: 'baseWebTraffic', editable: true, format: (n) => formatNumber(n), section: 'Web Funnel Drivers' },
        { label: 'Installs from Web', tooltip: 'Calculated as: Web Traffic × 1% CTR × 80% Landing Rate × CVR', key: 'installsFromWeb', editable: false, format: (n) => formatNumber(n), bold: true },
        { label: 'Target Keyword Search Vol.', tooltip: 'Editable: Total monthly search volume for your target App Store keywords.', key: 'baseKeywordSearchVolume', editable: true, format: (n) => formatNumber(n), section: 'App Store Funnel Drivers' },
        { label: 'Avg. Keyword Rank', tooltip: 'Editable: Your projected average rank across target keywords. Lower is better.', key: 'baseAvgKeywordRank', editable: true, format: (n) => formatNumber(n) },
        { label: 'Browse & Other Impressions', tooltip: 'Editable: Impressions from App Store features, browse sections, etc.', key: 'baseBrowseImpressions', editable: true, format: (n) => formatNumber(n) },
        { label: 'Total App Store Impressions', tooltip: 'Calculated from keyword rank, search volume, and browse.', key: 'totalStoreImpressions', editable: false, format: (n) => formatNumber(n), sub: true },
        { label: 'Installs from App Store', tooltip: 'Calculated as: Total App Store Impressions × CVR', key: 'installsFromStoreSearch', editable: false, format: (n) => formatNumber(n), bold: true },
        { label: 'Direct & Referral Installs', tooltip: 'Editable: Installs from PR, social media, direct links.', key: 'baseDirectReferrals', editable: true, format: (n) => formatNumber(n), section: 'Other Drivers' },
        { label: 'Total Monthly Installs', tooltip: 'Sum of all install channels for the month.', key: 'totalMonthlyInstalls', editable: false, format: (n) => formatNumber(n), bold: true, section: 'Totals' },
        { label: 'Cumulative Installs', tooltip: 'Running total of all installs over the project duration.', key: 'cumulativeInstalls', editable: false, format: (n) => formatNumber(n) }
    ];

    let currentSection = "";
    rows.forEach(row => {
        if(row.section && row.section !== currentSection){ currentSection = row.section; body += `<tr><td colspan="${scenario.forecast.months.length + 2}" class="px-2 py-1 bg-blue-50 text-blue-800 font-semibold text-sm">${currentSection}</td></tr>`; }
        const rowData = scenario.forecast.months.map((m, i) => {
            const value = row.key in m.drivers ? m.drivers[row.key] : m.results[row.key];
            return `<td class="px-4 py-2 text-right text-gray-700"><div contenteditable="${row.editable}" class="${row.editable ? 'editable-cell' : ''}" data-month-index="${i}" data-key="${row.key}">${row.format(value)}</div></td>`;
        }).join('');
        const totalValue = totals[row.key];
        body += `<tr class="${row.bold ? 'font-bold' : ''}"><td class="px-4 py-2 whitespace-nowrap text-gray-800 sticky left-0 bg-white z-10 w-48 ${row.sub ? 'pl-8' : 'font-medium'}">${row.label}<span class="tooltip text-gray-400">(?)<span class="tooltiptext">${row.tooltip}</span></span></td>${rowData}<td class="px-4 py-2 text-right text-gray-800 bg-gray-50 ${row.bold ? 'font-bold' : ''}">${row.format(totalValue)}</td></tr>`;
    });
    body += '</tbody>';
    table.innerHTML = head + body;
    
    // Add event listeners
    table.querySelectorAll<HTMLDivElement>('.editable-cell').forEach(cell => {
        cell.addEventListener('blur', (event) => {
            handleForecastUpdate(event.currentTarget as HTMLDivElement);
        });
    });
}

function renderForecastControls() {
    const scenario = getCurrentScenarioData();
    const selector = document.getElementById('month-selector') as HTMLSelectElement;
    if (!selector) return;
    selector.innerHTML = scenario.forecast.months.map((month, index) =>
        `<option value="${index}">${month.name}</option>`
    ).join('');
    selector.value = selectedMonthIndex.toString();
}

function renderKPIs() {
    const scenario = getCurrentScenarioData();
    document.getElementById('installs-value').textContent = formatNumber(scenario.kpi.totalInstallsTarget);
    document.getElementById('installs-target-text').textContent = `Target: ${formatNumber(scenario.kpi.totalInstallsTarget)}`;

    const firstMonth = scenario.forecast.months[0];
    if (!firstMonth) {
        document.getElementById('top-driver-icon').innerHTML = '';
        document.getElementById('top-driver-text').textContent = 'N/A';
        document.getElementById('top-driver-subtext').textContent = 'No data available';
        document.getElementById('cvr-chart-text').innerHTML = `<div class="text-2xl font-bold text-gray-800">0%</div>`;
        return;
    }
    const drivers = { "Web SEO": firstMonth.results.installsFromWeb, "App Store": firstMonth.results.installsFromStoreSearch, "Direct": firstMonth.drivers.baseDirectReferrals };
    const topDriver = Object.entries(drivers).reduce((a, b) => a[1] > b[1] ? a : b);
    const driverIcons = { "Web SEO": `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9V3"></path></svg>`, "App Store": `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>`, "Direct": `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>` };
    document.getElementById('top-driver-icon').innerHTML = driverIcons[topDriver[0]];
    document.getElementById('top-driver-text').textContent = topDriver[0];
    document.getElementById('top-driver-subtext').textContent = `${formatNumber(topDriver[1])} installs`;
}

function renderAssumptions() {
    const scenario = getCurrentScenarioData();
    const list = document.getElementById('assumptions-list');
    list.innerHTML = `<li><strong>Web to Store CTR:</strong> ${scenario.forecast.assumptions.webToStoreCTR * 100}% of web visitors click through to the app store page.</li><li><strong>Store Page CVR:</strong> ${scenario.forecast.assumptions.storeCVR * 100}% of store page visitors install the app.</li><li><strong>Midway Drop-off:</strong> ${scenario.forecast.assumptions.midwayDropOff * 100}% of users who click from web successfully land on the app store page.</li><li><strong>Impression Share by Rank:</strong> Rank 1 gets 30%, Rank 3 gets 10%, etc. This models the click-through rate from keyword search results.</li>`;
}

function renderCalculationsTab() {
    const container = document.getElementById('content-calculations');
    if (!container) return;

    const assumptions = getCurrentScenarioData().forecast.assumptions;
    let impressionShareHTML = '';
    const sortedRanks = Object.keys(assumptions.impressionShare).map(Number).sort((a, b) => a - b);

    for (const rank of sortedRanks) {
        impressionShareHTML += `
            <div class="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                <label for="rank-${rank}" class="text-sm font-medium text-gray-700">Rank <= ${rank}</label>
                <div class="flex items-center">
                    <input type="number" step="0.1" id="rank-${rank}" data-rank-key="${rank}" value="${assumptions.impressionShare[rank] * 100}" class="assumption-input w-24 rounded-md border-gray-300 shadow-sm text-right focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                    <span class="ml-2 text-gray-500 text-sm">%</span>
                </div>
            </div>
        `;
    }

    container.innerHTML = `
        <h3 class="text-lg font-semibold text-gray-800 mb-2">Editable Model Calculations</h3>
        <p class="text-gray-600 mb-6 text-sm">Adjust the core drivers of the forecast model. Changes will update the entire dashboard in real-time.</p>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <!-- Left Column: Funnel Assumptions -->
            <div class="space-y-6">
                <div class="bg-white p-4 rounded-lg shadow-sm border">
                    <h4 class="font-semibold text-gray-700 mb-3 border-b pb-2">Funnel Conversion Rates</h4>
                    <div class="space-y-4 pt-2">
                        <!-- Web to Store CTR -->
                        <div>
                            <label for="webToStoreCTR" class="block text-sm font-medium text-gray-700">Web to Store CTR</label>
                            <p class="text-xs text-gray-500 mb-1">Percentage of web visitors who click through to the app store.</p>
                            <div class="flex items-center mt-2">
                                <input type="number" step="0.1" id="webToStoreCTR" data-assumption-key="webToStoreCTR" value="${assumptions.webToStoreCTR * 100}" class="assumption-input w-24 rounded-md border-gray-300 shadow-sm text-right focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                                <span class="ml-2 text-gray-500 text-sm">%</span>
                            </div>
                        </div>
                        <!-- Store Page CVR -->
                        <div>
                            <label for="storeCVR" class="block text-sm font-medium text-gray-700">Store Page CVR</label>
                            <p class="text-xs text-gray-500 mb-1">Percentage of store visitors who install the app.</p>
                            <div class="flex items-center mt-2">
                                <input type="number" step="0.1" id="storeCVR" data-assumption-key="storeCVR" value="${assumptions.storeCVR * 100}" class="assumption-input w-24 rounded-md border-gray-300 shadow-sm text-right focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                                <span class="ml-2 text-gray-500 text-sm">%</span>
                            </div>
                        </div>
                        <!-- Midway Drop-off -->
                        <div>
                            <label for="midwayDropOff" class="block text-sm font-medium text-gray-700">Midway Success Rate</label>
                            <p class="text-xs text-gray-500 mb-1">Percentage of users who successfully land on the store page after clicking from the web.</p>
                            <div class="flex items-center mt-2">
                                <input type="number" step="0.1" id="midwayDropOff" data-assumption-key="midwayDropOff" value="${assumptions.midwayDropOff * 100}" class="assumption-input w-24 rounded-md border-gray-300 shadow-sm text-right focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                                <span class="ml-2 text-gray-500 text-sm">%</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Column: Impression Share -->
            <div class="space-y-6">
                <div class="bg-white p-4 rounded-lg shadow-sm border">
                    <h4 class="font-semibold text-gray-700 mb-3 border-b pb-2">ASO Impression Share Model (by Rank)</h4>
                     <p class="text-xs text-gray-500 mb-3 pt-2">Models the click-through rate from keyword search results based on ranking position.</p>
                    <div class="space-y-1">
                        ${impressionShareHTML}
                    </div>
                </div>
            </div>
        </div>
    `;

    // Add event listeners
    container.querySelectorAll<HTMLInputElement>('.assumption-input').forEach(input => {
        input.addEventListener('input', (event) => {
            handleAssumptionUpdate(event.currentTarget as HTMLInputElement);
        });
    });
}

function renderScenarioControls() {
    const container = document.getElementById('scenario-controls');
    if (!container) return;

    const scenarios = Object.keys(APP_STATE.scenarios);
    const optionsHTML = scenarios.map(name =>
        `<option value="${name}" ${name === APP_STATE.activeScenario ? 'selected' : ''}>${name}</option>`
    ).join('');

    container.innerHTML = `
        <label for="scenario-selector" class="text-sm font-medium text-gray-700">Scenario:</label>
        <select id="scenario-selector" class="w-48 border-gray-300 rounded-md shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50 text-sm py-2 px-3">
            ${optionsHTML}
        </select>
        <button id="save-scenario-btn" class="text-sm py-2 px-4 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
            Save as New...
        </button>
    `;
}


let charts: { [key: string]: any } = {};
function updateCharts() {
    const scenario = getCurrentScenarioData();
    const monthlyInstalls = scenario.forecast.months.map(m => m.results.totalMonthlyInstalls);
    const cumulativeInstalls = scenario.forecast.months.map(m => m.results.cumulativeInstalls);
    const monthlyRank = scenario.forecast.months.map(m => m.results.finalRank);
    const monthLabels = scenario.forecast.months.map(m => m.name);
    
    const firstMonth = scenario.forecast.months[0];
    if (!firstMonth) return;

    if (charts.installsSparkline) charts.installsSparkline.destroy();
    const sparklineCtx = (document.getElementById('installsSparkline') as HTMLCanvasElement)?.getContext('2d');
    if (sparklineCtx) charts.installsSparkline = new Chart(sparklineCtx, { type: 'line', data: { labels: monthLabels, datasets: [{ data: monthlyInstalls, borderColor: '#3b82f6', tension: 0.4, borderWidth: 2, pointRadius: 0 }] }, options: { maintainAspectRatio: false, responsive: true, plugins: { legend: { display: false }, tooltip: { enabled: false } }, scales: { x: { display: false }, y: { display: false } } } });

    if (charts.cvrChart) charts.cvrChart.destroy();
    const cvrCtx = (document.getElementById('cvrChart') as HTMLCanvasElement)?.getContext('2d');
    const finalCVR = firstMonth.results.finalCVR;
    document.getElementById('cvr-chart-text').innerHTML = `<div class="text-2xl font-bold text-gray-800">${(finalCVR * 100).toFixed(1)}%</div>`;
    if (cvrCtx) charts.cvrChart = new Chart(cvrCtx, { type: 'doughnut', data: { datasets: [{ data: [finalCVR, 1 - finalCVR], backgroundColor: ['#1e3a8a', '#e5e7eb'], borderWidth: 0, }] }, options: { responsive: true, cutout: '80%', plugins: { legend: { display: false }, tooltip: { enabled: false } } } });

    if (charts.breakdownChart) charts.breakdownChart.destroy();
    const breakdownCtx = (document.getElementById('breakdownChart') as HTMLCanvasElement)?.getContext('2d');
    const chartTitleElement = document.getElementById('breakdown-chart-title');
    const selectedMonth = scenario.forecast.months[selectedMonthIndex];

    if (breakdownCtx && selectedMonth) {
        if (chartTitleElement) {
            chartTitleElement.textContent = `Installs Breakdown (${selectedMonth.name})`;
        }
        charts.breakdownChart = new Chart(breakdownCtx, { 
            type: 'bar', 
            data: { 
                labels: ['Web', 'Search', 'Direct'], 
                datasets: [{ 
                    label: 'Installs', 
                    data: [selectedMonth.results.installsFromWeb, selectedMonth.results.installsFromStoreSearch, selectedMonth.drivers.baseDirectReferrals], 
                    backgroundColor: ['#60a5fa', '#3b82f6', '#1e3a8a'], 
                }] 
            }, 
            options: { 
                indexAxis: 'y', 
                responsive: true, 
                maintainAspectRatio: false, 
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `Installs: ${formatNumber(context.raw as number)}`
                        }
                    }
                }, 
                scales: { 
                    x: { beginAtZero: true, grid: { display: false }, ticks: { callback: (value) => formatNumber(value as number), font: { size: 10 } } }, 
                    y: { grid: { display: false }, ticks: { font: { size: 10 } } } 
                } 
            } 
        });
    }
    
    // Cumulative Installs Chart
    if (charts.cumulativeInstallsChart) charts.cumulativeInstallsChart.destroy();
    const cumulativeCtx = (document.getElementById('cumulativeInstallsChart') as HTMLCanvasElement)?.getContext('2d');
    if(cumulativeCtx) {
        charts.cumulativeInstallsChart = new Chart(cumulativeCtx, {
            type: 'line',
            data: {
                labels: monthLabels,
                datasets: [{
                    label: 'Cumulative Installs',
                    data: cumulativeInstalls,
                    borderColor: '#1e3a8a',
                    backgroundColor: '#bfdbfe',
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: '#1e3a8a'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `Total Installs: ${formatNumber(context.raw as number)}`
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { callback: (value) => formatNumber(value as number) } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // Rank Improvement Chart
    if (charts.rankImprovementChart) charts.rankImprovementChart.destroy();
    const rankCtx = (document.getElementById('rankImprovementChart') as HTMLCanvasElement)?.getContext('2d');
    if(rankCtx) {
        charts.rankImprovementChart = new Chart(rankCtx, {
            type: 'line',
            data: {
                labels: monthLabels,
                datasets: [{
                    label: 'Average Rank',
                    data: monthlyRank,
                    borderColor: '#4b5563',
                    backgroundColor: '#d1d5db',
                    tension: 0.3,
                    pointBackgroundColor: '#4b5563'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `Average Rank: ${formatNumber(context.raw as number, 1)}`
                        }
                    }
                },
                scales: {
                    y: { 
                        reverse: true, // Lower rank is better, so reverse axis
                        title: { display: true, text: 'Avg. Keyword Rank' } 
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    }
}

// --- EVENT HANDLERS & UI ---
function toggleDetails(index: number) {
    const detailsRow = document.getElementById(`details-${index}`);
    const toggleBtn = detailsRow.previousElementSibling.querySelector('.toggle-btn');
    detailsRow.classList.toggle('open');
    toggleBtn.classList.toggle('open');
}

function handleStatusUpdate(element: HTMLSelectElement) {
    const index = parseInt(element.dataset.index, 10);
    const newStatus = element.value;
    getCurrentScenarioData().projectPlan[index].status = newStatus;
    element.className = `status-select status-${newStatus.replace(/\s+/g, '-')}`;
}

function handleForecastUpdate(element: HTMLDivElement) {
    const monthIndex = parseInt(element.dataset.monthIndex, 10);
    const key = element.dataset.key;
    const rawValue = element.textContent.replace(/,/g, '');
    const value = parseFloat(rawValue) || 0;
    const months = getCurrentScenarioData().forecast.months;
    if (months[monthIndex] && key in months[monthIndex].drivers) {
        months[monthIndex].drivers[key] = value;
        renderAll();
    }
}

function handleAssumptionUpdate(element: HTMLInputElement) {
    const assumptionKey = element.dataset.assumptionKey;
    const rankKey = element.dataset.rankKey;
    const rawValue = element.value;
    const assumptions = getCurrentScenarioData().forecast.assumptions;

    // Do not update if the input is empty or ends with a decimal (still typing)
    if (rawValue === '' || rawValue.endsWith('.')) {
        return;
    }
    const value = parseFloat(rawValue) / 100;

    if (isNaN(value)) return;

    if (assumptionKey) {
        assumptions[assumptionKey] = value;
    } else if (rankKey) {
        assumptions.impressionShare[rankKey] = value;
    }
    
    renderAll();
}

function handleMonthChange(element: HTMLSelectElement) {
    selectedMonthIndex = parseInt(element.value, 10);
    updateCharts();
}

function handleScenarioChange(element: HTMLSelectElement) {
    const newScenarioName = element.value;
    if (APP_STATE.scenarios[newScenarioName]) {
        APP_STATE.activeScenario = newScenarioName;
        renderAll();
    }
}

function handleSaveScenario() {
    const newName = prompt("Enter a name for the new scenario:", "My New Scenario");
    if (!newName) return; // User cancelled

    if (APP_STATE.scenarios[newName]) {
        alert("A scenario with this name already exists. Please choose a different name.");
        return;
    }

    const currentData = getCurrentScenarioData();
    // Deep copy the current scenario data
    APP_STATE.scenarios[newName] = JSON.parse(JSON.stringify(currentData));
    APP_STATE.activeScenario = newName;
    
    renderAll();
}

function switchTab(tabId: string) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById(`content-${tabId}`)?.classList.remove('hidden');
    document.querySelectorAll('.tab-button').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabId}`)?.classList.add('active');
}

function updateClock() {
    const clockElement = document.getElementById('live-clock');
    if (clockElement) {
        const options: Intl.DateTimeFormatOptions = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true };
        clockElement.textContent = new Date().toLocaleString('en-US', options);
    }
}

async function generateAndLoadMockups() {
    // Initialize the Gemini API client here, just before it's used.
    const ai = new GoogleGenAI({apiKey: process.env.API_KEY});

    const displayImage = document.getElementById('mockup-display') as HTMLImageElement;
    const thumbnailContainers = document.querySelectorAll('.mockup-thumbnail');
    if (!displayImage || thumbnailContainers.length === 0) return;

    const prompts = [
        "Design a screenshot that looks like a real App Store 'Top Charts' page. The screen should show a business finance app in the #1 position within the 'Top Business Apps' category. The app icon should be prominently displayed next to the number 1, with the app's name and a positive star rating. The title of the creative should be a powerful statement like: 'Ranked #1 for Business Owners.' This visual should immediately communicate authority and popularity.",
        "Create a compelling banner graphic for a business finance app. The creative should have a clean, modern design. The central element should be a large, bold number, like '1,000,000+' followed by the word 'Downloads'. The app's logo should be in a corner. The background can be a simple gradient that aligns with a professional brand's colors. The text should be a clear and proud statement like: 'Trusted by 1 Million+ Businesses Worldwide.'",
        "Design a sleek and professional screenshot that looks like it's a feature from the App Store's editorial section. It should have a heading like 'App of the Week'. Place a business finance app's icon and a prominent screenshot from the app within this framed layout. A simple badge that says 'Featured' or 'Editor's Choice' should be included. This creative leverages the authority and credibility of the app store platform.",
        "Design a screenshot that puts a user review and star rating for a business finance app front and center. A large, prominent star rating, 4.9 stars, should be the main visual element. Below it, in a slightly smaller font, include a compelling, positive user review: 'The best business app I've ever used. My productivity has skyrocketed.' The user's name, 'Emily R.', should be included for authenticity. This creative is a direct visual representation of user satisfaction."
    ];

    try {
        // Use a for...of loop to process requests sequentially to avoid rate limiting.
        for (const [index, prompt] of prompts.entries()) {
            const response = await ai.models.generateImages({
                model: 'imagen-4.0-generate-001',
                prompt: prompt,
                config: {
                    numberOfImages: 1,
                    outputMimeType: 'image/jpeg',
                    aspectRatio: '9:16',
                },
            });

            const container = thumbnailContainers[index];
            if (!container) continue;

            const base64ImageBytes = response.generatedImages[0].image.imageBytes;
            const imageUrl = `data:image/jpeg;base64,${base64ImageBytes}`;
            
            const imgElement = container.querySelector('img') as HTMLImageElement;
            const spinner = container.querySelector('.spinner') as HTMLDivElement;
            
            if(spinner) spinner.style.display = 'none';
            if(imgElement) {
                imgElement.src = imageUrl;
                imgElement.style.display = 'block';
            }

            if (index === 0) {
                displayImage.src = imageUrl;
            }
        }

    } catch (error) {
        console.error("Error generating mockup images:", error);
        // Fallback to showing broken image placeholders if generation fails
        thumbnailContainers.forEach(container => {
             const spinner = container.querySelector('.spinner') as HTMLDivElement;
             if(spinner) spinner.style.display = 'none';
             const imgElement = container.querySelector('img') as HTMLImageElement;
             if(imgElement) imgElement.style.display = 'block'; // Let the onerror handler take over
        });
    }
}

function initializeMockupViewer() {
    const thumbnails = document.querySelectorAll('.mockup-thumbnail');
    const displayImage = document.getElementById('mockup-display') as HTMLImageElement;

    if (!displayImage || thumbnails.length === 0) return;

    thumbnails.forEach(thumb => {
        thumb.addEventListener('click', () => {
            const newSrc = thumb.querySelector('img')?.src;
            // Only switch if the image has loaded
            if (newSrc && !newSrc.startsWith('data:image/svg+xml')) {
                thumbnails.forEach(t => t.classList.remove('active'));
                thumb.classList.add('active');
                displayImage.src = newSrc;
            }
        });
    });
}


// --- INITIAL LOAD & APP INITIALIZATION ---
function initializeApp() {
    // Setup listeners for static elements that are always in the DOM
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', (event) => {
            const tabId = (event.currentTarget as HTMLElement).dataset.tabId;
            if (tabId) {
                switchTab(tabId);
            }
        });
    });

    const monthSelector = document.getElementById('month-selector');
    if (monthSelector) {
        monthSelector.addEventListener('change', (event) => {
            handleMonthChange(event.currentTarget as HTMLSelectElement);
        });
    }

    // Add new listeners for scenario controls
    const header = document.querySelector('header');
    if (header) {
        header.addEventListener('change', (event) => {
            const target = event.target as HTMLElement;
            if (target.id === 'scenario-selector') {
                handleScenarioChange(target as HTMLSelectElement);
            }
        });
        header.addEventListener('click', (event) => {
            const target = event.target as HTMLElement;
            if (target.id === 'save-scenario-btn' || target.closest('#save-scenario-btn')) {
                handleSaveScenario();
            }
        });
    }

    initializeMockupViewer();
    generateAndLoadMockups(); // Generate images on load

    // Start clock
    setInterval(updateClock, 1000);
    updateClock();
}

document.addEventListener('DOMContentLoaded', () => {
    generateForecastMonths();
    renderAll();
    initializeApp();
});
