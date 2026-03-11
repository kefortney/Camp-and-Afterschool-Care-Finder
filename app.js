// ===== State =====
let activeCategory = 'camp';
let allPrograms = [];
let lastFiltered = [];
let currentView = 'list';
let mapInstance = null;
let calendarState = { year: 2026, month: 5 };
let currentProgram = null;
let orgMap = new Map(); // orgId -> org record, populated at init

let activeFilters = {
  search: '',
  type: '',
  grades: '',
  city: '',
  subject: '',
  week: '',
  maxCost: '',
  scholarship: '',
  county: '',
  stars: '',
  status: ''
};

// ===== DOM References =====
const searchInput = document.getElementById('searchInput');
const filterType = document.getElementById('filterType');
const filterGrades = document.getElementById('filterGrades');
const filterCity = document.getElementById('filterCity');
const filterSubject = document.getElementById('filterSubject');
const filterWeek = document.getElementById('filterWeek');
const filterMaxCost = document.getElementById('filterMaxCost');
const filterScholarship = document.getElementById('filterScholarship');
const filterCounty = document.getElementById('filterCounty');
const filterStars = document.getElementById('filterStars');
const filterStatus = document.getElementById('filterStatus');

const labelType = document.getElementById('labelType');
const labelGrades = document.getElementById('labelGrades');
const labelCity = document.getElementById('labelCity');
const labelSubject = document.getElementById('labelSubject');
const labelWeek = document.getElementById('labelWeek');
const labelCounty = document.getElementById('labelCounty');
const labelStars = document.getElementById('labelStars');
const labelStatus = document.getElementById('labelStatus');
const labelMaxCost = document.getElementById('labelMaxCost');
const labelScholarship = document.getElementById('labelScholarship');

const groupCounty = document.getElementById('groupCounty');
const groupStars = document.getElementById('groupStars');
const groupStatus = document.getElementById('groupStatus');

const cardsGrid = document.getElementById('cardsGrid');
const resultsCount = document.getElementById('resultsCount');
const noResults = document.getElementById('noResults');
const noResultsTitle = document.getElementById('noResultsTitle');
const noResultsHint = document.getElementById('noResultsHint');
const btnReset = document.getElementById('btnReset');
const btnClearSearch = document.getElementById('btnClearSearch');
const modalOverlay = document.getElementById('modalOverlay');
const modalClose = document.getElementById('modalClose');

const tabButtons = document.querySelectorAll('.tab-btn');

// ===== Helpers =====
const gradeOrder = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_FULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

const categoryUiConfig = {
  camp: {
    searchPlaceholder: 'Search camps by name, organization, or activity...',
    typeLabel: 'Camp Type',
    typeAny: 'All Camp Types',
    gradeLabel: 'Grade',
    gradeAny: 'All Grades',
    cityLabel: 'City',
    cityAny: 'All Cities',
    subjectLabel: 'Subject / Activity',
    subjectAny: 'All Activities',
    weekLabel: 'Week',
    countyLabel: 'County',
    starsLabel: 'STARS Rating',
    statusLabel: 'Status',
    maxCostLabel: 'Max Cost (weekly)',
    scholarshipLabel: 'Financial Aid',
    emptyTitle: 'No camps found',
    emptyHint: 'Try adjusting your search or filters to find camps in your area.'
  },
  afterschool: {
    searchPlaceholder: 'Search afterschool programs by provider, town, or keyword...',
    typeLabel: 'Program Model',
    typeAny: 'All Program Models',
    gradeLabel: 'Grade Served',
    gradeAny: 'All Grades',
    cityLabel: 'City',
    cityAny: 'All Cities',
    subjectLabel: 'Enrichment Tags',
    subjectAny: 'All Tags',
    weekLabel: 'Week',
    countyLabel: 'County',
    starsLabel: 'STARS Rating',
    statusLabel: 'Status',
    maxCostLabel: 'Max Cost (weekly)',
    scholarshipLabel: 'Financial Aid',
    emptyTitle: 'No afterschool programs found',
    emptyHint: 'Try broadening county, rating, or status filters to see more options.'
  },
  daycare: {
    searchPlaceholder: 'Search daycare providers by name, town, or keyword...',
    typeLabel: 'Care Model',
    typeAny: 'All Care Models',
    gradeLabel: 'Age / Grade',
    gradeAny: 'All Ages / Grades',
    cityLabel: 'City',
    cityAny: 'All Cities',
    subjectLabel: 'Program Tags',
    subjectAny: 'All Tags',
    weekLabel: 'Week',
    countyLabel: 'County',
    starsLabel: 'STARS Rating',
    statusLabel: 'Status',
    maxCostLabel: 'Max Cost (weekly)',
    scholarshipLabel: 'Financial Aid',
    emptyTitle: 'No daycare providers found',
    emptyHint: 'Try broadening county, rating, or status filters to see more providers.'
  }
};

function parseNumber(raw) {
  const n = parseInt(String(raw || '').replace(/[^0-9-]/g, ''), 10);
  return Number.isFinite(n) ? n : 0;
}

function yesNoToBool(raw) {
  return String(raw || '').trim().toLowerCase() === 'yes';
}

function asString(raw) {
  return String(raw || '').trim();
}

function gradeToIndex(g) {
  return gradeOrder.indexOf(String(g));
}

