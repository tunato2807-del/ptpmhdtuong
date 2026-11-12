'use strict';
// Proxies submit through the real form, preserving validation, submitter and CSRF.
window.GentlemanDialogActions = (body, footer) => {
  const target = footer.querySelector('[data-quick-submit]');
  let current, observer, busy = false;
  function clear() {
    observer?.disconnect(); current = null;
    target.replaceChildren(); footer.hidden = true;
  }
  function choose(form) {
    if (current === form) return;
    clear();
    body.querySelectorAll('[data-quick-proxied]').forEach(button => button.removeAttribute('data-quick-proxied'));
    if (!form) return;
    const buttons = [...form.querySelectorAll('button:not([type]), button[type="submit"], input[type="submit"]')];
    if (!buttons.length) return;
    current = form; footer.hidden = false;
    const pairs = buttons.map(original => {
      const proxy = document.createElement('button');
      proxy.type = 'button'; proxy.className = original.className || 'btn btn-primary';
      proxy.addEventListener('click', () => { if (!busy && !original.disabled) HTMLFormElement.prototype.requestSubmit.call(form, original); });
      target.append(proxy); original.dataset.quickProxied = 'true';
      return [original, proxy];
    });
    const sync = () => pairs.forEach(([original, proxy]) => {
      proxy.textContent = original.textContent.trim() || original.value;
      proxy.disabled = busy || original.disabled;
    });
    observer = new MutationObserver(sync);
    buttons.forEach(button => observer.observe(button, {attributes:true, childList:true, subtree:true, characterData:true}));
    sync();
  }
  function update() {
    clear();
    const forms = [...body.querySelectorAll('form')].filter(form => form.getAttribute('method')?.toLowerCase() === 'post');
    choose(forms.find(form => form.querySelector('input[name="token"]')) || forms[0]);
  }
  body.addEventListener('focusin', event => {
    const form = event.target.closest('form');
    if (form && form.getAttribute('method')?.toLowerCase() === 'post') choose(form);
  });
  return {update, clear, setBusy(value) {
    busy = value;
    target.querySelectorAll('button').forEach(button => { button.disabled = busy; });
    if (!busy && current) { const form = current; current = null; choose(form); }
  }};
};
