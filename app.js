// ===== State =====
let activeFilters = {
  search: '',
  type: '',
  grades: '',
  city: '',
  subject: '',
  maxCost: '',
  scholarship: '',
  week: ''
};

let currentView = 'list'; // 'list' | 'calendar' | 'map'
let mapInstance = null;
let calendarState = { year: 2026, month: 5 }; // month is 0-indexed (5 = June)
let lastFiltered = [];
let currentProgram = null;

// ===== DOM References =====
const searchInput       = document.getElementById('searchInput');
const filterType        = document.getElementById('filterType');
const filterGrades      = document.getElementById('filterGrades');
const filterCity        = document.getElementById('filterCity');
const filterSubject     = document.getElementById('filterSubject');
const filterMaxCost     = document.getElementById('filterMaxCost');
const filterScholarship = document.getElementById('filterScholarship');
const filterWeek        = document.getElementById('filterWeek');
const cardsGrid         = document.getElementById('cardsGrid');
const resultsCount      = document.getElementById('resultsCount');
const noResults         = document.getElementById('noResults');
const btnReset          = document.getElementById('btnReset');
const btnClearSearch    = document.getElementById('btnClearSearch');
const modalOverlay      = document.getElementById('modalOverlay');
const modalClose        = document.getElementById('modalClose');

// ===== Grade Range Helpers =====
const gradeOrder = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];

function gradeToIndex(g) {
  return gradeOrder.indexOf(String(g));
}

function gradesOverlap(progMin, progMax, filterGrade) {
  if (!filterGrade) return true;
  const pMin = gradeToIndex(progMin);
  const pMax = gradeToIndex(progMax);
  const fIdx = gradeToIndex(filterGrade);
  if (pMin < 0 || pMax < 0) return true; // unknown grade range — don't exclude
  return fIdx >= pMin && fIdx <= pMax;
}

// ===== Cost Helpers =====
function normalizeCostToWeekly(cost, period) {
  if (period === 'week')  return cost;
  if (period === 'month') return cost / 4;
  if (period === 'day')   return cost * 5;
  return cost; // session — compare as-is
}

function formatCost(cost, period) {
  if (!cost || cost === 0) return 'Contact for pricing';
  return `$${cost.toLocaleString()} / ${period}`;
}

// ===== Date Helpers =====
const MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const MONTH_FULL = ['January','February','March','April','May','June','July','August','September','October','November','December'];

function parseDate(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d); // local time, no UTC shift
}

/** "Jun 22" */
function fmtShort(iso) {
  const d = parseDate(iso);
  if (!d) return '';
  return `${MONTH_ABBR[d.getMonth()]} ${d.getDate()}`;
}

/** "Jun 22–26" or "Jun 29 – Jul 3" */
function fmtWeekRange(startIso, endIso) {
  const s = parseDate(startIso);
  if (!s) return '';
  const label = `${MONTH_ABBR[s.getMonth()]} ${s.getDate()}`;
  const e = parseDate(endIso);
  if (!e) return `Week of ${label}`;
  if (s.getMonth() === e.getMonth()) {
    return `${label}–${e.getDate()}`;
  }
  return `${label} – ${MONTH_ABBR[e.getMonth()]} ${e.getDate()}`;
}

// ===== Week Helpers =====
function getMondayOfWeek(d) {
  const result = new Date(d);
  const day = result.getDay(); // 0=Sun, 1=Mon, ...
  const diff = (day === 0) ? -6 : 1 - day;
  result.setDate(result.getDate() + diff);
  return result;
}