function gradesOverlap(progMin, progMax, filterGrade) {
  if (!filterGrade) return true;
  const pMin = gradeToIndex(progMin);
  const pMax = gradeToIndex(progMax);
  const fIdx = gradeToIndex(filterGrade);
  if (pMin < 0 || pMax < 0) return true;
  return fIdx >= pMin && fIdx <= pMax;
}

function normalizeCostToWeekly(cost, period) {
  if (period === 'week') return cost;
  if (period === 'month') return cost / 4;
  if (period === 'day') return cost * 5;
  return cost;
}

function formatCost(cost, period) {
  if (!cost || cost === 0) return 'Contact for pricing';
  return `$${cost.toLocaleString()} / ${period}`;
}

function parseDate(iso) {
  if (!iso) return null;
  const parts = String(iso).split('-').map(Number);
  if (parts.length !== 3 || parts.some(n => !Number.isFinite(n))) return null;
  return new Date(parts[0], parts[1] - 1, parts[2]);
}

function toIso(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function getMondayOfWeek(d) {
  const result = new Date(d);
  const day = result.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  result.setDate(result.getDate() + diff);
  return result;
}

function getFridayOfWeek(monday) {
  const d = new Date(monday);
  d.setDate(d.getDate() + 4);
  return d;
}

function fmtWeekRange(startIso, endIso) {
  const s = parseDate(startIso);
  if (!s) return '';
  const label = `${MONTH_ABBR[s.getMonth()]} ${s.getDate()}`;
  const e = parseDate(endIso);
  if (!e) return `Week of ${label}`;
  if (s.getMonth() === e.getMonth()) return `${label}-${e.getDate()}`;
  return `${label} - ${MONTH_ABBR[e.getMonth()]} ${e.getDate()}`;
}

function fmtWeekOption(mondayIso) {
  const mon = parseDate(mondayIso);
  const fri = getFridayOfWeek(mon);
  const monLabel = `${MONTH_ABBR[mon.getMonth()]} ${mon.getDate()}`;
  if (mon.getMonth() === fri.getMonth()) {
    return `${monLabel}-${fri.getDate()}, ${fri.getFullYear()}`;
  }
  return `${monLabel} - ${MONTH_ABBR[fri.getMonth()]} ${fri.getDate()}, ${fri.getFullYear()}`;
}

function show(el, isVisible) {
  if (!el) return;
  el.classList.toggle('hidden', !isVisible);
}

function categoryLabel(cat) {
  if (cat === 'camp') return 'camps';
  if (cat === 'afterschool') return 'afterschool programs';
  return 'daycare providers';
}

function categoryUi() {
  return categoryUiConfig[activeCategory] || categoryUiConfig.camp;
}

function applyCategoryUiText() {
  const ui = categoryUi();

  searchInput.placeholder = ui.searchPlaceholder;
  if (labelType) labelType.textContent = ui.typeLabel;
  if (labelGrades) labelGrades.textContent = ui.gradeLabel;
  if (labelCity) labelCity.textContent = ui.cityLabel;
  if (labelSubject) labelSubject.textContent = ui.subjectLabel;
  if (labelWeek) labelWeek.textContent = ui.weekLabel;
  if (labelCounty) labelCounty.textContent = ui.countyLabel;
  if (labelStars) labelStars.textContent = ui.starsLabel;
  if (labelStatus) labelStatus.textContent = ui.statusLabel;
  if (labelMaxCost) labelMaxCost.textContent = ui.maxCostLabel;
  if (labelScholarship) labelScholarship.textContent = ui.scholarshipLabel;
  if (noResultsTitle) noResultsTitle.textContent = ui.emptyTitle;
  if (noResultsHint) noResultsHint.textContent = ui.emptyHint;

  const gradeAnyOption = filterGrades.querySelector('option[value=""]');
  if (gradeAnyOption) gradeAnyOption.textContent = ui.gradeAny;
}

function normalizeCampPrograms(camps) {
  return camps.map(p => ({
    ...p,
    uid: `camp-${p.id}`,
    category: 'camp',
    county: '',
    starsLevel: '',
    referralStatus: 'Active',
    providerProgramType: p.type
  }));
}

// ===== Organizations =====
const ORG_PATTERNS = [
  { re: /^Rec Kids/i,                                    orgId: 'rec-kids-essex' },
  { re: /^Part 2/i,                                      orgId: 'part-2' },
  { re: /Heartworks/i,                                   orgId: 'heartworks' },
  { re: /Boys and Girls Club of Burlington/i,            orgId: 'bgc-burlington' },
  { re: /Boys & Girls Club of Rutland/i,                 orgId: 'bgc-rutland' },
  { re: /Burlington City Kids/i,                         orgId: 'burlington-city-kids' },
  { re: /Burlington Vt School District Afterschool/i,    orgId: 'burlington-sd' },
  { re: /King Street Center/i,                           orgId: 'king-street-center' },
  { re: /Miller Community/i,                             orgId: 'miller-rec' },
  { re: /ONE Arts/i,                                     orgId: 'one-arts' },
  { re: /Milton Family/i,                                orgId: 'milton-family-center' },
  { re: /Thrive After School/i,                          orgId: 'thrive-winooski' },
  { re: /Healthy Kids Extended Day/i,                    orgId: 'healthy-kids' },
  { re: /Y School Age Program/i,                         orgId: 'y-gbymca' },
  { re: /The Y ASPIRE/i,                                 orgId: 'y-aspire' },
  { re: /^Community Connections/i,                       orgId: 'community-connections' },
  { re: /^School'?s Out/i,                               orgId: 'south-burlington-sd' },
  { re: /^A\.?C\.?E\.?\s+(Before|After|At)/i,           orgId: 'ace-colchester' },
];

function resolveOrgId(providerName) {
  for (const { re, orgId } of ORG_PATTERNS) {
    if (re.test(providerName)) return orgId;
  }
  return null;
}

async function loadOrganizations() {
  try {
    const resp = await fetch('data/organizations.csv', { cache: 'no-store' });
    if (!resp.ok) return;
    const text = await resp.text();
    const rows = parseCsv(text);
    rows.forEach(row => {
      const id = asString(row['orgId']);
      if (id) orgMap.set(id, row);
    });
  } catch (err) {
    console.error('Could not load organizations CSV:', err);
  }
}

function parseCsv(csvText) {
  const rows = [];
  let cur = '';
  let row = [];
  let inQuotes = false;

  for (let i = 0; i < csvText.length; i++) {
    const ch = csvText[i];
    const next = csvText[i + 1];

    if (ch === '"') {
      if (inQuotes && next === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (ch === ',' && !inQuotes) {
      row.push(cur);
      cur = '';
      continue;
    }

    if ((ch === '\n' || ch === '\r') && !inQuotes) {
      if (ch === '\r' && next === '\n') i++;
      row.push(cur);
      const hasData = row.some(cell => asString(cell) !== '');
      if (hasData) rows.push(row);
      row = [];
      cur = '';
      continue;
    }

    cur += ch;
  }

  if (cur.length || row.length) {
    row.push(cur);
    const hasData = row.some(cell => asString(cell) !== '');
    if (hasData) rows.push(row);
  }

  if (rows.length === 0) return [];

  const header = rows[0].map(h => asString(h));
  return rows.slice(1).map(r => {
    const obj = {};
    header.forEach((h, idx) => {
      obj[h] = r[idx] ?? '';
    });
    return obj;
  });
}

function providerSubjects(programType, row) {
  const subjects = [];
  if (String(programType).includes('Afterschool')) subjects.push('Afterschool');
  if (yesNoToBool(row['Prequalified Prekindgarten Program'])) subjects.push('Pre-K');
  if (yesNoToBool(row['Reported Food Program Participation'])) subjects.push('Food Program');
  if (yesNoToBool(row['Special Services Status'])) subjects.push('Special Services');
  if (row['Current STARS Level']) subjects.push(String(row['Current STARS Level']).trim());
  return [...new Set(subjects)];
}

function providerDescription(row) {
  const model = asString(row['Provider Program Type']);
  const stars = asString(row['Current STARS Level']);
  const county = asString(row['County']);
  const status = asString(row['Provider Referral Status']) || 'Unknown';
  const schedule = asString(row['Special Schedule']);
  const details = [model, stars, county ? `${county} County` : '', `Status: ${status}`, schedule].filter(Boolean);
  return details.join(' · ');
}

function providerToProgram(row) {
  const programType = asString(row['Provider Program Type']);
  const isAfterschool = programType.includes('Afterschool');
  const orgId = resolveOrgId(asString(row['Provider Name']));
  const org = orgId ? orgMap.get(orgId) : null;

  const schoolAgeCap = parseNumber(row['School Age Licensed Capacity']);
  const infantCap = parseNumber(row['Infant Licensed Capacity']);
  const toddlerCap = parseNumber(row['Toddler Licensed Capacity']);
  const preschoolCap = parseNumber(row['Preschool Licensed Capacity']);

  let gradesMin = '';
  let gradesMax = '';
  if (schoolAgeCap > 0) {
    gradesMin = 'K';
    gradesMax = '12';
  }

  let ageMin = null;
  let ageMax = null;
  if (infantCap > 0) ageMin = 0;
  if (toddlerCap > 0) ageMax = 4;
  if (preschoolCap > 0 && ageMax === null) ageMax = 5;
  if (schoolAgeCap > 0 && ageMax === null) ageMax = 17;

  const start = asString(row['Usual Program Start']);
  const end = asString(row['Usual Program End']);
  const hours = start && end ? `${start} - ${end}` : '';

  const addr1 = asString(row['Address 1']);
  const addr2 = asString(row['Address 2']);
  const address = [addr1, addr2].filter(Boolean).join(', ');

  return {
    uid: `provider-${asString(row['Provider ID'])}`,
    id: parseNumber(row['Provider ID']),
    category: isAfterschool ? 'afterschool' : 'daycare',
    type: isAfterschool ? 'Afterschool Care' : 'Daycare',
    providerProgramType: programType,
    name: asString(row['Provider Name']) || 'Unknown Provider',
    organization: asString(row['License Type']) || asString(row['Provider Name']) || '',
    address,
    city: asString(row['Provider Town']),
    state: 'VT',
    zip: asString(row['Zip Code']),
    phone: asString(row['Phone Number']),
    email: asString(row['Email Address']),
    website: org ? asString(org['website']) : '',
    gradesMin,
    gradesMax,
    ageMin,
    ageMax,
    cost: 0,
    costPeriod: 'session',
    scholarshipAvailable: false,
    hours,
    daysOffered: '',
    sessionType: asString(row['Special Schedule']) || 'Year-round',
    subjects: providerSubjects(programType, row),
    description: providerDescription(row),
    indoorOutdoor: 'Both',
    transportation: false,
    mealsProvided: yesNoToBool(row['Reported Food Program Participation']),
    acceptingRegistration: asString(row['Provider Referral Status']) !== 'Inactive',
    startDate: '',
    endDate: '',
    county: asString(row['County']),
    starsLevel: asString(row['Current STARS Level']),
    referralStatus: asString(row['Provider Referral Status']) || 'Unknown',
    orgId,
    orgName: org ? asString(org['name']) : ''
  };
}

async function loadProviderPrograms() {
  try {
    const resp = await fetch('data/providers/provider_data_20260304.csv', { cache: 'no-store' });
    if (!resp.ok) return [];
    const text = await resp.text();
    const rows = parseCsv(text);
    return rows.map(providerToProgram);
  } catch (err) {
    console.error('Could not load provider CSV:', err);
    return [];
  }
}

function subsidizedToProgram(row, idx) {
  const subjects = asString(row['Subjects']).split('|').map(s => s.trim()).filter(Boolean);
  const orgId = asString(row['orgId']) || null;
  const org = orgId ? orgMap.get(orgId) : null;
  return {
    uid: `subsidized-${idx}`,
    id: idx,
    category: 'afterschool',
    type: '21CCLC Afterschool (Free)',
    isFree: true,
    providerProgramType: asString(row['Funding Source']) || '21st Century Community Learning Centers',
    name: asString(row['Name']) || 'Unknown Program',
    organization: asString(row['Organization']) || asString(row['Supervisory Union']),
    address: asString(row['Address']),
    city: asString(row['City']),
    state: asString(row['State']) || 'VT',
    zip: asString(row['Zip']),
    phone: asString(row['Phone']) || (org ? asString(org['phone']) : ''),
    email: asString(row['Email']) || (org ? asString(org['email']) : ''),
    website: asString(row['Website']) || (org ? asString(org['website']) : ''),
    gradesMin: asString(row['Grades Min']),
    gradesMax: asString(row['Grades Max']),
    ageMin: null,
    ageMax: null,
    cost: 0,
    costPeriod: 'session',
    scholarshipAvailable: true,
    hours: asString(row['Hours']),
    daysOffered: 'Monday-Friday',
    sessionType: asString(row['Session Type']) || 'School Year Only',
    subjects,
    description: asString(row['Description']),
    indoorOutdoor: 'Both',
    transportation: false,
    mealsProvided: false,
    acceptingRegistration: true,
    startDate: '',
    endDate: '',
    county: asString(row['County']),
    starsLevel: '',
    referralStatus: 'Active',
    orgId,
    orgName: org ? asString(org['name']) : (asString(row['Organization']) || '')
  };
}

async function loadSubsidizedPrograms() {
  try {
    const resp = await fetch('data/subsidized/21cclc_2025_2026.csv', { cache: 'no-store' });
    if (!resp.ok) return [];
    const text = await resp.text();
    const rows = parseCsv(text);
    return rows.map((row, idx) => subsidizedToProgram(row, idx));
  } catch (err) {
    console.error('Could not load subsidized CSV:', err);
    return [];
  }
}

function categoryPrograms() {
  return allPrograms.filter(p => p.category === activeCategory);
}

function resetFilterOptions(selectEl, firstLabel) {
  selectEl.innerHTML = '';
  const first = document.createElement('option');
  first.value = '';
  first.textContent = firstLabel;
  selectEl.appendChild(first);
}

function populateDropdown(selectEl, values, firstLabel) {
  resetFilterOptions(selectEl, firstLabel);
  values.forEach(v => {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    selectEl.appendChild(opt);
  });
}

function populateWeekDropdown(programs) {
  resetFilterOptions(filterWeek, 'Any Week');
  const mondaySet = new Set();
  programs.forEach(p => {
    if (!p.startDate) return;
    const d = parseDate(p.startDate);
    if (!d) return;
    mondaySet.add(toIso(getMondayOfWeek(d)));
  });
  [...mondaySet].sort().forEach(iso => {
    const opt = document.createElement('option');
    opt.value = iso;
    opt.textContent = fmtWeekOption(iso);
    filterWeek.appendChild(opt);
  });
}

function updateFilterVisibility() {
  const isCamp = activeCategory === 'camp';
  const isProvider = !isCamp;

  show(filterSubject.closest('.filter-group'), isCamp);
  show(filterWeek.closest('.filter-group'), isCamp);
  show(filterMaxCost.closest('.filter-group'), isCamp);
  show(filterScholarship.closest('.filter-group'), isCamp);
  show(groupCounty, isProvider);
  show(groupStars, isProvider);
  show(groupStatus, isProvider);
}

function populateFiltersForCategory() {
  const ui = categoryUi();
  const programs = categoryPrograms();

  const types = [...new Set(programs.map(p => p.providerProgramType || p.type).filter(Boolean))].sort();
  const cities = [...new Set(programs.map(p => p.city).filter(Boolean))].sort();
  const subjects = [...new Set(programs.flatMap(p => p.subjects || []).filter(Boolean))].sort();
  const counties = [...new Set(programs.map(p => p.county).filter(Boolean))].sort();
  const stars = [...new Set(programs.map(p => p.starsLevel).filter(Boolean))].sort();

  populateDropdown(filterType, types, ui.typeAny);
  populateDropdown(filterCity, cities, ui.cityAny);
  populateDropdown(filterSubject, subjects, ui.subjectAny);
  populateDropdown(filterCounty, counties, 'All Counties');
  populateDropdown(filterStars, stars, 'Any Rating');
  populateWeekDropdown(programs);

  filterType.value = activeFilters.type;
  filterCity.value = activeFilters.city;
  filterSubject.value = activeFilters.subject;
  filterCounty.value = activeFilters.county;
  filterStars.value = activeFilters.stars;
  filterStatus.value = activeFilters.status;
  filterWeek.value = activeFilters.week;
}

function applyFilters() {
  const search = activeFilters.search.toLowerCase().trim();
  const isCamp = activeCategory === 'camp';

  return categoryPrograms().filter(p => {
    if (search) {
      const haystack = [
        p.name,
        p.organization,
        p.city,
        p.county,
        p.description,
        ...(p.subjects || [])
      ].join(' ').toLowerCase();
      if (!haystack.includes(search)) return false;
    }

    const model = p.providerProgramType || p.type;
    if (activeFilters.type && model !== activeFilters.type) return false;

    if (activeFilters.grades && !gradesOverlap(p.gradesMin, p.gradesMax, activeFilters.grades)) return false;
    if (activeFilters.city && p.city !== activeFilters.city) return false;
    if (activeFilters.subject && !(p.subjects || []).includes(activeFilters.subject)) return false;

    if (isCamp) {
      if (activeFilters.maxCost !== '') {
        const max = parseInt(activeFilters.maxCost, 10);
        if (p.cost !== 0 && normalizeCostToWeekly(p.cost, p.costPeriod) > max) return false;
      }
      if (activeFilters.scholarship === 'yes' && !p.scholarshipAvailable) return false;
      if (activeFilters.week) {
        if (!p.startDate) return true;
        const d = parseDate(p.startDate);
        if (!d) return true;
        const campMonday = toIso(getMondayOfWeek(d));
        if (campMonday !== activeFilters.week) return false;
      }
    } else {
      if (activeFilters.county && p.county !== activeFilters.county) return false;
      if (activeFilters.stars && p.starsLevel !== activeFilters.stars) return false;
      if (activeFilters.status && p.referralStatus !== activeFilters.status) return false;
    }

    return true;
  });
}

// ===== Render Cards =====
function renderCards(programs) {
  cardsGrid.innerHTML = '';

  if (programs.length === 0) {
    noResults.style.display = 'block';
    return;
  }
  noResults.style.display = 'none';

  const sorted = [...programs].sort((a, b) => {
    if (a.startDate && b.startDate) return a.startDate.localeCompare(b.startDate);
    if (a.startDate) return -1;
    if (b.startDate) return 1;
    return a.name.localeCompare(b.name);
  });

  sorted.forEach(p => {
    const card = document.createElement('article');
    card.className = 'program-card';

    const badgeClass = p.category === 'camp' ? 'badge-camp'
      : p.category === 'afterschool' ? 'badge-afterschool'
      : 'badge-both';

    const costDisplay = p.isFree
      ? '<span class="free-badge">Free (Federally Funded)</span>'
      : (!p.cost || p.cost === 0)
        ? '<span class="free-badge">Contact for pricing</span>'
        : `<span>${formatCost(p.cost, p.costPeriod)}</span>`;

    const scholarshipHtml = p.scholarshipAvailable
      ? '<span class="scholarship-badge">Aid Available</span>'
      : '';

    const registrationHtml = !p.acceptingRegistration
      ? '<span class="registration-closed">Closed</span>'
      : '';

    const subjectTags = (p.subjects || []).slice(0, 3).map(s => `<span class="tag">${s}</span>`).join('');
    const locationText = [p.city, p.state].filter(Boolean).join(', ') || 'Vermont';
    const gradesText = (p.gradesMin && p.gradesMax)
      ? `Grades ${p.gradesMin}-${p.gradesMax}`
      : (p.ageMin !== null && p.ageMax !== null ? `Ages ${p.ageMin}-${p.ageMax}` : '');

    const weekBadgeHtml = p.startDate
      ? `<span class="week-badge">${fmtWeekRange(p.startDate, p.endDate)}</span>`
      : '';

    card.innerHTML = `
      <div class="card-header">
        <div class="card-header-top">
          <span class="card-type-badge ${badgeClass}">${p.type}</span>
          ${weekBadgeHtml}
        </div>
        <div class="card-title">${p.name}</div>
        <div class="card-org">${p.organization || ''}</div>
      </div>
      <div class="card-body">
        <p class="card-description">${p.description || ''}</p>
        <div class="card-meta">
          <div class="meta-item"><span class="meta-icon">📍</span><span class="meta-value">${locationText}</span></div>
          ${p.county ? `<div class="meta-item"><span class="meta-icon">🧭</span><span class="meta-value">${p.county} County</span></div>` : ''}
          ${gradesText ? `<div class="meta-item"><span class="meta-icon">🎓</span><span class="meta-value">${gradesText}</span></div>` : ''}
          ${p.hours ? `<div class="meta-item"><span class="meta-icon">🕐</span><span class="meta-value">${p.hours}</span></div>` : ''}
          <div class="meta-item"><span class="meta-icon">💰</span><span class="meta-value">${costDisplay} ${scholarshipHtml}</span></div>
          ${p.starsLevel ? `<div class="meta-item"><span class="meta-icon">⭐</span><span class="meta-value">${p.starsLevel}</span></div>` : ''}
        </div>
        <div class="tags">${subjectTags}</div>
      </div>
      <div class="card-footer">
        <button class="btn-details" data-id="${p.uid}">View Details</button>
        ${p.website ? `<a class="btn-website" href="${p.website}" target="_blank" rel="noopener noreferrer">Visit Website</a>` : ''}
        ${registrationHtml}
      </div>
    `;

    card.querySelector('.btn-details').addEventListener('click', () => openModal(p));
    cardsGrid.appendChild(card);
  });
}

// ===== Calendar =====
function renderCalendar(programs) {
  const { year, month } = calendarState;
  const monthLabel = document.getElementById('calMonthLabel');
  const grid = document.getElementById('calendarGrid');
  const undatedNote = document.getElementById('calUndatedNote');

  monthLabel.textContent = `${MONTH_FULL[month]} ${year}`;

  const dayMap = {};
  const undated = [];

  programs.forEach(p => {
    if (!p.startDate) {
      undated.push(p);
      return;
    }

    const start = parseDate(p.startDate);
    const end = p.endDate ? parseDate(p.endDate) : start;
    if (!start || !end) {
      undated.push(p);
      return;
    }

    const cur = new Date(start);
    while (cur <= end) {
      const iso = toIso(cur);
      if (!dayMap[iso]) dayMap[iso] = [];
      dayMap[iso].push(p);
      cur.setDate(cur.getDate() + 1);
    }
  });

  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startDow = firstDay.getDay();

  const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  let html = '<div class="cal-header-row">' + DOW.map(d => `<div class="cal-dow">${d}</div>`).join('') + '</div>';
  html += '<div class="cal-body">';

  for (let i = 0; i < startDow; i++) {
    html += '<div class="cal-day cal-day-empty"></div>';
  }

  for (let day = 1; day <= lastDay.getDate(); day++) {
    const iso = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const dayProgs = dayMap[iso] || [];
    const dow = new Date(year, month, day).getDay();
    const isWeekend = dow === 0 || dow === 6;

    html += `<div class="cal-day${dayProgs.length ? ' cal-day-has-camps' : ''}${isWeekend ? ' cal-day-weekend' : ''}">`;
    html += `<div class="cal-day-num">${day}</div>`;
    dayProgs.slice(0, 3).forEach(p => {
      const label = p.name.length > 22 ? `${p.name.slice(0, 22)}...` : p.name;
      html += `<button class="cal-camp-badge" data-id="${p.uid}" title="${p.name}">${label}</button>`;
    });
    if (dayProgs.length > 3) html += `<span class="cal-more">+${dayProgs.length - 3} more</span>`;
    html += '</div>';
  }

  html += '</div>';
  grid.innerHTML = html;

  grid.querySelectorAll('.cal-camp-badge').forEach(btn => {
    const uid = btn.dataset.id;
    const prog = allPrograms.find(p => p.uid === uid);
    if (prog) btn.addEventListener('click', () => openModal(prog));
  });

  if (undated.length > 0) {
    undatedNote.textContent = `${undated.length} results do not have specific dates and are not shown on the calendar.`;
    undatedNote.style.display = '';
  } else {
    undatedNote.style.display = 'none';
  }
}

// ===== Map =====
const CITY_COORDS = {
  'Burlington': [44.4759, -73.2121],
  'South Burlington': [44.4667, -73.1710],
  'Winooski': [44.4918, -73.1873],
  'Shelburne': [44.3762, -73.2293],
  'Williston': [44.4270, -73.0618],
  'Essex': [44.4918, -73.1124],
  'Essex Junction': [44.4918, -73.1124],
  'Colchester': [44.5454, -73.1543],
  'Milton': [44.6078, -73.1076],
  'Richmond': [44.4040, -72.9996],
  'Hinesburg': [44.3351, -73.1152],
  'Charlotte': [44.3090, -73.2565],
  'St Albans': [44.8117, -73.0832],
  'St. Albans': [44.8117, -73.0832],
  'Montpelier': [44.2601, -72.5754],
  'Middlebury': [44.0145, -73.1673],
  'Brattleboro': [42.8509, -72.5579],
  'Rutland': [43.6106, -72.9726],
  'St Johnsbury': [44.4196, -72.0162],
  'St. Johnsbury': [44.4196, -72.0162],
  'White River Junction': [43.6493, -72.3193]
};

const VT_BOUNDS = [[42.73, -73.44], [45.02, -71.46]];

function renderMap(programs) {
  if (!mapInstance) {
    mapInstance = L.map('mapContainer', {
      maxBounds: VT_BOUNDS,
      maxBoundsViscosity: 0.8
    });
    mapInstance.fitBounds(VT_BOUNDS);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 18
    }).addTo(mapInstance);
  }

  mapInstance.eachLayer(layer => {
    if (layer instanceof L.CircleMarker) mapInstance.removeLayer(layer);
  });

  const cityGroups = {};
  programs.forEach(p => {
    const city = p.city || '';
    if (!city) return;
    if (!cityGroups[city]) cityGroups[city] = [];
    cityGroups[city].push(p);
  });

  Object.entries(cityGroups).forEach(([city, progs]) => {
    const coords = CITY_COORDS[city];
    if (!coords) return;

    const radius = Math.min(8 + progs.length * 1.6, 30);
    const marker = L.circleMarker(coords, {
      radius,
      color: '#1e5e3a',
      fillColor: '#2a7d4f',
      fillOpacity: 0.75,
      weight: 2
    });

    const list = progs.slice(0, 8).map(p => `<li><a href="#" data-id="${p.uid}" style="color:#2a7d4f;font-weight:600;">${p.name}</a></li>`).join('');
    const more = progs.length > 8 ? `<li style="color:#6c757d;font-size:0.8rem;">+${progs.length - 8} more...</li>` : '';

    marker.bindPopup(`
      <strong style="font-size:0.95rem;">${city}</strong>
      <span style="color:#6c757d;font-size:0.8rem;"> - ${progs.length} result${progs.length !== 1 ? 's' : ''}</span>
      <ul style="margin:0.4rem 0 0;padding-left:1rem;font-size:0.85rem;">${list}${more}</ul>
    `);

    marker.on('popupopen', () => {
      setTimeout(() => {
        document.querySelectorAll('.leaflet-popup a[data-id]').forEach(a => {
          a.addEventListener('click', e => {
            e.preventDefault();
            const uid = a.dataset.id;
            const prog = allPrograms.find(p => p.uid === uid);
            if (prog) {
              mapInstance.closePopup();
              openModal(prog);
            }
          });
        });
      }, 0);
    });

    marker.addTo(mapInstance);
  });

  mapInstance.invalidateSize();
  setTimeout(() => mapInstance.invalidateSize(), 300);
}

// ===== Modal =====
function openModal(p) {
  currentProgram = p;

  const badgeClass = p.category === 'camp' ? 'badge-camp'
    : p.category === 'afterschool' ? 'badge-afterschool'
    : 'badge-both';

  document.getElementById('modalBadge').className = `card-type-badge ${badgeClass}`;
  document.getElementById('modalBadge').textContent = p.type;
  document.getElementById('modalTitle').textContent = p.name;
  document.getElementById('modalOrg').textContent = p.organization || '';
  document.getElementById('modalDescription').textContent = p.description || 'No description available.';

  const gradesText = (p.gradesMin && p.gradesMax)
    ? `Grades ${p.gradesMin}-${p.gradesMax}`
    : (p.ageMin !== null && p.ageMax !== null ? `Ages ${p.ageMin}-${p.ageMax}` : 'Not specified');

  document.getElementById('modalGrades').textContent = gradesText;
  document.getElementById('modalSession').textContent = p.sessionType || 'Not specified';

  const dateEl = document.getElementById('modalDates');
  if (p.startDate) {
    dateEl.textContent = fmtWeekRange(p.startDate, p.endDate);
    dateEl.closest('.modal-detail-item').style.display = '';
  } else {
    dateEl.closest('.modal-detail-item').style.display = 'none';
  }

  document.getElementById('modalHours').textContent = p.hours || 'See provider details';
  document.getElementById('modalDays').textContent = p.daysOffered || 'Varies';
  document.getElementById('modalCost').textContent = p.isFree ? 'Free (Federally Funded)' : (!p.cost || p.cost === 0) ? 'Contact provider' : formatCost(p.cost, p.costPeriod);
  document.getElementById('modalScholarship').textContent = p.scholarshipAvailable ? 'Yes' : 'Not listed';
  document.getElementById('modalTransportation').textContent = p.transportation ? 'Yes' : 'Not listed';
  document.getElementById('modalMeals').textContent = p.mealsProvided ? 'Yes' : 'Not listed';

  const location = [p.address, p.city, p.state, p.zip].filter(Boolean).join(', ');
  document.getElementById('modalLocation').textContent = location || 'Vermont';

  const phoneEl = document.getElementById('modalPhone');
  phoneEl.textContent = p.phone || '-';

  const emailEl = document.getElementById('modalEmail');
  if (p.email) {
    emailEl.textContent = p.email;
    emailEl.href = `mailto:${p.email}`;
  } else {
    emailEl.textContent = '-';
    emailEl.removeAttribute('href');
  }

  document.getElementById('modalRegistration').textContent = p.acceptingRegistration ? 'Open/Active' : 'Closed/Inactive';
  document.getElementById('modalRegistration').style.color = p.acceptingRegistration ? '#065f46' : '#b91c1c';

  const tagsContainer = document.getElementById('modalSubjects');
  tagsContainer.innerHTML = (p.subjects || []).length
    ? p.subjects.map(s => `<span class="tag">${s}</span>`).join('')
    : '<span style="color:var(--gray-600);font-size:0.85rem;">No tags available</span>';

  const websiteLink = document.getElementById('modalWebsiteLink');
  if (p.website) {
    websiteLink.href = p.website;
    websiteLink.style.display = '';
  } else {
    websiteLink.style.display = 'none';
  }

  const emailBtn = document.getElementById('modalEmailBtn');
  if (p.email) {
    emailBtn.href = `mailto:${p.email}`;
    emailBtn.style.display = '';
  } else {
    emailBtn.style.display = 'none';
  }

  const orgSection = document.getElementById('modalOrgPrograms');
  if (p.orgId) {
    const siblings = allPrograms.filter(q => q.orgId === p.orgId && q.uid !== p.uid);
    if (siblings.length > 0) {
      orgSection.style.display = '';
      const org = orgMap.get(p.orgId);
      const orgLabel = org ? asString(org['name']) : (p.orgName || 'this organization');
      orgSection.innerHTML = `
        <h4 class="modal-org-heading">More from ${orgLabel}</h4>
        <ul class="modal-org-list">
          ${siblings.slice(0, 6).map(q => `<li><button class="modal-org-link" data-uid="${q.uid}">${q.name}</button></li>`).join('')}
          ${siblings.length > 6 ? `<li class="modal-org-more">+${siblings.length - 6} more</li>` : ''}
        </ul>`;
      orgSection.querySelectorAll('.modal-org-link').forEach(btn => {
        btn.addEventListener('click', () => {
          const prog = allPrograms.find(q => q.uid === btn.dataset.uid);
          if (prog) openModal(prog);
        });
      });
    } else {
      orgSection.style.display = 'none';
    }
  } else {
    orgSection.style.display = 'none';
  }

  modalOverlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modalOverlay.classList.remove('open');
  document.body.style.overflow = '';
  currentProgram = null;
}

// ===== View Switching =====
function switchView(view) {
  currentView = view;

  document.getElementById('listView').style.display = view === 'list' ? '' : 'none';
  document.getElementById('calendarView').style.display = view === 'calendar' ? '' : 'none';
  document.getElementById('mapView').style.display = view === 'map' ? '' : 'none';

  document.querySelectorAll('.btn-view').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === view);
  });

  if (view === 'list') renderCards(lastFiltered);
  else if (view === 'calendar') renderCalendar(lastFiltered);
  // Double RAF: ensures Leaflet container has real pixel dimensions before rendering
  else requestAnimationFrame(() => requestAnimationFrame(() => renderMap(lastFiltered)));
}

