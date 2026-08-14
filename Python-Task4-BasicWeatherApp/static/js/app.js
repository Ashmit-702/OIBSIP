/* ============================================================
   STATION — frontend for the Flask-backed weather instrument
   Talks only to our own /api/* routes — never to OpenWeatherMap
   directly, so the API key never reaches the browser.
   ============================================================ */

let unit = 'metric';
let lastQuery = null;
let currentLocation = null; // { name, country, lat, lon } for whatever's on screen
let pinnedCities = [];      // cached from /api/pinned

const els = {
  cityInput: document.getElementById('cityInput'),
  searchBtn: document.getElementById('searchBtn'),
  geoBtn: document.getElementById('geoBtn'),
  unitC: document.getElementById('unitC'),
  unitF: document.getElementById('unitF'),
  status: document.getElementById('status'),
  statusIcon: document.getElementById('statusIcon'),
  statusText: document.getElementById('statusText'),
  card: document.getElementById('card'),
  graphBg: document.getElementById('graphBg'),
  skyBg: document.getElementById('skyBg'),
  heroLoc: document.getElementById('heroLoc'),
  heroCity: document.getElementById('heroCity'),
  heroLocalTime: document.getElementById('heroLocalTime'),
  heroTemp: document.getElementById('heroTemp'),
  heroUnit: document.getElementById('heroUnit'),
  heroDesc: document.getElementById('heroDesc'),
  heroFeels: document.getElementById('heroFeels'),
  heroAdvisory: document.getElementById('heroAdvisory'),
  heroIcon: document.getElementById('heroIcon'),
  pinBtn: document.getElementById('pinBtn'),
  pinnedRow: document.getElementById('pinnedRow'),
  hourlyTitle: document.getElementById('hourlyTitle'),
  hourly: document.getElementById('hourly'),
  rHumidity: document.getElementById('rHumidity'),
  rWind: document.getElementById('rWind'),
  rPressure: document.getElementById('rPressure'),
  rVisibility: document.getElementById('rVisibility'),
  sunArc: document.getElementById('sunArc'),
  sunriseTime: document.getElementById('sunriseTime'),
  sunsetTime: document.getElementById('sunsetTime'),
  aqiBadge: document.getElementById('aqiBadge'),
  aqiCategory: document.getElementById('aqiCategory'),
  aqiFine: document.getElementById('aqiFine'),
  forecastTitle: document.getElementById('forecastTitle'),
  forecast: document.getElementById('forecast'),
  history: document.getElementById('history'),
  clock: document.getElementById('clock'),
};

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---- sky background: builds decorative elements for the current theme ---- */
function renderSky(theme){
  els.skyBg.dataset.sky = theme;
  if(prefersReducedMotion){ els.skyBg.innerHTML = ''; return; }

  const rand = (min, max) => Math.random() * (max - min) + min;
  let html = '';

  if(theme === 'clear_night' || theme === 'cloudy_night'){
    for(let i = 0; i < 40; i++){
      html += `<div class="sky-el sky-star" style="top:${rand(0,70)}%; left:${rand(0,100)}%; animation-delay:${rand(0,3)}s;"></div>`;
    }
    html += `<div class="sky-el sky-moon" style="width:90px; height:90px; top:8%; right:12%;"></div>`;
  }
  if(theme === 'clear_day'){
    html += `<div class="sky-el sky-sun" style="width:220px; height:220px; top:-4%; right:8%;"></div>`;
  }
  if(theme === 'cloudy_day' || theme === 'cloudy_night' || theme === 'rain' || theme === 'drizzle' || theme === 'storm'){
    const count = theme === 'storm' ? 5 : 3;
    for(let i = 0; i < count; i++){
      const size = rand(140, 260);
      html += `<div class="sky-el sky-cloud" style="width:${size}px; height:${size*0.5}px; top:${rand(4,30)}%; left:${rand(-10,80)}%; animation-duration:${rand(50,90)}s; animation-delay:-${rand(0,60)}s;"></div>`;
    }
  }
  if(theme === 'rain' || theme === 'drizzle' || theme === 'storm'){
    const count = theme === 'storm' ? 60 : 36;
    for(let i = 0; i < count; i++){
      html += `<div class="sky-el sky-drop" style="height:${rand(14,26)}px; top:0; left:${rand(0,100)}%; animation-duration:${rand(0.5,1)}s; animation-delay:-${rand(0,1)}s;"></div>`;
    }
  }
  if(theme === 'snow'){
    for(let i = 0; i < 40; i++){
      const size = rand(2,4);
      html += `<div class="sky-el sky-flake" style="width:${size}px; height:${size}px; top:0; left:${rand(0,100)}%; animation-duration:${rand(6,12)}s; animation-delay:-${rand(0,10)}s;"></div>`;
    }
  }
  if(theme === 'mist'){
    for(let i = 0; i < 4; i++){
      html += `<div class="sky-el sky-fogband" style="top:${rand(10,70)}%; animation-duration:${rand(14,22)}s; animation-delay:-${rand(0,10)}s;"></div>`;
    }
  }
  els.skyBg.innerHTML = html;
}
renderSky('clear_night'); // sensible default before the first search

