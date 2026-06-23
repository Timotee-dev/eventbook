/* EventBook — site-wide JS. No build step, no frameworks. */

// ── Flash messages ──
function flash(msg, type='info') {
  let wrap = document.getElementById('flashWrap');
  if (!wrap) { wrap = document.createElement('div'); wrap.id='flashWrap'; wrap.className='flash-wrap'; document.body.appendChild(wrap); }
  const el = document.createElement('div');
  el.className = `flash ${type}`;
  el.textContent = msg;
  wrap.appendChild(el);
  setTimeout(() => { el.style.opacity='0'; el.style.transition='300ms'; setTimeout(()=>el.remove(),300); }, 3500);
}

// ── Button loading ──
function setLoading(btn, on) {
  if (on) { btn._html = btn.innerHTML; btn.disabled=true; btn.innerHTML='<span class="loading-ring"></span>'; }
  else     { btn.disabled=false; btn.innerHTML=btn._html||btn.innerHTML; }
}

// ── API client ──
const api = {
  async req(method, url, body) {
    const opts = { method, headers: {'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')} };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(url, opts);
    let d; try { d = await r.json(); } catch { d = {}; }
    return { ok: r.ok, status: r.status, data: d };
  },
  get:    (url)       => api.req('GET', url),
  post:   (url, body) => api.req('POST', url, body),
  patch:  (url, body) => api.req('PATCH', url, body),
  delete: (url)       => api.req('DELETE', url),
};

function getCookie(name) {
  const m = document.cookie.match(new RegExp(`(^|;)\\s*${name}\\s*=\\s*([^;]+)`));
  return m ? decodeURIComponent(m[2]) : '';
}

// ── Format helpers ──
function fmtNGN(amount) {
  const n = parseFloat(amount);
  if (n === 0) return '<span style="color:var(--green)">Free</span>';
  return '₦' + n.toLocaleString('en-NG', {minimumFractionDigits: 0});
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString('en-NG', {weekday:'short',day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
}

function fmtDateShort(iso) {
  return new Date(iso).toLocaleDateString('en-NG', {day:'numeric',month:'short',year:'numeric'});
}

function badge(status) {
  const map = {confirmed:'green',pending:'warn',cancelled:'red',refunded:'red',valid:'green',used:'violet',published:'green',draft:'violet',rejected:'red',failed:'red'};
  return `<span class="badge badge-${map[status]||'violet'}">${status}</span>`;
}

// ── Countdown chips ──
function initChips() {
  document.querySelectorAll('[data-start]').forEach(el => {
    updateChip(el);
    const iv = setInterval(()=>{ if (!document.contains(el)) clearInterval(iv); else updateChip(el); }, 15000);
  });
}

function updateChip(el) {
  const start = new Date(el.dataset.start);
  const end   = el.dataset.end ? new Date(el.dataset.end) : null;
  const now   = Date.now();
  const diff  = start - now;

  if (diff <= 0) {
    if (end && end > now) { el.className='chip live'; el.textContent=' LIVE NOW'; }
    else { el.className='chip'; el.textContent=' Ended'; el.style.opacity='.4'; }
    return;
  }
  const d=Math.floor(diff/86400000), h=Math.floor((diff%86400000)/3600000), m=Math.floor((diff%3600000)/60000);
  const label = d>30?`${Math.floor(d/7)}w`:d>0?`${d}d ${h}h`:h>0?`${h}h ${m}m`:`${m}m`;
  el.className = diff < 86400000 ? 'chip soon' : 'chip';
  el.textContent = ` ${label}`;
}

// ── Event card renderer ──
function renderCard(e) {
  const price = e.min_price !== undefined ? e.min_price : e.base_price;
  const img = e.banner
    ? `<img src="${e.banner}" alt="${e.title}" loading="lazy">`
    : `<div class="card-img-ph">${e.category_icon||'✦'}</div>`;
  return `
    <div class="card" onclick="location.href='/events/${e.slug}/'">
      <div class="card-img">
        ${img}
        <div class="chip" data-start="${e.start_datetime}" data-end="${e.end_datetime}"></div>
        ${e.is_sold_out?'<div class="sold-banner">Sold Out</div>':''}
      </div>
      <div class="card-body">
        <div class="card-cat">${e.category||'Event'} ${e.category_icon||''}</div>
        <div class="card-title">${e.title}</div>
        <div class="card-meta">
          <span>📅 ${fmtDate(e.start_datetime)}</span>
          <span>📍 ${e.is_online?'Online':e.city||''}</span>
        </div>
        <div class="card-footer">
          <div class="card-price ${e.is_free?'free':''}">${fmtNGN(price)}</div>
          ${e.avg_rating>0?`<span class="card-rating">★ ${e.avg_rating}</span>`:''}
        </div>
      </div>
    </div>`;
}

function skeletons(n=6) {
  return Array(n).fill(`<div class="card"><div class="skeleton card-img"></div><div class="card-body" style="gap:10px;display:flex;flex-direction:column"><div class="skeleton" style="height:11px;width:55%;border-radius:4px"></div><div class="skeleton" style="height:17px;border-radius:4px"></div><div class="skeleton" style="height:11px;width:75%;border-radius:4px"></div></div></div>`).join('');
}

// ── Nav ──
window.addEventListener('scroll', ()=>{
  document.querySelector('.nav')?.classList.toggle('scrolled', scrollY>30);
},{passive:true});

document.querySelector('.hamburger')?.addEventListener('click', ()=>{
  document.querySelector('.nav-links')?.classList.toggle('open');
});

// ── Notification badge ──
async function loadNotifCount() {
  const {data} = await api.get('/api/notifications/unread/');
  const dot = document.querySelector('.notif-dot');
  if (dot) dot.classList.toggle('hidden', !data?.count);
}

// ── Logout ──
document.getElementById('logoutBtn')?.addEventListener('click', async()=>{
  await api.post('/api/auth/logout/');
  location.href='/';
});

// ── Boot ──
document.addEventListener('DOMContentLoaded', ()=>{
  initChips();
  if (document.body.dataset.auth === 'true') loadNotifCount();
  // Show registered message
  if (new URLSearchParams(location.search).get('registered')) {
    flash('Account created! Check your email to verify.','info');
  }
});