function update() {
  lastFiltered = applyFilters();
  const total = categoryPrograms().length;
  resultsCount.innerHTML = `Showing <strong>${lastFiltered.length}</strong> of <strong>${total}</strong> ${categoryLabel(activeCategory)}`;

  if (currentView === 'list') renderCards(lastFiltered);
  else if (currentView === 'calendar') renderCalendar(lastFiltered);
  // Double RAF: ensures Leaflet container has real pixel dimensions before rendering
  else requestAnimationFrame(() => requestAnimationFrame(() => renderMap(lastFiltered)));
}

function clearAllFilters() {
  activeFilters = {
    search: '',
    type: '',
    grades: '',
    city: '',
    subject: '',
    week: '',
    maxCost: '',
    scholarship: '',
    county: '',
    stars: '',
    status: ''
  };

  searchInput.value = '';
  filterType.value = '';
  filterGrades.value = '';
  filterCity.value = '';
  filterSubject.value = '';
  filterWeek.value = '';
  filterMaxCost.value = '';
  filterScholarship.value = '';
  filterCounty.value = '';
  filterStars.value = '';
  filterStatus.value = '';
}

function setCategory(cat) {
  activeCategory = cat;
  tabButtons.forEach(btn => {
    const active = btn.dataset.category === cat;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });

  clearAllFilters();
  applyCategoryUiText();
  updateFilterVisibility();
  populateFiltersForCategory();
  update();
}

