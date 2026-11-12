'use strict';
document.addEventListener('click', event => {
  const dismiss = event.target.closest('.dismiss');
  if (dismiss) dismiss.closest('.alert')?.remove();
  if (event.target.closest('[data-print]')) window.print();
});
const menuButton = document.querySelector('.menu-toggle');
if (menuButton) {
  menuButton.addEventListener('click', () => {
    const open = document.querySelector('#sidebar').classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Đóng menu' : 'Mở menu');
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.querySelector('#sidebar').classList.contains('open')) {
      document.querySelector('#sidebar').classList.remove('open');
      menuButton.setAttribute('aria-expanded', 'false');
      menuButton.setAttribute('aria-label', 'Mở menu');
      menuButton.focus();
    }
  });
}
