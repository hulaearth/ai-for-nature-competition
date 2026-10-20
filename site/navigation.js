// Switch views without another private-Space request; fragments preserve browser history.
(() => {
  const views = [...document.querySelectorAll('[data-view]')];
  const links = [...document.querySelectorAll('nav[aria-label="Main navigation"] a')];
  const initial = document.body.dataset.initialPage;
  function showPage() {
    const requested = location.hash.slice(1);
    if (requested === 'main') return; // Keep the keyboard skip link on the current view.
    const active = views.find(view => view.dataset.view === requested)
      || views.find(view => view.dataset.view === initial);
    for (const view of views) view.hidden = view !== active;
    for (const link of links) {
      if (link.getAttribute('href') === '#' + active.dataset.view) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    }
    document.title = active.dataset.title;
  }
  showPage();
  window.addEventListener('hashchange', () => {
    if (location.hash === '#main') return;
    showPage(); window.scrollTo(0, 0);
  });
})();