/* ---- clock ---- */
function tickClock(){
  const now = new Date();
  els.clock.textContent = now.toLocaleString(undefined, {
    weekday:'short', hour:'2-digit', minute:'2-digit', hour12:false
  }).toUpperCase();
}
tickClock();
setInterval(tickClock, 30_000);

/* ---- icon set ---- */
function weatherIcon(code, color){
  color = color || 'var(--amber)';
  const stroke = `stroke="${color}" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"`;
  const main = code ? code.slice(0,2) : '01';
  const icons = {
    '01': `<circle cx="50" cy="50" r="20" ${stroke}/>`,
    '02': `<circle cx="38" cy="46" r="14" ${stroke}/><path d="M30 68h40a14 14 0 0 0 0-28 18 18 0 0 0-34-6" ${stroke}/>`,
    '03': `<path d="M26 68h46a16 16 0 0 0 0-32 22 22 0 0 0-42 6 14 14 0 0 0-4 26z" ${stroke}/>`,
    '04': `<path d="M22 70h40a14 14 0 0 0 2-28 20 20 0 0 0-38-4 12 12 0 0 0-4 32z" ${stroke}/><path d="M52 40a16 16 0 0 1 16 16" ${stroke}/>`,
    '09': `<path d="M26 54h44a14 14 0 0 0 0-28 20 20 0 0 0-38 4 12 12 0 0 0-6 24z" ${stroke}/><path d="M36 68v6M50 68v6M64 68v6" ${stroke}/>`,
    '10': `<path d="M24 50h44a14 14 0 0 0 0-28 20 20 0 0 0-38 4 12 12 0 0 0-6 24z" ${stroke}/><path d="M34 64v8M48 64v8M62 64v8" ${stroke}/>`,
    '11': `<path d="M24 46h44a14 14 0 0 0 0-28 20 20 0 0 0-38 4 12 12 0 0 0-6 24z" ${stroke}/><path d="M52 58l-10 16h10l-8 14" ${stroke}/>`,
    '13': `<path d="M24 46h44a14 14 0 0 0 0-28 20 20 0 0 0-38 4 12 12 0 0 0-6 24z" ${stroke}/><path d="M36 62v10M31 67h10M56 62v10M51 67h10" ${stroke}/>`,
    '50': `<path d="M20 40h56M28 52h48M20 64h56" ${stroke}/>`
  };
  return icons[main] || icons['01'];
}
function renderIconInto(el, code, color){ el.innerHTML = weatherIcon(code, color); }

