// ===== State =====
let activeFilters = {
  search: '',
  type: '',
  grades: '',
  city: '',
  subject: '',
  maxCost: '',
  scholarship: '',
  month: ''
};

let currentProgram = null;

// ===== DOM References =====
const searchInput     = document.getElementById('searchInput');
const filterType      = document.getElementById('filterType');
const filterGrades    = document.getElementById('filterGrades');
const filterCity      = document.getElementById('filterCity');
const filterSubject   = document.getElementById('filterSubject');
const filterMaxCost   = document.getElementById('filterMaxCost');
const filterScholarship = document.getElementById('filterScholarship');
const filterMonth       = document.getElementById('filterMonth');
const cardsGrid       = document.getElementById('cardsGrid');
const resultsCount    = document.getElementById('resultsCount');
const noResults       = document.getElementById('noResults');
const btnReset        = document.getElementById('btnReset');
const btnClearSearch  = document.getElementById('btnClearSearch');
const modalOverlay    = document.getElementById('modalOverlay');
const modalClose      = document.getElementById('modalClose');

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

/** "Jun 22 – 26" or "Jun 29 – Jul 3" */
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
      if (p.cost === 0) {
        // cost=0 means we don't have pricing — don't exclude it
      } else {
        const weekly = normalizeCostToWeekly(p.cost, p.costPeriod);
        if (weekly > max) return false;
      }
    }

    // Scholarship / Financial Aid
    if (activeFilters.scholarship === 'yes' && !p.scholarshipAvailable) return false;

    // Month (matches week start date)
    if (activeFilters.month) {
      if (!p.startDate) return true; // no date info — keep it visible
      const d = parseDate(p.startDate);
      if (d && (d.getMonth() + 1) !== parseInt(activeFilters.month, 10)) return false;
    }

    return true;
  });
}

// ===== Render Cards =====
function renderCards(programs) {
  cardsGrid.innerHTML = '';
  resultsCount.innerHTML = `Showing <strong>${programs.length}</strong> of <strong>${programsData.length}</strong> programs`;

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
  }); // end sorted.forEach
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
  const filtered = applyFilters();
  renderCards(filtered);
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

filterType.addEventListener('change', e => { activeFilters.type = e.target.value; update(); });
filterGrades.addEventListener('change', e => { activeFilters.grades = e.target.value; update(); });
filterCity.addEventListener('change', e => { activeFilters.city = e.target.value; update(); });
filterSubject.addEventListener('change', e => { activeFilters.subject = e.target.value; update(); });
filterMaxCost.addEventListener('change', e => { activeFilters.maxCost = e.target.value; update(); });
filterScholarship.addEventListener('change', e => { activeFilters.scholarship = e.target.value; update(); });
filterMonth.addEventListener('change', e => { activeFilters.month = e.target.value; update(); });

btnReset.addEventListener('click', () => {
  activeFilters = { search: '', type: '', grades: '', city: '', subject: '', maxCost: '', scholarship: '', month: '' };
  searchInput.value = '';
  filterType.value = '';
  filterGrades.value = '';
  filterCity.value = '';
  filterSubject.value = '';
  filterMaxCost.value = '';
  filterScholarship.value = '';
  filterMonth.value = '';
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
update();
