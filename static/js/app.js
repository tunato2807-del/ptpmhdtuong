'use strict';
document.querySelectorAll('.dismiss').forEach(button => button.addEventListener('click', () => button.closest('.alert').remove()));
document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', event => {
  if (!window.confirm(form.dataset.confirm)) event.preventDefault();
}));
document.querySelectorAll('[data-print]').forEach(button => button.addEventListener('click', () => window.print()));
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
const bookingForm = document.querySelector('#booking-form');
if (bookingForm) {
  const branchPolicies = JSON.parse(document.querySelector('#branches-data').textContent);
  const employees = JSON.parse(document.querySelector('#employees-data').textContent);
  const services = JSON.parse(document.querySelector('#services-data').textContent);
  const branch = bookingForm.querySelector('#id_branch');
  const stylist = bookingForm.querySelector('#id_employee');
  const date = bookingForm.querySelector('#id_date');
  const time = bookingForm.querySelector('#id_time');
  const slots = document.querySelector('#time-slots');
  const submit = document.querySelector('#submit-booking');
  const customerSelect = bookingForm.querySelector('#id_customer');
  if (customerSelect) {
    const syncCustomer = () => document.querySelector('#summary-customer').textContent = customerSelect.value ? customerSelect.selectedOptions[0].textContent : 'Chưa chọn khách';
    customerSelect.addEventListener('change', syncCustomer); syncCustomer();
  }
  const currency = number => new Intl.NumberFormat('vi-VN').format(number) + ' ₫';
  let controller, requestVersion = 0;
  const selectedServices = () => Array.from(bookingForm.querySelectorAll('input[name="services"]:checked')).map(input => input.value);
  function updateTicket() {
    const values = {
      'summary-time': time.value || '—',
      'summary-date': /^\d{4}-\d{2}-\d{2}$/.test(date.value) ? date.value.split('-').reverse().join(' / ') : 'Chưa chọn ngày',
      'summary-branch': branch.value ? branch.selectedOptions[0].textContent : 'Chưa chọn',
      'summary-stylist': stylist.value ? stylist.selectedOptions[0].textContent : 'Chưa chọn',
    };
    Object.entries(values).forEach(([id, value]) => { const node = document.getElementById(id); if (node) node.textContent = value; });
  }
  function updateStylists() {
    const policy=branchPolicies.find(item=>String(item.id)===branch.value);
    const hint=document.querySelector('#branch-policy');
    if (hint) hint.textContent=policy ? `Đổi/hủy trước ít nhất ${policy.cancel_hours} giờ; đặt trước tối đa ${policy.booking_days} ngày; chờ khách muộn ${policy.late_minutes} phút.` : 'Việc đổi/hủy áp dụng chính sách của chi nhánh bạn chọn.';
    const previous = stylist.value;
    stylist.replaceChildren(new Option('Chọn stylist', ''));
    employees.filter(item => String(item.branch_id) === branch.value).forEach(item => stylist.add(new Option(item.name + ' · ' + item.specialty, item.id)));
    if (Array.from(stylist.options).some(option => option.value === previous)) stylist.value = previous;
  }
  function updateSummary() {
    updateTicket();
    const ids = selectedServices();
    const selected = services.filter(item => ids.includes(String(item.id)));
    const target = document.querySelector('#selected-services');
    target.replaceChildren();
    if (!selected.length) {const p = document.createElement('p'); p.className = 'muted'; p.textContent = 'Chưa chọn dịch vụ'; target.append(p);}
    selected.forEach(item => {
      const row = document.createElement('div');
      const name = document.createElement('span'); name.textContent = item.name;
      const price = document.createElement('strong'); price.textContent = currency(item.price);
      row.append(name, price); target.append(row);
    });
    document.querySelector('#summary-total').textContent = currency(selected.reduce((n, item) => n + item.price, 0));
    document.querySelector('#summary-duration').textContent = selected.length ? selected.reduce((n, item) => n + item.duration, 0) + ' phút' : '—';
  }
  function message(text) {const p = document.createElement('p'); p.className = 'muted'; p.textContent = text; slots.replaceChildren(p);}
  async function loadSlots(preserve = false) {
    if (controller) controller.abort();
    const version = ++requestVersion;
    const oldTime = preserve ? time.value : '';
    time.value = ''; submit.disabled = true;
    updateSummary();
    const ids = selectedServices();
    if (!branch.value || !stylist.value || !date.value || !ids.length) {message('Chọn chi nhánh, dịch vụ, stylist và ngày để xem giờ trống.'); return;}
    message('Đang tìm khung giờ phù hợp…');
    const params = new URLSearchParams({branch:branch.value, employee:stylist.value, date:date.value});
    ids.forEach(id => params.append('services', id));
    controller = new AbortController();
    try {
      const response = await fetch(bookingForm.dataset.slotsUrl + '?' + params, {signal:controller.signal, headers:{'Accept':'application/json'}});
      const data = await response.json();
      if (version !== requestVersion) return;
      if (!response.ok) throw new Error(data.error || 'Không thể tải khung giờ. Vui lòng thử lại.');
      if (!data.slots.length) {message('Không còn khung giờ phù hợp. Hãy thử ngày hoặc stylist khác.'); return;}
      slots.replaceChildren();
      data.slots.forEach(value => {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'slot-button';
        button.textContent = value; button.setAttribute('aria-pressed', 'false');
        const choose = () => {slots.querySelectorAll('button').forEach(item => {item.classList.remove('selected'); item.setAttribute('aria-pressed', 'false');}); button.classList.add('selected'); button.setAttribute('aria-pressed', 'true'); time.value = value; submit.disabled = false; updateTicket();};
        button.addEventListener('click', choose); slots.append(button);
        if (value === oldTime) choose();
      });
    } catch (error) {
      if (error.name !== 'AbortError' && version === requestVersion) {message(error.message || 'Kết nối gián đoạn. Hãy đổi ngày để thử lại.');}
    }
  }
  branch.addEventListener('change', () => {updateStylists(); loadSlots();});
  stylist.addEventListener('change', () => loadSlots());
  date.addEventListener('change', () => loadSlots());
  bookingForm.querySelectorAll('input[name="services"]').forEach(input => input.addEventListener('change', () => loadSlots()));
  bookingForm.addEventListener('submit', event => {
    if (!time.value) {event.preventDefault(); message('Vui lòng chọn một khung giờ.'); return;}
    submit.disabled = true; submit.textContent = 'Đang xác nhận…';
  });
  updateStylists(); loadSlots(true);
}

const pointInput = document.querySelector('#redeem-points');
const paymentPreview = document.querySelector('#payment-preview');
if (pointInput && paymentPreview) {
  const form = pointInput.closest('form');
  const voucher = form.querySelector('[name="voucher_code"]');
  const quoted = form.querySelector('[name="quoted_total"]');
  const submit = form.querySelector('#collect-payment');
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
