'use strict';
// Keep error feedback and management navigation usable with a keyboard.
(() => {
  const errors = document.querySelector('[data-error-summary]');
  if (errors) errors.focus();
  const menu = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('#sidebar');
  if (menu && sidebar) {
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && sidebar.contains(document.activeElement)) menu.focus();
    });
    document.addEventListener('click', event => {
      if (!sidebar.contains(event.target) && !menu.contains(event.target)) {
        sidebar.classList.remove('open');
        menu.setAttribute('aria-expanded', 'false');
        menu.setAttribute('aria-label', 'Mở menu');
      }
    });
  }
})();
