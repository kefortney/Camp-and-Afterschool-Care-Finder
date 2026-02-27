// ===== State =====
let activeFilters = {
  search: '',
  type: '',
  grades: '',
  city: '',
  subject: '',
  maxCost: '',
  scholarship: '',
  session: ''
};

let currentProgram = null;

// ===== DOM References =====
const searchInput = document.getElementById('searchInput');
const filterType = document.getElementById('filterType');
const filterGrades = document.getElementById('filterGrades');
const filterCity = document.getElementById('filterCity');
const filterSubject = document.getElementById('filterSubject');
const filterMaxCost = document.getElementById('filterMaxCost');
const filterScholarship = document.getElementById('filterScholarship');
const filterSession = document.getElementById('filterSession');
const cardsGrid = document.getElementById('cardsGrid');
const resultsCount = document.getElementById('resultsCount');
const noResults = document.getElementById('noResults');
const btnReset = document.getElementById('btnReset');
const btnClearSearch = document.getElementById('btnClearSearch');
const modalOverlay = document.getElementById('modalOverlay');
const modalClose = document.getElementById('modalClose');

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
  return fIdx >= pMin && fIdx <= pMax;
}

// ===== Cost Helpers =====
function normalizeCostToMonthly(cost, period) {
  if (period === 'month') return cost;
  if (period === 'week') return cost * 4;
  // 'session' costs vary widely; compare as-is against the monthly budget filter
  return cost;
}

function formatCost(cost, period) {
  if (cost === 0) return 'FREE';
  return `$${cost.toLocaleString()} / ${period}`;
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
      // Normalize cost to monthly for comparison
      const monthly = normalizeCostToMonthly(p.cost, p.costPeriod);
      if (monthly > max) return false;
    }

    // Scholarship
    if (activeFilters.scholarship === 'yes' && !p.scholarshipAvailable) return false;

    // Session Type
    if (activeFilters.session && p.sessionType !== activeFilters.session) return false;

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

  programs.forEach(p => {
    const card = document.createElement('article');
    card.className = 'program-card';

    const badgeClass = p.type === 'Summer Camp' ? 'badge-camp'
      : p.type === 'Afterschool Care' ? 'badge-afterschool'
      : 'badge-both';

    const costDisplay = p.cost === 0
      ? '<span class="free-badge">★ FREE</span>'
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

    card.innerHTML = `
      <div class="card-header">
        <span class="card-type-badge ${badgeClass}">${p.type}</span>
        <div class="card-title">${p.name}</div>
        <div class="card-org">${p.organization}</div>
      </div>
      <div class="card-body">
        <p class="card-description">${p.description}</p>
        <div class="card-meta">
          <div class="meta-item">
            <span class="meta-icon">📍</span>
            <span class="meta-value">${p.city}, ${p.state}</span>
          </div>
          <div class="meta-item">
            <span class="meta-icon">🎓</span>
            <span class="meta-value">Grades ${p.gradesMin}–${p.gradesMax}</span>
          </div>
          <div class="meta-item">
            <span class="meta-icon">🕐</span>
            <span class="meta-value">${p.hours} (${p.daysOffered})</span>
          </div>
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
        <a href="${p.website}" target="_blank" rel="noopener noreferrer" class="btn-website" title="Visit website">🔗</a>
      </div>
    `;

    card.querySelector('.btn-details').addEventListener('click', () => openModal(p));
    cardsGrid.appendChild(card);
  });
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
  document.getElementById('modalDescription').textContent = p.description;

  document.getElementById('modalGrades').textContent = `Grades ${p.gradesMin}–${p.gradesMax}`;
  document.getElementById('modalSession').textContent = p.sessionType;
  document.getElementById('modalHours').textContent = p.hours;
  document.getElementById('modalDays').textContent = p.daysOffered;
  document.getElementById('modalCost').textContent = formatCost(p.cost, p.costPeriod);
  document.getElementById('modalScholarship').textContent = p.scholarshipAvailable ? 'Yes – financial aid available' : 'No';
  document.getElementById('modalTransportation').textContent = p.transportation ? 'Yes' : 'No';
  document.getElementById('modalMeals').textContent = p.mealsProvided ? 'Yes' : 'No';
  document.getElementById('modalLocation').textContent = `${p.address}, ${p.city}, ${p.state} ${p.zip}`;
  document.getElementById('modalPhone').textContent = p.phone;
  document.getElementById('modalEmail').textContent = p.email;
  document.getElementById('modalEmail').href = `mailto:${p.email}`;
  document.getElementById('modalRegistration').textContent = p.acceptingRegistration ? 'Open' : 'Closed';
  document.getElementById('modalRegistration').style.color = p.acceptingRegistration ? '#065f46' : '#b91c1c';

  const tagsContainer = document.getElementById('modalSubjects');
  tagsContainer.innerHTML = p.subjects.map(s => `<span class="tag">${s}</span>`).join('');

  document.getElementById('modalWebsiteLink').href = p.website;
  document.getElementById('modalEmailBtn').href = `mailto:${p.email}`;

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
filterSession.addEventListener('change', e => { activeFilters.session = e.target.value; update(); });

btnReset.addEventListener('click', () => {
  activeFilters = { search: '', type: '', grades: '', city: '', subject: '', maxCost: '', scholarship: '', session: '' };
  searchInput.value = '';
  filterType.value = '';
  filterGrades.value = '';
  filterCity.value = '';
  filterSubject.value = '';
  filterMaxCost.value = '';
  filterScholarship.value = '';
  filterSession.value = '';
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

// ===== Init =====
update();