// ===== Event Listeners =====
searchInput.addEventListener('input', e => { activeFilters.search = e.target.value; update(); });
filterType.addEventListener('change', e => { activeFilters.type = e.target.value; update(); });
filterGrades.addEventListener('change', e => { activeFilters.grades = e.target.value; update(); });
filterCity.addEventListener('change', e => { activeFilters.city = e.target.value; update(); });
filterSubject.addEventListener('change', e => { activeFilters.subject = e.target.value; update(); });
filterWeek.addEventListener('change', e => { activeFilters.week = e.target.value; update(); });
filterMaxCost.addEventListener('change', e => { activeFilters.maxCost = e.target.value; update(); });
filterScholarship.addEventListener('change', e => { activeFilters.scholarship = e.target.value; update(); });
filterCounty.addEventListener('change', e => { activeFilters.county = e.target.value; update(); });
filterStars.addEventListener('change', e => { activeFilters.stars = e.target.value; update(); });
filterStatus.addEventListener('change', e => { activeFilters.status = e.target.value; update(); });

btnClearSearch.addEventListener('click', () => {
  searchInput.value = '';
  activeFilters.search = '';
  update();
});

btnReset.addEventListener('click', () => {
  clearAllFilters();
  populateFiltersForCategory();
  update();
});

modalClose.addEventListener('click', closeModal);
document.getElementById('modalCloseBtn').addEventListener('click', closeModal);
modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeModal(); });

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && modalOverlay.classList.contains('open')) closeModal();
});

