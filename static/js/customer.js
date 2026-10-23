'use strict';
// Progressive enhancement: content and links remain available without JavaScript.
(() => {
  if (!document.body.classList.contains('customer-app')) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const header = document.querySelector('.public-header');
  const menu = document.querySelector('.customer-menu');
  const nav = document.querySelector('#customer-nav');
  if (header && menu && nav) {
    header.classList.add('nav-ready');
    const closeMenu = (restoreFocus = false) => {
      nav.classList.remove('is-open');
      menu.setAttribute('aria-expanded', 'false');
      menu.setAttribute('aria-label', 'Mở điều hướng');
      if (restoreFocus) menu.focus();
    };
    menu.addEventListener('click', () => {
      const open = menu.getAttribute('aria-expanded') !== 'true';
      nav.classList.toggle('is-open', open);
      menu.setAttribute('aria-expanded', String(open));
      menu.setAttribute('aria-label', open ? 'Đóng điều hướng' : 'Mở điều hướng');
    });
    nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => closeMenu()));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') closeMenu(true);
    });
    document.addEventListener('click', event => { if (!header.contains(event.target)) closeMenu(); });
    window.matchMedia('(min-width: 981px)').addEventListener('change', () => closeMenu());
    const updateHeader = () => header.classList.toggle('is-scrolled', window.scrollY > 15);
    window.addEventListener('scroll', updateHeader, {passive: true});
    updateHeader();
  }

  const revealItems = document.querySelectorAll('[data-reveal]');
  if ('IntersectionObserver' in window && !reducedMotion.matches) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, {threshold: 0.05, rootMargin: '0px 0px 35px 0px'});
    revealItems.forEach(item => {
      // Leave content already in view visible; animate upcoming sections once.
      if (item.getBoundingClientRect().top < window.innerHeight) return;
      item.classList.add('reveal-ready');
      observer.observe(item);
    });
    reducedMotion.addEventListener('change', event => {
      if (event.matches) {
        observer.disconnect();
        revealItems.forEach(item => item.classList.add('is-visible'));
      }
    });
  }

  const filterBar = document.querySelector('.service-filters');
  if (filterBar) {
    filterBar.hidden = false;
    const services = [...document.querySelectorAll('.gh-service')];
    filterBar.querySelectorAll('button').forEach(button => {
      button.addEventListener('click', () => {
        const kind = button.dataset.serviceFilter;
        filterBar.querySelectorAll('button').forEach(item => {
          const active = item === button;
          item.classList.toggle('is-active', active);
          item.setAttribute('aria-pressed', String(active));
        });
        let visible = 0;
        services.forEach(card => {
          card.hidden = kind !== 'all' && card.dataset.kind !== kind;
          if (!card.hidden) { visible++; card.classList.add('is-visible'); }
        });
        document.querySelector('#filter-status').textContent = visible + ' dịch vụ: ' + button.textContent;
      });
    });
  }

  const gallery = document.querySelector('#style-gallery');
  if (gallery) {
    const buttons = [...document.querySelectorAll('[data-gallery-direction]')];
    const progress = document.querySelector('.gallery-progress > span');
    document.querySelector('.gallery-controls').hidden = false;
    const move = direction => gallery.scrollBy({
      left: direction * (gallery.querySelector('.style-card').getBoundingClientRect().width + parseFloat(getComputedStyle(gallery).gap)),
      behavior: reducedMotion.matches ? 'instant' : 'smooth',
    });
    buttons.forEach(button => button.addEventListener('click', () => move(Number(button.dataset.galleryDirection))));
    gallery.addEventListener('keydown', event => {
      if (event.target !== gallery || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault(); move(event.key === 'ArrowRight' ? 1 : -1);
    });
    const updateGallery = () => {
      const maximum = gallery.scrollWidth - gallery.clientWidth;
      buttons.forEach(button => {
        button.disabled = Number(button.dataset.galleryDirection) < 0 ? gallery.scrollLeft <= 2 : gallery.scrollLeft >= maximum - 2;
      });
      if (progress) progress.style.width = maximum > 0 ? (gallery.clientWidth + gallery.scrollLeft) / gallery.scrollWidth * 100 + '%' : '100%';
    };
    gallery.addEventListener('scroll', updateGallery, {passive: true});
    window.addEventListener('resize', updateGallery);
    updateGallery();
  }
})();
