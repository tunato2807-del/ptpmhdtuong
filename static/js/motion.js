'use strict';
(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  // Stagger existing scroll reveals; keep the original observer and no-JS fallback.
  if (!reduced.matches) {
    document.querySelectorAll('.gh-service[data-reveal], .gh-branch[data-reveal], .how-grid [data-reveal]')
      .forEach((item, index) => { item.style.transitionDelay = `${(index % 3) * 70}ms`; });
  }
  document.querySelectorAll('[data-slideshow]').forEach(root => {
    const slides = [...root.querySelectorAll('.hero-slide')];
    const controls = root.querySelector('.slideshow-controls');
    const toggle = root.querySelector('[data-slide-toggle]');
    const count = root.querySelector('.slideshow-count');
    if (slides.length < 2 || !controls || !toggle || !count) return;
    let index = 0;
    let timer = null;
    let paused = false;
    let hovered = false;
    let focused = false;
    let visible = true;
    const stop = () => {
      window.clearTimeout(timer);
      timer = null;
      root.classList.remove('is-playing');
    };
    const show = step => {
      // Skip images that failed or have not loaded; never replace a good image with a blank one.
      let next = index;
      for (let attempt = 1; attempt < slides.length; attempt++) {
        const candidate = (index + step * attempt + slides.length * attempt) % slides.length;
        if (slides[candidate].complete && slides[candidate].naturalWidth > 0) { next = candidate; break; }
      }
      if (next === index) return;
      index = next;
      slides.forEach((slide, i) => {
        slide.classList.toggle('is-active', i === index);
        slide.setAttribute('aria-hidden', String(i !== index));
      });
      count.textContent = `${String(index + 1).padStart(2, '0')} / ${String(slides.length).padStart(2, '0')}`;
    };
    const sync = () => {
      stop();
      toggle.disabled = reduced.matches;
      toggle.textContent = reduced.matches ? 'Chuyển ảnh thủ công' : paused ? 'Bật tự chuyển' : 'Dừng tự chuyển';
      if (paused || reduced.matches || hovered || focused || !visible || document.hidden) return;
      root.classList.add('is-playing');
      timer = window.setTimeout(() => { show(1); sync(); }, 5500);
    };
    controls.hidden = false;
    root.querySelectorAll('[data-slide-step]').forEach(button => {
      button.addEventListener('click', () => {
        paused = true;
        show(Number(button.dataset.slideStep));
        sync();
      });
    });
    toggle.addEventListener('click', () => {
      paused = !paused;
      // Explicit play takes precedence over focus/hover on the play button itself.
      if (!paused) { focused = false; hovered = false; }
      sync();
    });
    root.addEventListener('pointerenter', event => { if (event.pointerType === 'mouse') { hovered = true; sync(); } });
    root.addEventListener('pointerleave', () => { hovered = false; sync(); });
    root.addEventListener('focusin', () => { focused = true; sync(); });
    root.addEventListener('focusout', event => {
      if (!root.contains(event.relatedTarget)) { focused = false; sync(); }
    });
    document.addEventListener('visibilitychange', sync);
    reduced.addEventListener('change', sync);
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(entries => {
        visible = entries[0].isIntersecting;
        sync();
      }, { threshold: 0 }).observe(root);
    }
    sync();
  });
})();