/* ---- barograph background ---- */
function drawGraph(temps){
  const w = 900, h = 260;
  let grid = '';
  for(let x=0; x<=w; x+=45){ grid += `<line x1="${x}" y1="0" x2="${x}" y2="${h}" stroke="rgba(244,247,248,0.03)" stroke-width="1"/>`; }
  for(let y=0; y<=h; y+=32.5){ grid += `<line x1="0" y1="${y}" x2="${w}" y2="${y}" stroke="rgba(244,247,248,0.03)" stroke-width="1"/>`; }

  let path = '';
  if(temps && temps.length > 1){
    const min = Math.min(...temps), max = Math.max(...temps);
    const range = (max - min) || 1;
    const stepX = w / (temps.length - 1);
    const pts = temps.map((t,i) => [i * stepX, h - 40 - ((t - min) / range) * (h - 80)]);
    // smooth the polyline into a curve through midpoints, so real-world
    // temperature noise doesn't read as a jagged, alarming zig-zag
    path = `M ${pts[0][0]},${pts[0][1]} `;
    for(let i = 1; i < pts.length; i++){
      const [x0,y0] = pts[i-1], [x1,y1] = pts[i];
      const mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
      path += `Q ${x0},${y0} ${mx},${my} `;
    }
    path += `T ${pts[pts.length-1][0]},${pts[pts.length-1][1]}`;
  }

  els.graphBg.innerHTML = `
    ${grid}
    <path d="${path}" fill="none" stroke="var(--amber)" stroke-width="2"
      stroke-dasharray="1400" stroke-dashoffset="1400"
      style="animation: draw 1.6s ease forwards;" opacity="0.6"/>
    <style>@keyframes draw { to { stroke-dashoffset: 0; } }</style>
  `;
}

/* ---- sun arc: half-circle path, dot positioned by day_progress ---- */
function drawSunArc(dayProgress, isDaytime){
  const w = 300, h = 110;
  const cx = w/2, cy = 100, r = 90;
  const angle = Math.PI * (1 - dayProgress);
  const sunX = cx + r * Math.cos(angle);
  const sunY = cy - r * Math.sin(angle);
  const sunColor = isDaytime ? 'var(--amber)' : 'var(--teal)';

  els.sunArc.innerHTML = `
    <path d="M ${cx-r} ${cy} A ${r} ${r} 0 0 1 ${cx+r} ${cy}"
      fill="none" stroke="var(--line-strong)" stroke-width="1.5" stroke-dasharray="3 4"/>
    <line x1="${cx-r-6}" y1="${cy}" x2="${cx+r+6}" y2="${cy}" stroke="var(--line)" stroke-width="1"/>
    <circle cx="${sunX}" cy="${sunY}" r="16" fill="${sunColor}" opacity="0.18"/>
    <circle cx="${sunX}" cy="${sunY}" r="8" fill="${sunColor}"/>
    <circle cx="${sunX}" cy="${sunY}" r="8" fill="none" stroke="var(--sky-deep)" stroke-width="1.5"/>
  `;
}

/* ---- number count-up ---- */
function animateNumber(el, to){
  const duration = 700;
  const start = performance.now();
  function step(now){
    const p = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(to * eased);
    if(p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/* ---- status ---- */
function setStatus(msg, isError, done){
  els.statusText.textContent = msg;
  els.status.className = 'status show' + (isError ? ' error' : '') + (done ? ' done' : '');
}
function clearStatus(){ els.status.className = 'status'; }

/* ---- unit toggle ---- */
function setUnit(u){
  unit = u;
  els.unitC.classList.toggle('active', u === 'metric');
  els.unitF.classList.toggle('active', u === 'imperial');
  if(lastQuery) fetchWeather(lastQuery);
  loadPinned();
}
els.unitC.addEventListener('click', () => setUnit('metric'));
els.unitF.addEventListener('click', () => setUnit('imperial'));

/* ---- pinned cities ---- */
async function loadPinned(){
  try{
    const res = await fetch(`/api/pinned?units=${unit}`);
    if(!res.ok) return;
    pinnedCities = await res.json();
    renderPinned();
    updatePinButton();
  } catch(e){ /* pinned cities are a bonus feature; fail silently */ }
}

function renderPinned(){
  els.pinnedRow.innerHTML = pinnedCities.map(p => `
    <div class="pin-chip" data-city="${p.city}" data-country="${p.country}">
      <svg viewBox="0 0 100 100">${p.ok ? weatherIcon(p.icon, 'var(--amber)') : ''}</svg>
      <span class="pin-chip-name">${p.city}</span>
      <span class="pin-chip-temp">${p.ok ? p.temp + '°' : '—'}</span>
      <button class="pin-chip-remove" data-remove-city="${p.city}" data-remove-country="${p.country}" title="Unpin" aria-label="Unpin ${p.city}">✕</button>
    </div>
  `).join('');

  els.pinnedRow.querySelectorAll('.pin-chip').forEach(chip => {
    chip.addEventListener('click', (e) => {
      if(e.target.closest('.pin-chip-remove')) return;
      fetchWeather({ type: 'city', value: `${chip.dataset.city}, ${chip.dataset.country}` });
    });
  });
  els.pinnedRow.querySelectorAll('.pin-chip-remove').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await fetch('/api/pinned', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city: btn.dataset.removeCity, country: btn.dataset.removeCountry }),
      });
      loadPinned();
    });
  });
}

