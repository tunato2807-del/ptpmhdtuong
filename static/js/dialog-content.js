'use strict';
(() => {
  const download = url => /\/(?:xuat|pdf)\//.test(url.pathname) || /\.(?:pdf|xlsx|csv)$/.test(url.pathname) || url.searchParams.has('export');
  const supported = url => url.origin === location.origin && !download(url) &&
    !/\/(?:bao-gia|thao-tac|danh-gia|ngung)\/$/.test(url.pathname) &&
    /^(?:\/quan-ly\/(?:.+)?|\/lich-hen\/\d+\/(?:.*)?|\/(?:dat-lich|lich-cua-toi|tai-khoan|thong-bao|diem-tich-luy|stylist|tim-kiem)\/)$/u.test(url.pathname);
  function eligible(link) {
    if (link.getAttribute('href')?.startsWith('#') && !link.closest('#quick-dialog')) return false;
    if (link.hasAttribute('data-quick-native') || link.hasAttribute('download') || (link.target && link.target !== '_self')) return false;
    const url = new URL(link.href, location.href);
    if (!supported(url)) return false;
    return link.hasAttribute('data-quick-dialog') || !link.closest('.sidebar, #customer-nav, .footer-links');
  }
  function decorate(root) {
    root.querySelectorAll('a[href]').forEach(link => {
      if (eligible(link)) { link.setAttribute('aria-haspopup', 'dialog'); link.setAttribute('aria-controls', 'quick-dialog'); }
    });
  }
  async function read(url, options = {}) {
    const response = await fetch(url, {credentials:'same-origin', cache:'no-store', ...options});
    const destination = new URL(response.url);
    if (destination.origin !== location.origin) throw new Error('Không thể mở địa chỉ này tại đây.');
    if (/^\/dang-nhap\//.test(destination.pathname)) { location.assign(destination.href); return null; }
    if (response.status >= 500) throw new Error('Máy chủ chưa xử lý được yêu cầu. Hãy thử lại sau.');
    if (!response.headers.get('Content-Type')?.includes('text/html')) throw new Error('Nội dung này cần mở bằng trang riêng.');
    const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
    if (!doc.querySelector('main')) throw new Error('Không tải được nội dung. Phiên đăng nhập có thể đã thay đổi; hãy mở trang riêng để kiểm tra.');
    return {doc, url:destination.href, redirected:response.redirected, status:response.status};
  }
  function mount(body, result) {
    const root = document.importNode(result.doc.querySelector('main'), true);
    root.removeAttribute('id');
    root.removeAttribute('class');
    root.className = result.doc.body.classList.contains('staff-app') ? 'quick-surface staff-app' : 'quick-surface customer-app';
    root.querySelectorAll('script:not([type="application/json"]), iframe, object, embed, .staff-footer').forEach(el => el.remove());
    const ids = new Map();
    root.querySelectorAll('[id]').forEach(el => {
      const old = el.id;
      el.dataset.quickId = old;
      el.id = 'quick-content-' + old;
      ids.set(old, el.id);
    });
    root.querySelectorAll('[for], [aria-labelledby], [aria-describedby], [aria-controls], [form]').forEach(el => {
      ['for', 'aria-labelledby', 'aria-describedby', 'aria-controls', 'form'].forEach(attr => {
        if (el.hasAttribute(attr)) el.setAttribute(attr, el.getAttribute(attr).split(/\s+/).map(id => ids.get(id) || id).join(' '));
      });
    });
    root.querySelectorAll('a[href]').forEach(link => {
      const url = new URL(link.getAttribute('href'), result.url);
      if (url.hash && ids.has(url.hash.slice(1))) url.hash = ids.get(url.hash.slice(1));
      link.href = url.href;
    });
    root.querySelectorAll('form').forEach(form => {
      form.setAttribute('action', new URL(form.getAttribute('action') || result.url, result.url).href);
      form.querySelectorAll('[formaction]').forEach(button => { button.formAction = new URL(button.getAttribute('formaction'), result.url).href; });
    });
    root.querySelectorAll('.reveal-ready').forEach(el => el.classList.add('is-visible'));
    body.replaceChildren(root);
    body.scrollTop = 0;
    decorate(body);
    document.dispatchEvent(new CustomEvent('gentleman:content', {detail:{root}}));
    return root;
  }
  window.GentlemanDialogContent = {download, supported, eligible, decorate, read, mount};
})();
