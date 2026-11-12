'use strict';
(() => {
const initialized = new WeakSet();
const confirmed = new WeakSet();
function init(root) {
const find = id => root.querySelector(`[data-quick-id="${id}"], #${id}`);
root.querySelectorAll('form[data-confirm]').forEach(form => {
  if (confirmed.has(form)) return;
  confirmed.add(form);
  form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});
const pointInput = find('redeem-points');
const paymentPreview = find('payment-preview');
if (pointInput && paymentPreview && !initialized.has(pointInput)) {
  initialized.add(pointInput);
  const form = pointInput.closest('form');
  const voucher = form.querySelector('[name="voucher_code"]');
  const quoted = form.querySelector('[name="quoted_total"]');
  const submit = find('collect-payment');
  let version = 0;
  const preview = async () => {
    const current = ++version;
    submit.disabled = true;
    try {
      const params = new URLSearchParams({points:pointInput.value || '0',voucher:voucher.value.trim()});
      const response = await fetch(form.dataset.quoteUrl + '?' + params);
      const data = await response.json();
      if (current !== version) return;
      if (!response.ok) throw new Error(data.error || 'Chưa kiểm tra được số cần thu.');
      quoted.value = data.total;
      paymentPreview.textContent = 'Cần thu: ' + new Intl.NumberFormat('vi-VN').format(data.total) + ' ₫';
      submit.disabled = false;
    } catch (error) {
      if (current === version) paymentPreview.textContent = error.message || 'Kết nối gián đoạn, hãy thử lại.';
    }
  };
  pointInput.addEventListener('input', preview); voucher.addEventListener('input', preview); preview();
}
}
document.addEventListener('gentleman:content', event => init(event.detail.root));
init(document);
})();