function updatePinButton(){
  if(!currentLocation){ return; }
  const pinned = pinnedCities.some(p => p.city === currentLocation.name && p.country === currentLocation.country);
  els.pinBtn.classList.toggle('pinned', pinned);
  els.pinBtn.textContent = pinned ? '★' : '☆';
  els.pinBtn.title = pinned ? 'Unpin this city' : 'Pin this city';
}

els.pinBtn.addEventListener('click', async () => {
  if(!currentLocation) return;
  const alreadyPinned = pinnedCities.some(p => p.city === currentLocation.name && p.country === currentLocation.country);
  if(alreadyPinned){
    await fetch('/api/pinned', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city: currentLocation.name, country: currentLocation.country }),
    });
  } else {
    const res = await fetch('/api/pinned', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentLocation),
    });
    if(!res.ok){
      const data = await res.json().catch(() => ({}));
      setStatus(data.error || "Couldn't pin that city.", true);
      return;
    }
  }
  loadPinned();
});

/* ---- history ---- */
async function loadHistory(){
  try{
    const res = await fetch('/api/history');
    if(!res.ok) return;
    const items = await res.json();
    if(items.length === 0){ els.history.innerHTML = ''; return; }
    els.history.innerHTML = '<div class="history-title">Recent</div>' +
      items.map(c => `<button class="chip" data-city="${c.city}, ${c.country}">${c.city}, ${c.country}</button>`).join('');
    els.history.querySelectorAll('.chip').forEach(chip => {
      chip.addEventListener('click', () => {
        els.cityInput.value = chip.dataset.city;
        fetchWeather({ type: 'city', value: chip.dataset.city });
      });
    });
  } catch(e){ /* history is a nice-to-have; fail silently */ }
}

/* ---- main fetch ---- */
async function fetchWeather(query){
  lastQuery = query;
  setStatus('Reading the instrument…');
  els.forecastTitle.classList.remove('show');
  els.forecast.innerHTML = '';
  if(els.card.classList.contains('show')){
    els.card.classList.add('loading'); // keep last result visible, dimmed, while refetching
  }

  const params = new URLSearchParams({ units: unit });
  if(query.type === 'city') params.set('city', query.value);
  else { params.set('lat', query.value.lat); params.set('lon', query.value.lon); }

  try{
    const res = await fetch(`/api/weather?${params.toString()}`);
    const data = await res.json();
    if(!res.ok){ throw new Error(data.error || `Server returned ${res.status}`); }
    render(data);
    setStatus('Up to date', false, true);
    setTimeout(clearStatus, 2000);
    els.card.classList.remove('loading');
    els.card.classList.add('show');
    loadHistory();
  } catch(err){
    els.card.classList.remove('loading');
    setStatus(err.message || 'Something went wrong.', true);
  }
}