document.querySelectorAll('.btn-view').forEach(btn => {
  btn.addEventListener('click', () => switchView(btn.dataset.view));
});

document.getElementById('btnCalPrev').addEventListener('click', () => {
  calendarState.month--;
  if (calendarState.month < 0) {
    calendarState.month = 11;
    calendarState.year--;
  }
  renderCalendar(lastFiltered);
});

document.getElementById('btnCalNext').addEventListener('click', () => {
  calendarState.month++;
  if (calendarState.month > 11) {
    calendarState.month = 0;
    calendarState.year++;
  }
  renderCalendar(lastFiltered);
});

tabButtons.forEach(btn => {
  btn.addEventListener('click', () => setCategory(btn.dataset.category));
});

// ===== Boot =====
async function init() {
  // Load org lookup first — provider and subsidized loaders read from orgMap
  await loadOrganizations();
  const campPrograms = normalizeCampPrograms(programsData || []);
  const [providerPrograms, subsidizedPrograms] = await Promise.all([
    loadProviderPrograms(),
    loadSubsidizedPrograms()
  ]);
  allPrograms = [...campPrograms, ...providerPrograms, ...subsidizedPrograms];

  applyCategoryUiText();
  updateFilterVisibility();
  populateFiltersForCategory();
  update();
}

init();
