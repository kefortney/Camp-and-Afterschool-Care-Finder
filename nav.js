(function () {
  const NAV_ITEMS = [
    { label: 'Camps',       href: 'index.html',       key: 'camps' },
    { label: 'Afterschool', href: 'afterschool.html',  key: 'afterschool' },
    { label: 'About',       href: 'about.html',        key: 'about' },
    { label: 'Data',        href: 'data.html',         key: 'data' },
    { label: 'Hackathon',   href: 'hackathon.html',    key: 'hackathon' },
    { label: 'Admin',       href: 'admin.html',        key: 'admin' },
  ];

  function renderNav() {
    const activeKey = window.NAV_PAGE || '';

    const nav = document.createElement('nav');
    nav.className = 'top-nav';
    nav.setAttribute('aria-label', 'Site navigation');

    const brand = document.createElement('a');
    brand.href = 'index.html';
    brand.className = 'top-nav-brand';
    brand.innerHTML = '<span class="top-nav-icon" aria-hidden="true">🏕️</span> Camp &amp; Afterschool Finder';

    const hamburger = document.createElement('button');
    hamburger.className = 'top-nav-hamburger';
    hamburger.setAttribute('aria-label', 'Toggle navigation');
    hamburger.setAttribute('aria-expanded', 'false');
    hamburger.innerHTML = '<span></span><span></span><span></span>';

    const ul = document.createElement('ul');
    ul.className = 'top-nav-links';
    ul.setAttribute('role', 'list');

    NAV_ITEMS.forEach(item => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = item.href;
      a.textContent = item.label;
      if (item.key === activeKey) {
        a.className = 'active';
        a.setAttribute('aria-current', 'page');
      }
      li.appendChild(a);
      ul.appendChild(li);
    });

    hamburger.addEventListener('click', function () {
      const open = ul.classList.toggle('open');
      hamburger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    nav.appendChild(brand);
    nav.appendChild(hamburger);
    nav.appendChild(ul);
    document.body.prepend(nav);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderNav);
  } else {
    renderNav();
  }
})();