function render(data){
  const { location, current, sun, air_quality, forecast, hourly, trend, units, sky_theme, advisory } = data;
  const unitLabel = units === 'metric' ? '°C' : '°F';
  const windUnit = units === 'metric' ? 'm/s' : 'mph';

  currentLocation = { name: location.name, country: location.country, lat: location.lat, lon: location.lon };
  document.title = `${location.name} ${current.temp}${unitLabel} — Station`;
  renderSky(sky_theme);

  els.heroLoc.textContent = `${location.lat.toFixed(2)}°, ${location.lon.toFixed(2)}°`;
  els.heroCity.textContent = `${location.name}, ${location.country}`;
  els.heroLocalTime.textContent = `Local time ${sun.local_time}`;
  animateNumber(els.heroTemp, current.temp);
  els.heroUnit.textContent = unitLabel;
  els.heroDesc.textContent = current.description;
  els.heroFeels.textContent = `Feels like ${current.feels_like}${unitLabel} · ${current.clouds_pct}% cloud cover`;
  els.heroAdvisory.textContent = advisory;
  renderIconInto(els.heroIcon, current.icon, 'var(--amber)');

  els.rHumidity.textContent = `${current.humidity}%`;
  els.rWind.textContent = `${current.wind_speed} ${windUnit} ${current.wind_compass}`;
  els.rPressure.textContent = `${current.pressure} hPa`;
  els.rVisibility.textContent = `${current.visibility_km} km`;

  els.sunriseTime.textContent = sun.sunrise;
  els.sunsetTime.textContent = sun.sunset;
  drawSunArc(sun.day_progress, sun.is_daytime);

  const aqiClass = air_quality.aqi <= 2 ? '' : air_quality.aqi <= 3 ? 'moderate' : 'poor';
  els.aqiBadge.textContent = air_quality.aqi;
  els.aqiBadge.className = 'aqi-badge' + (aqiClass ? ' ' + aqiClass : '');
  els.aqiCategory.textContent = air_quality.category;
  els.aqiFine.textContent = `PM2.5 ${air_quality.pm2_5} · PM10 ${air_quality.pm10} µg/m³`;

  drawGraph(trend);

  els.hourly.innerHTML = '';
  (hourly || []).forEach(h => {
    const div = document.createElement('div');
    div.className = 'hour-card';
    div.innerHTML = `
      <div class="hour-card-time">${h.time}</div>
      <svg viewBox="0 0 100 100">${weatherIcon(h.icon, 'var(--amber)')}</svg>
      <div class="hour-card-temp">${h.temp}°</div>
      <div class="hour-card-pop">${h.pop > 0 ? h.pop + '%' : ''}</div>
    `;
    els.hourly.appendChild(div);
  });
  els.hourlyTitle.classList.add('show');

  els.forecast.innerHTML = '';
  forecast.forEach((entry, i) => {
    const dayLabel = i === 0 ? 'Today' : entry.day_label;
    const div = document.createElement('div');
    div.className = 'fcard';
    div.style.animationDelay = `${i * 80}ms`;
    div.innerHTML = `
      <div class="fcard-day">${dayLabel}</div>
      <svg viewBox="0 0 100 100">${weatherIcon(entry.icon, 'var(--teal)')}</svg>
      <div class="fcard-hi">${entry.temp_max}°</div>
      <div class="fcard-lo">${entry.temp_min}°</div>
    `;
    els.forecast.appendChild(div);
  });
  els.forecastTitle.classList.add('show');
  updatePinButton();
}

/* ---- events ---- */
els.searchBtn.addEventListener('click', () => {
  const v = els.cityInput.value.trim();
  if(!v){ setStatus('Type a city name first.', true); return; }
  fetchWeather({ type: 'city', value: v });
});
els.cityInput.addEventListener('keydown', e => { if(e.key === 'Enter') els.searchBtn.click(); });

els.geoBtn.addEventListener('click', () => {
  if(!navigator.geolocation){ setStatus('Geolocation is not supported by this browser.', true); return; }
  setStatus('Finding your location…');
  navigator.geolocation.getCurrentPosition(
    pos => fetchWeather({ type: 'coords', value: { lat: pos.coords.latitude, lon: pos.coords.longitude } }),
    () => setStatus('Location access was denied — try searching a city instead.', true)
  );
});

/* ---- init ---- */
drawGraph([]);
drawSunArc(0.5, true);
loadHistory();
loadPinned();
setStatus('Enter a city, or press Locate to use your current position.', false, true);