function toIso(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function getFridayOfWeek(monday) {
  const d = new Date(monday);
  d.setDate(d.getDate() + 4);
  return d;
}

function fmtWeekOption(mondayIso) {
  const mon = parseDate(mondayIso);
  const fri = getFridayOfWeek(mon);
  const monLabel = `${MONTH_ABBR[mon.getMonth()]} ${mon.getDate()}`;
  if (mon.getMonth() === fri.getMonth()) {
    return `${monLabel}–${fri.getDate()}, ${fri.getFullYear()}`;
  }
  return `${monLabel} – ${MONTH_ABBR[fri.getMonth()]} ${fri.getDate()}, ${fri.getFullYear()}`;
}

function populateWeekDropdown() {
  const mondaySet = new Set();
  programsData.forEach(p => {
    if (p.startDate) {
      const mon = getMondayOfWeek(parseDate(p.startDate));
      mondaySet.add(toIso(mon));
    }
  });
  const sortedMondays = [...mondaySet].sort();
  sortedMondays.forEach(mondayIso => {
    const opt = document.createElement('option');
    opt.value = mondayIso;
    opt.textContent = fmtWeekOption(mondayIso);
    filterWeek.appendChild(opt);
  });
}

// ===== Filtering =====
function applyFilters() {
  const search = activeFilters.search.toLowerCase().trim();

  return programsData.filter(p => {
    // Search
    if (search) {
      const haystack = [
        p.name, p.organization, p.city, p.description, ...p.subjects
      ].join(' ').toLowerCase();
      if (!haystack.includes(search)) return false;
    }

    // Type
    if (activeFilters.type && p.type !== activeFilters.type) return false;

    // Grades
    if (activeFilters.grades && !gradesOverlap(p.gradesMin, p.gradesMax, activeFilters.grades)) return false;

    // City
    if (activeFilters.city && p.city !== activeFilters.city) return false;

    // Subject
    if (activeFilters.subject && !p.subjects.includes(activeFilters.subject)) return false;

    // Max Cost
    if (activeFilters.maxCost !== '') {
      const max = parseInt(activeFilters.maxCost, 10);
      if (p.cost !== 0) {
        const weekly = normalizeCostToWeekly(p.cost, p.costPeriod);
        if (weekly > max) return false;
      }
    }

    // Scholarship / Financial Aid
    if (activeFilters.scholarship === 'yes' && !p.scholarshipAvailable) return false;

    // Week filter (match camp's Monday to selected Monday ISO)
    if (activeFilters.week) {
      if (!p.startDate) return true; // no date info — keep visible
      const campMonday = toIso(getMondayOfWeek(parseDate(p.startDate)));
      if (campMonday !== activeFilters.week) return false;
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

  // Sort: dated entries first (ascending by start date), undated last
  const sorted = [...programs].sort((a, b) => {
    if (a.startDate && b.startDate) return a.startDate.localeCompare(b.startDate);
    if (a.startDate) return -1;
    if (b.startDate) return 1;
    return 0;
  });

  sorted.forEach(p => {
    const card = document.createElement('article');
    card.className = 'program-card';

    const badgeClass = p.type === 'Summer Camp' ? 'badge-camp'
      : p.type === 'Afterschool Care' ? 'badge-afterschool'
      : 'badge-both';

    const costDisplay = (!p.cost || p.cost === 0)
      ? '<span class="free-badge">Contact for pricing</span>'
      : `<span>${formatCost(p.cost, p.costPeriod)}</span>`;

    const scholarshipHtml = p.scholarshipAvailable
      ? '<span class="scholarship-badge">✓ Aid Available</span>'
      : '';

    const registrationHtml = !p.acceptingRegistration
      ? '<span class="registration-closed">Closed</span>'
      : '';

    const subjectTags = p.subjects.slice(0, 3).map(s =>
      `<span class="tag">${s}</span>`
    ).join('');

    const locationText = [p.city, p.state].filter(Boolean).join(', ') || 'Vermont';
    const gradesText = (p.gradesMin && p.gradesMax)
      ? `Grades ${p.gradesMin}–${p.gradesMax}`
      : (p.ageMin && p.ageMax ? `Ages ${p.ageMin}–${p.ageMax}` : '');
    const hoursText = p.hours || '';

    const websiteHtml = p.website
      ? `<a href="${p.website}" target="_blank" rel="noopener noreferrer" class="btn-website" title="Visit website">🔗</a>`
      : '';

    const weekBadgeHtml = p.startDate
      ? `<span class="week-badge">📅 ${fmtWeekRange(p.startDate, p.endDate)}</span>`
      : '';

    card.innerHTML = `
      <div class="card-header">
        <div class="card-header-top">
          <span class="card-type-badge ${badgeClass}">${p.type}</span>
          ${weekBadgeHtml}
        </div>
        <div class="card-title">${p.name}</div>
        <div class="card-org">${p.organization}</div>
      </div>
      <div class="card-body">
        <p class="card-description">${p.description || ''}</p>
        <div class="card-meta">
          <div class="meta-item">
            <span class="meta-icon">📍</span>
            <span class="meta-value">${locationText}</span>
          </div>
          ${gradesText ? `
          <div class="meta-item">
            <span class="meta-icon">🎓</span>
            <span class="meta-value">${gradesText}</span>
          </div>` : ''}
          ${hoursText ? `
          <div class="meta-item">
            <span class="meta-icon">🕐</span>
            <span class="meta-value">${hoursText}</span>
          </div>` : ''}
          <div class="meta-item">
            <span class="meta-icon">💰</span>
            <span class="meta-value">${costDisplay} ${scholarshipHtml}</span>
          </div>
        </div>
        <div class="tags">${subjectTags}</div>
      </div>
      <div class="card-footer">
        <button class="btn-details" data-id="${p.id}">View Details</button>
        ${registrationHtml}
        ${websiteHtml}
      </div>
    `;

    card.querySelector('.btn-details').addEventListener('click', () => openModal(p));
    cardsGrid.appendChild(card);
  });
}

// ===== Calendar View =====
function renderCalendar(programs) {
  const { year, month } = calendarState;
  const monthLabel = document.getElementById('calMonthLabel');
  const grid = document.getElementById('calendarGrid');
  const undatedNote = document.getElementById('calUndatedNote');

  monthLabel.textContent = `${MONTH_FULL[month]} ${year}`;

  // Build a map of ISO date → [programs], spanning all days start→end
  const dayMap = {};
  const undated = [];
  programs.forEach(p => {
    if (p.startDate) {
      const start = parseDate(p.startDate);
      const end = p.endDate ? parseDate(p.endDate) : start;
      const cur = new Date(start);
      while (cur <= end) {
        const iso = toIso(cur);
        if (!dayMap[iso]) dayMap[iso] = [];
        dayMap[iso].push(p);
        cur.setDate(cur.getDate() + 1);
      }
    } else {
      undated.push(p);
    }
  });

  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startDow = firstDay.getDay(); // 0=Sun

  const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  let html = '<div class="cal-header-row">' + DOW.map(d => `<div class="cal-dow">${d}</div>`).join('') + '</div>';
  html += '<div class="cal-body">';

  // Empty cells before the 1st
  for (let i = 0; i < startDow; i++) {
    html += '<div class="cal-day cal-day-empty"></div>';
  }

  // Day cells
  for (let day = 1; day <= lastDay.getDate(); day++) {
    const iso = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const dayProgs = dayMap[iso] || [];
    const dow = new Date(year, month, day).getDay();
    const isWeekend = dow === 0 || dow === 6;

    html += `<div class="cal-day${dayProgs.length ? ' cal-day-has-camps' : ''}${isWeekend ? ' cal-day-weekend' : ''}">`;
    html += `<div class="cal-day-num">${day}</div>`;
    dayProgs.slice(0, 3).forEach(p => {
      html += `<button class="cal-camp-badge" data-id="${p.id}" title="${p.name}">${p.name.length > 22 ? p.name.slice(0, 22) + '…' : p.name}</button>`;
    });
    if (dayProgs.length > 3) {
      html += `<span class="cal-more">+${dayProgs.length - 3} more</span>`;
    }
    html += '</div>';
  }

  html += '</div>'; // cal-body
  grid.innerHTML = html;

  // Attach click handlers
  grid.querySelectorAll('.cal-camp-badge').forEach(btn => {
    const id = parseInt(btn.dataset.id);
    const prog = programsData.find(p => p.id === id);
    if (prog) btn.addEventListener('click', () => openModal(prog));
  });

  if (undated.length > 0) {
    undatedNote.textContent = `${undated.length} program${undated.length !== 1 ? 's' : ''} without specific dates are not shown on the calendar. Use List view to see all programs.`;
    undatedNote.style.display = '';
  } else {
    undatedNote.style.display = 'none';
  }
}

// ===== Map View =====
const CITY_COORDS = {
  'Burlington':       [44.4759, -73.2121],
  'South Burlington': [44.4667, -73.1710],
  'Winooski':         [44.4918, -73.1873],
  'Shelburne':        [44.3762, -73.2293],
  'Williston':        [44.4270, -73.0618],
  'Essex':            [44.4918, -73.1124],
  'Essex Junction':   [44.4918, -73.1124],
  'Colchester':       [44.5454, -73.1543],
  'Milton':           [44.6078, -73.1076],
  'Richmond':         [44.4040, -72.9996],
  'Hinesburg':        [44.3351, -73.1152],
  'Charlotte':        [44.3090, -73.2565],
  'Jericho':          [44.4952, -72.9934],
  'Huntington':       [44.3298, -72.9818],
  'Stowe':            [44.4654, -72.6870],
  'Waterbury':        [44.3371, -72.7560],
  'Montpelier':       [44.2601, -72.5754],
  'Barre':            [44.2170, -72.5024],
  'Bristol':          [44.1348, -73.0751],
  'Middlebury':       [44.0145, -73.1673],
  'Vergennes':        [44.1684, -73.2543],
  'St. Albans':       [44.8117, -73.0832],
  'St Albans':        [44.8117, -73.0832],
  'St. Johnsbury':    [44.4196, -72.0162],
  'Morrisville':      [44.5601, -72.5984],
  'Hyde Park':        [44.5937, -72.6100],
  'Johnson':          [44.6340, -72.6784],
  'Lamoille Valley':  [44.5601, -72.5984],
  'Jay':              [44.9307, -72.5145],
  'Fairlee':          [43.9065, -72.1351],
  'Greensboro':       [44.5912, -72.2885],
  'Roxbury':          [44.0843, -72.7257],
  'Plymouth':         [43.5382, -72.7273],
  'Bolton':           [44.3966, -72.8666],
  'Underhill':        [44.5318, -72.8862],
  'South Hero':       [44.6344, -73.3098],
  'Williamstown':     [44.1076, -72.5393],
  'Cabot':            [44.4040, -72.3162],
  'Craftsbury':       [44.6554, -72.3729],
  'Peacham':          [44.3287, -72.1762],
  'Barton':           [44.7490, -72.1742],
  'Newport':          [44.9365, -72.2064],
  'Lyndonville':      [44.5340, -72.0126],
  'Bradford':         [44.0051, -72.1326],
  'Thetford':         [43.9387, -72.2304],
  'Norwich':          [43.7193, -72.3248],
  'Woodstock':        [43.6237, -72.5215],
  'Quechee':          [43.6540, -72.4215],
  'White River Junction': [43.6493, -72.3193],
  'Randolph':         [43.9248, -72.6632],
  'Barre City':       [44.1970, -72.5024],
};

// Vermont bounding box  SW corner → NE corner
const VT_BOUNDS = [[42.73, -73.44], [45.02, -71.46]];

function renderMap(programs) {
  if (!mapInstance) {
    mapInstance = L.map('mapContainer', {
      maxBounds: VT_BOUNDS,
      maxBoundsViscosity: 0.8,
    });
    mapInstance.fitBounds(VT_BOUNDS);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
    }).addTo(mapInstance);
  }

  // Remove existing circle markers
  mapInstance.eachLayer(layer => {
    if (layer instanceof L.CircleMarker) {
      mapInstance.removeLayer(layer);
    }
  });

  // Group programs by city
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

    const radius = Math.min(8 + progs.length * 2, 30);
    const marker = L.circleMarker(coords, {
      radius,
      color: '#1e5e3a',
      fillColor: '#2a7d4f',
      fillOpacity: 0.75,
      weight: 2,
    });

    const campList = progs.slice(0, 8).map(p =>
      `<li><a href="#" data-id="${p.id}" style="color:#2a7d4f;font-weight:600;">${p.name}</a></li>`
    ).join('');
    const more = progs.length > 8
      ? `<li style="color:#6c757d;font-size:0.8rem;">+${progs.length - 8} more…</li>`
      : '';

    marker.bindPopup(`
      <strong style="font-size:0.95rem;">${city}</strong>
      <span style="color:#6c757d;font-size:0.8rem;"> – ${progs.length} program${progs.length !== 1 ? 's' : ''}</span>
      <ul style="margin:0.4rem 0 0;padding-left:1rem;font-size:0.85rem;">${campList}${more}</ul>
    `);

    marker.on('popupopen', () => {
      setTimeout(() => {
        document.querySelectorAll('.leaflet-popup a[data-id]').forEach(a => {
          a.addEventListener('click', e => {
            e.preventDefault();
            const id = parseInt(a.dataset.id);
            const prog = programsData.find(p => p.id === id);
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

  // Ensure tiles render correctly after container becomes visible
  mapInstance.invalidateSize();
  setTimeout(() => mapInstance.invalidateSize(), 300);
}

// ===== View Switching =====
function switchView(view) {
  currentView = view;

  document.getElementById('listView').style.display     = view === 'list'     ? '' : 'none';
  document.getElementById('calendarView').style.display = view === 'calendar' ? '' : 'none';
  document.getElementById('mapView').style.display      = view === 'map'      ? '' : 'none';

  document.querySelectorAll('.btn-view').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === view);
  });

  if (view === 'list')          renderCards(lastFiltered);
  else if (view === 'calendar') renderCalendar(lastFiltered);
  else if (view === 'map') {
    // Double rAF: first frame commits layout, second fires after paint
    requestAnimationFrame(() => requestAnimationFrame(() => renderMap(lastFiltered)));
  }
}

// ===== Modal =====
function openModal(p) {
  currentProgram = p;

  const badgeClass = p.type === 'Summer Camp' ? 'badge-camp'
    : p.type === 'Afterschool Care' ? 'badge-afterschool'
    : 'badge-both';

  document.getElementById('modalBadge').className = `card-type-badge ${badgeClass}`;
  document.getElementById('modalBadge').textContent = p.type;
  document.getElementById('modalTitle').textContent = p.name;
  document.getElementById('modalOrg').textContent = p.organization;
  document.getElementById('modalDescription').textContent = p.description || 'No description available.';

  const gradesText = (p.gradesMin && p.gradesMax)
    ? `Grades ${p.gradesMin}–${p.gradesMax}`
    : (p.ageMin && p.ageMax ? `Ages ${p.ageMin}–${p.ageMax}` : 'Not specified');

  document.getElementById('modalGrades').textContent = gradesText;
  document.getElementById('modalSession').textContent = p.sessionType || 'Summer';

  const dateEl = document.getElementById('modalDates');
  if (dateEl) {
    if (p.startDate) {
      dateEl.textContent = fmtWeekRange(p.startDate, p.endDate);
      dateEl.closest('.modal-detail-item').style.display = '';
    } else {
      dateEl.closest('.modal-detail-item').style.display = 'none';
    }
  }

  document.getElementById('modalHours').textContent = p.hours || 'See website for hours';
  document.getElementById('modalDays').textContent = p.daysOffered || '';
  document.getElementById('modalCost').textContent = (!p.cost || p.cost === 0)
    ? 'See website for pricing'
    : formatCost(p.cost, p.costPeriod);
  document.getElementById('modalScholarship').textContent = p.scholarshipAvailable ? 'Yes – financial aid available' : 'No';
  document.getElementById('modalTransportation').textContent = p.transportation ? 'Yes' : 'No';
  document.getElementById('modalMeals').textContent = p.mealsProvided ? 'Yes' : 'No';

  const addressParts = [p.address, p.city, p.state, p.zip].filter(Boolean);
  document.getElementById('modalLocation').textContent = addressParts.join(', ') || 'Vermont';

  const phoneEl = document.getElementById('modalPhone');
  phoneEl.textContent = p.phone || '—';

  const emailEl = document.getElementById('modalEmail');
  if (p.email) {
    emailEl.textContent = p.email;
    emailEl.href = `mailto:${p.email}`;
  } else {
    emailEl.textContent = '—';
    emailEl.removeAttribute('href');
  }

  document.getElementById('modalRegistration').textContent = p.acceptingRegistration ? 'Open' : 'Closed';
  document.getElementById('modalRegistration').style.color = p.acceptingRegistration ? '#065f46' : '#b91c1c';

  const tagsContainer = document.getElementById('modalSubjects');
  tagsContainer.innerHTML = p.subjects.length
    ? p.subjects.map(s => `<span class="tag">${s}</span>`).join('')
    : '<span style="color:var(--gray-600);font-size:0.85rem;">See website for program details</span>';

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

  modalOverlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modalOverlay.classList.remove('open');
  document.body.style.overflow = '';
  currentProgram = null;
}

// ===== Event Listeners =====
function update() {
  lastFiltered = applyFilters();
  resultsCount.innerHTML = `Showing <strong>${lastFiltered.length}</strong> of <strong>${programsData.length}</strong> programs`;

  if (currentView === 'list')          renderCards(lastFiltered);
  else if (currentView === 'calendar') renderCalendar(lastFiltered);
  else if (currentView === 'map')      requestAnimationFrame(() => requestAnimationFrame(() => renderMap(lastFiltered)));
}

searchInput.addEventListener('input', e => {
  activeFilters.search = e.target.value;
  update();
});

btnClearSearch.addEventListener('click', () => {
  searchInput.value = '';
  activeFilters.search = '';
  update();
});

filterType.addEventListener('change',       e => { activeFilters.type       = e.target.value; update(); });
filterGrades.addEventListener('change',     e => { activeFilters.grades     = e.target.value; update(); });
filterCity.addEventListener('change',       e => { activeFilters.city       = e.target.value; update(); });
filterSubject.addEventListener('change',    e => { activeFilters.subject    = e.target.value; update(); });
filterMaxCost.addEventListener('change',    e => { activeFilters.maxCost    = e.target.value; update(); });
filterScholarship.addEventListener('change',e => { activeFilters.scholarship= e.target.value; update(); });
filterWeek.addEventListener('change',       e => { activeFilters.week       = e.target.value; update(); });

btnReset.addEventListener('click', () => {
  activeFilters = { search: '', type: '', grades: '', city: '', subject: '', maxCost: '', scholarship: '', week: '' };
  searchInput.value     = '';
  filterType.value      = '';
  filterGrades.value    = '';
  filterCity.value      = '';
  filterSubject.value   = '';
  filterMaxCost.value   = '';
  filterScholarship.value = '';
  filterWeek.value      = '';
  update();
});

modalClose.addEventListener('click', closeModal);
document.getElementById('modalCloseBtn').addEventListener('click', closeModal);
modalOverlay.addEventListener('click', e => {
  if (e.target === modalOverlay) closeModal();
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && modalOverlay.classList.contains('open')) closeModal();
});

// ===== View Toggle Buttons =====
document.querySelectorAll('.btn-view').forEach(btn => {
  btn.addEventListener('click', () => switchView(btn.dataset.view));
});

// ===== Calendar Navigation =====
document.getElementById('btnCalPrev').addEventListener('click', () => {
  calendarState.month--;
  if (calendarState.month < 0) { calendarState.month = 11; calendarState.year--; }
  renderCalendar(lastFiltered);
});

document.getElementById('btnCalNext').addEventListener('click', () => {
  calendarState.month++;
  if (calendarState.month > 11) { calendarState.month = 0; calendarState.year++; }
  renderCalendar(lastFiltered);
});

// ===== Populate dynamic dropdowns =====
function populateCityDropdown() {
  const cities = [...new Set(
    programsData.map(p => p.city).filter(c => c)
  )].sort();

  cities.forEach(city => {
    const opt = document.createElement('option');
    opt.value = city;
    opt.textContent = city;
    filterCity.appendChild(opt);
  });
}

function populateSubjectDropdown() {
  const subjects = [...new Set(
    programsData.flatMap(p => p.subjects)
  )].sort();

  subjects.forEach(subj => {
    const opt = document.createElement('option');
    opt.value = subj;
    opt.textContent = subj;
    filterSubject.appendChild(opt);
  });
}

// ===== Init =====
populateCityDropdown();
populateSubjectDropdown();
populateWeekDropdown();
update();
