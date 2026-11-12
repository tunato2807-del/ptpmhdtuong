'use strict';
(() => {
  const dialog = document.querySelector('#quick-dialog');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const views = window.GentlemanDialogContent;
  const body = dialog.querySelector('[data-quick-body]');
  const title = dialog.querySelector('#quick-dialog-title');
  const status = dialog.querySelector('[data-quick-status]');
  const closeButton = dialog.querySelector('[data-quick-close]');
  const back = dialog.querySelector('[data-quick-back]');
  const fullPage = dialog.querySelector('[data-quick-page]');
  const actions = window.GentlemanDialogActions(body, dialog.querySelector('[data-quick-footer]'));
  let opener, current = null, trail = [], controller, sequence = 0, posting = false, unsaved = false, changed = false;
  const mayLeave = () => !posting && (!unsaved || window.confirm('Thông tin chưa được lưu. Bạn muốn bỏ thay đổi và tiếp tục?'));
  function chrome() {
    back.hidden = !trail.length;
    fullPage.hidden = !current;
    if (current) fullPage.href = current;
  }
  function show() {
    if (dialog.open) return;
    opener = document.activeElement;
    document.body.classList.add('quick-dialog-open'); dialog.showModal();
  }
  function focusContent(url) {
    const error = body.querySelector('[data-error-summary], .errorlist, .alert.error');
    const hash = new URL(url, location.href).hash.slice(1);
    const anchor = hash ? [...body.querySelectorAll('[id], [data-quick-id]')].find(el => el.id === hash || el.dataset.quickId === hash) : null;
    const focus = error || anchor?.querySelector('input:not([type="hidden"]), select, textarea') || title;
    if (!focus.hasAttribute('tabindex') && !focus.matches('input, select, textarea, button, a')) focus.tabIndex = -1;
    focus.focus({preventScroll:true});
    if (focus !== title) focus.scrollIntoView({block:'nearest'});
  }
  function menu() {
    ++sequence; controller?.abort(); body.removeAttribute('aria-busy');
    current = null; unsaved = false; actions.clear();
    title.textContent = 'Bạn cần làm gì?'; status.textContent = '';
    body.replaceChildren(document.querySelector('#quick-menu-content').content.cloneNode(true));
    body.scrollTop = 0; views.decorate(body); chrome(); title.focus();
  }
  function loading() {
    actions.clear(); status.textContent = 'Đang mở nội dung…'; body.setAttribute('aria-busy', 'true');
    body.innerHTML = '<div class="quick-skeleton" aria-hidden="true"><span></span><span></span><span></span></div>';
  }
  function display(result, requested) {
    current = result.url; unsaved = false;
    title.textContent = result.doc.title.split(' · ')[0] || 'Thông tin';
    views.mount(body, result); actions.update(); chrome(); focusContent(requested);
  }
  async function load(url, remember = true) {
    if (!mayLeave()) return;
    unsaved = false;
    if (remember && dialog.open) trail.push(current);
    if (trail.length > 20) trail.shift();
    show(); current = url; chrome(); controller?.abort(); controller = new AbortController();
    const request = controller;
    const version = ++sequence; const timer = setTimeout(() => request.abort(), 20000);
    loading();
    try {
      const result = await views.read(url, {signal:request.signal});
      if (version !== sequence || !dialog.open || !result) return;
      display(result, url); status.textContent = '';
    } catch (_) {
      if (version !== sequence || !dialog.open) return;
      body.replaceChildren(); status.textContent = 'Chưa mở được nội dung. Hãy thử lại hoặc mở trang riêng.';
      const retry = document.createElement('button'); retry.type = 'button'; retry.className = 'btn btn-outline'; retry.textContent = 'Thử lại';
      retry.addEventListener('click', () => load(url, false)); body.append(retry); retry.focus();
    } finally { clearTimeout(timer); if (version === sequence) body.removeAttribute('aria-busy'); }
  }
  function close() {
    if (!mayLeave()) return;
    ++sequence; controller?.abort(); dialog.close(); actions.clear(); body.replaceChildren();
    document.body.classList.remove('quick-dialog-open');
    opener?.focus({preventScroll:true});
    if (changed) {
      try { sessionStorage.setItem('gentleman-dialog-scroll', JSON.stringify([window.scrollX, window.scrollY])); } catch (_) { /* Storage is optional. */ }
      location.reload();
    }
    trail = []; unsaved = false;
  }
  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const launcher = event.target.closest('[data-quick-menu]');
    if (launcher) { event.preventDefault(); if (!mayLeave()) return; show(); trail = []; menu(); return; }
    const link = event.target.closest('a[href]');
    if (!link || !views.eligible(link)) return;
    const url = new URL(link.href);
    if (dialog.contains(link) && url.hash && current && url.pathname === new URL(current).pathname && url.search === new URL(current).search) {
      const anchor = [...body.querySelectorAll('[id]')].find(el => el.id === url.hash.slice(1));
      if (anchor) {
        event.preventDefault(); anchor.scrollIntoView({block:'start'});
        anchor.querySelector('input:not([type="hidden"]), select, textarea')?.focus({preventScroll:true});
        return;
      }
    }
    event.preventDefault(); load(url.href, dialog.open);
  });
  closeButton.addEventListener('click', close);
  document.addEventListener('submit', event => {
    const form = event.target;
    if (event.defaultPrevented || dialog.contains(form) || (form.getAttribute('method') || 'get').toLowerCase() !== 'get') return;
    const url = new URL(form.getAttribute('action') || location.href, location.href);
    if (url.origin !== location.origin || url.pathname !== '/dat-lich/') return;
    event.preventDefault(); url.search = new URLSearchParams(new FormData(form, event.submitter)).toString(); load(url.href, false);
  });
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
  back.addEventListener('click', () => { if (!mayLeave()) return; const url = trail.pop(); unsaved = false; if (url) load(url, false); else menu(); });
  ['input', 'change'].forEach(type => body.addEventListener(type, event => { if (event.target.closest('form')?.getAttribute('method')?.toLowerCase() === 'post') unsaved = true; }));
  body.addEventListener('submit', async event => {
    const form = event.target;
    if (event.defaultPrevented || posting) { if (posting) event.preventDefault(); return; }
    const action = event.submitter?.getAttribute('formaction') || form.getAttribute('action') || current;
    const url = new URL(action, current || location.href);
    if (url.origin !== location.origin || /\/dang-(?:nhap|xuat)\//.test(url.pathname)) return;
    const data = new FormData(form, event.submitter);
    event.preventDefault();
    if ((form.getAttribute('method') || 'get').toLowerCase() === 'get') {
      url.search = new URLSearchParams(data).toString();
      if (views.download(url)) window.open(url.href, '_blank', 'noopener'); else load(url.href);
      return;
    }
    posting = true; changed = true; closeButton.disabled = true; back.disabled = true; fullPage.hidden = true;
    actions.setBusy(true); status.textContent = 'Đang gửi thông tin. Vui lòng chờ kết quả…';
    const pending = new AbortController(); const timer = setTimeout(() => pending.abort(), 45000);
    try {
      const result = await views.read(url.href, {method:'POST', body:data, signal:pending.signal});
      if (!result) return;
      display(result, result.url);
      unsaved = Boolean(body.querySelector('.errorlist, .alert.error, [data-error-summary], input[name="token"]'));
      status.textContent = unsaved ? 'Kiểm tra thông tin trong cửa sổ này trước khi tiếp tục.' : 'Đã nhận kết quả. Bạn có thể tiếp tục thao tác hoặc đóng cửa sổ.';
    } catch (_) {
      status.textContent = 'Chưa xác nhận được kết quả gửi. Hãy kiểm tra lại dữ liệu trước khi gửi thêm; yêu cầu không được tự gửi lại.';
    } finally { clearTimeout(timer); posting = false; closeButton.disabled = false; back.disabled = false; actions.setBusy(false); chrome(); }
  });
  document.body.classList.add('quick-ready'); views.decorate(document);
  try {
    const saved = JSON.parse(sessionStorage.getItem('gentleman-dialog-scroll'));
    sessionStorage.removeItem('gentleman-dialog-scroll');
    if (Array.isArray(saved) && saved.length === 2 && saved.every(n => Number.isFinite(n) && n >= 0 && n < 1e7)) {
      window.addEventListener('load', () => { requestAnimationFrame(() => { window.scrollTo({left:saved[0], top:saved[1], behavior:'instant'}); document.querySelector('.quick-launcher').focus({preventScroll:true}); }); });
    }
  } catch (_) { /* The dialog also works when browser storage is disabled. */ }
})();
