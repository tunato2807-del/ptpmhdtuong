'use strict';
(() => {
const initialized = new WeakSet();
function init(root) {
const find = id => root.querySelector(`[data-quick-id="${id}"], #${id}`);
const bookingForm = find('booking-form');
if (!bookingForm || initialized.has(bookingForm)) return;
initialized.add(bookingForm);
{
  const branchPolicies = JSON.parse(find('branches-data').textContent);
  const employees = JSON.parse(find('employees-data').textContent);
  const services = JSON.parse(find('services-data').textContent);
  const branch = find('id_branch');
  const stylist = find('id_employee');
  const date = find('id_date');
  const time = find('id_time');
  const slots = find('time-slots');
  const submit = find('submit-booking');
  const customerSelect = find('id_customer');
  if (customerSelect) {
    const syncCustomer = () => find('summary-customer').textContent = customerSelect.value ? customerSelect.selectedOptions[0].textContent : 'Chưa chọn khách';
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
    Object.entries(values).forEach(([id, value]) => { const node = find(id); if (node) node.textContent = value; });
  }
  function updateStylists() {
    const policy=branchPolicies.find(item=>String(item.id)===branch.value);
    const hint=find('branch-policy');
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
    const target = find('selected-services');
    target.replaceChildren();
    if (!selected.length) {const p = document.createElement('p'); p.className = 'muted'; p.textContent = 'Chưa chọn dịch vụ'; target.append(p);}
    selected.forEach(item => {
      const row = document.createElement('div');
      const name = document.createElement('span'); name.textContent = item.name;
      const price = document.createElement('strong'); price.textContent = currency(item.price);
      row.append(name, price); target.append(row);
    });
    find('summary-total').textContent = currency(selected.reduce((n, item) => n + item.price, 0));
    find('summary-duration').textContent = selected.length ? selected.reduce((n, item) => n + item.duration, 0) + ' phút' : '—';
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
        const choose = () => {slots.querySelectorAll('button').forEach(item => {item.classList.remove('selected'); item.setAttribute('aria-pressed', 'false');}); button.classList.add('selected'); button.setAttribute('aria-pressed', 'true'); time.value = value; submit.disabled = false; updateTicket(); time.dispatchEvent(new Event('change', {bubbles:true}));};
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
}
document.addEventListener('gentleman:content', event => init(event.detail.root));
init(document);
})();
