from __future__ import annotations

import concurrent.futures
import html as html_lib
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, jsonify, render_template_string, request

app = Flask(__name__, static_folder=None)

INDEX_HTML = '<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <meta name="description" content="Browse new, certified pre-owned, and used vehicle inventory with Peyton Gaskins at Jim Hudson Cadillac / Buick GMC in Columbia, South Carolina.">\n  <title>Peyton Gaskins | Jim Hudson Cadillac / Buick GMC</title>\n  <link rel="preconnect" href="https://vehicle-images.carscommerce.inc">\n  <link rel="stylesheet" href="/assets/styles.css">\n</head>\n<body>\n  <header class="site-header">\n    <div class="shell nav-wrap">\n      <a class="brand" href="#top" aria-label="Peyton Gaskins inventory home">\n        <span class="brand-name">Peyton Gaskins</span>\n        <span class="brand-sub">Jim Hudson Cadillac / Buick GMC</span>\n      </a>\n      <div class="header-actions">\n        <a class="plain-link" href="#inventory">Inventory</a>\n        <a class="button button-primary compact" href="tel:{{ person.phone_tel }}">Call {{ person.phone_display }}</a>\n      </div>\n    </div>\n  </header>\n\n  <main id="top">\n    <section class="hero">\n      <div class="shell hero-grid">\n        <div>\n          <p class="eyebrow">Columbia, South Carolina</p>\n          <h1>Find the right vehicle. Work directly with Peyton.</h1>\n          <p class="hero-copy">Browse current vehicles with the essentials: price, mileage, VIN and available dealership photos. Call or text Peyton to confirm availability and schedule an appointment.</p>\n          <div class="hero-actions">\n            <a class="button button-primary" href="#inventory">Browse Inventory</a>\n            <a class="button button-secondary" href="sms:{{ person.phone_tel }}?body=Hi%20Peyton%2C%20I%27m%20interested%20in%20a%20vehicle%20I%20saw%20on%20your%20website.">Text Peyton</a>\n          </div>\n        </div>\n        <aside class="contact-card">\n          <p class="contact-name">{{ person.name }}</p>\n          <p>{{ person.title }}</p>\n          <p>{{ person.dealership }}</p>\n          <a class="phone" href="tel:{{ person.phone_tel }}">{{ person.phone_display }}</a>\n          <p class="contact-copy">Contact me directly for additional information, vehicle videos, pricing details, availability, or to schedule an appointment. Please ask for Peyton Gaskins when calling or visiting the dealership.</p>\n        </aside>\n      </div>\n    </section>\n\n    <section class="inventory-section" id="inventory">\n      <div class="shell">\n        <div class="section-heading">\n          <div>\n            <p class="eyebrow">Current Inventory</p>\n            <h2>New and Pre-Owned Vehicles</h2>\n          </div>\n          <p class="inventory-status" id="inventoryStatus">Loading current inventory...</p>\n        </div>\n\n        <div class="filters" aria-label="Inventory filters">\n          <label class="search-field">\n            <span>Search</span>\n            <input id="searchInput" type="search" placeholder="Year, make, model, stock or VIN" autocomplete="off">\n          </label>\n          <label>\n            <span>Type</span>\n            <select id="conditionFilter">\n              <option value="all">All Inventory</option>\n              <option value="new">New</option>\n              <option value="certified">Certified Pre-Owned</option>\n              <option value="preowned">Pre-Owned / Used</option>\n            </select>\n          </label>\n          <label>\n            <span>Make</span>\n            <select id="makeFilter"><option value="all">All Makes</option></select>\n          </label>\n          <label>\n            <span>Maximum Price</span>\n            <select id="priceFilter">\n              <option value="all">Any Price</option>\n              <option value="30000">$30,000</option>\n              <option value="40000">$40,000</option>\n              <option value="50000">$50,000</option>\n              <option value="60000">$60,000</option>\n              <option value="75000">$75,000</option>\n              <option value="100000">$100,000</option>\n            </select>\n          </label>\n          <label>\n            <span>Sort</span>\n            <select id="sortFilter">\n              <option value="recommended">Recommended</option>\n              <option value="price-low">Price: Low to High</option>\n              <option value="price-high">Price: High to Low</option>\n              <option value="year-new">Newest Year</option>\n              <option value="miles-low">Mileage: Low to High</option>\n            </select>\n          </label>\n        </div>\n\n        <div class="inventory-summary" id="inventorySummary"></div>\n        <div class="vehicle-grid" id="vehicleGrid" aria-live="polite"></div>\n        <div class="load-more-wrap hidden" id="loadMoreWrap"><button class="button button-secondary" type="button" id="loadMoreButton">Load More Vehicles</button></div>\n        <div class="empty-state hidden" id="emptyState">\n          <h3>No vehicles match those filters.</h3>\n          <p>Change your filters or contact Peyton directly for help finding a vehicle.</p>\n          <a class="button button-primary" href="tel:{{ person.phone_tel }}">Call {{ person.phone_display }}</a>\n        </div>\n      </div>\n    </section>\n\n    <section class="certification-section">\n      <div class="shell">\n        <div class="section-heading simple">\n          <div>\n            <p class="eyebrow">Certification</p>\n            <h2>Certified Pre-Owned Coverage</h2>\n          </div>\n        </div>\n        <div class="cert-grid">\n          <article>\n            <h3>CarBravo Certified Pre-Owned</h3>\n            <p>12-month / 12,000-mile warranty.</p>\n          </article>\n          <article>\n            <h3>Cadillac Certified Pre-Owned</h3>\n            <p>12-month unlimited-mile bumper-to-bumper warranty.</p>\n          </article>\n        </div>\n        <p class="fine-print">Warranty coverage shown is based on the certification information provided for this site. Contact Peyton for vehicle eligibility, complete warranty terms, exclusions and current availability.</p>\n      </div>\n    </section>\n\n    <section class="contact-section" id="contact">\n      <div class="shell contact-layout">\n        <div>\n          <p class="eyebrow">Work With Peyton</p>\n          <h2>Questions about a vehicle?</h2>\n          <p>Contact me directly for additional information, vehicle videos, pricing details, availability, trade questions, or to schedule an appointment.</p>\n        </div>\n        <div class="contact-actions">\n          <a class="button button-primary" href="tel:{{ person.phone_tel }}">Call {{ person.phone_display }}</a>\n          <a class="button button-secondary light" href="sms:{{ person.phone_tel }}?body=Hi%20Peyton%2C%20I%27d%20like%20more%20information%20about%20a%20vehicle.">Send a Text</a>\n          <p>{{ person.address }}</p>\n          <p>Please ask for Peyton Gaskins when you call or visit.</p>\n        </div>\n      </div>\n    </section>\n  </main>\n\n  <footer>\n    <div class="shell footer-wrap">\n      <p>Peyton Gaskins | Jim Hudson Cadillac / Buick GMC</p>\n      <p>Vehicle information, price and availability are subject to change. Contact Peyton to confirm details before visiting.</p>\n    </div>\n  </footer>\n\n  <template id="vehicleTemplate">\n    <article class="vehicle-card">\n      <div class="vehicle-image-wrap">\n        <img class="vehicle-image" alt="" loading="lazy">\n        <span class="condition-badge"></span>\n      </div>\n      <div class="vehicle-body">\n        <p class="vehicle-dealer"></p>\n        <h3 class="vehicle-title"></h3>\n        <p class="vehicle-price"></p>\n        <div class="vehicle-meta"></div>\n        <p class="warranty-line hidden"></p>\n        <div class="vehicle-actions">\n          <a class="button button-primary call-button">Call Peyton</a>\n          <a class="button button-secondary text-link">Text Peyton</a>\n        </div>\n        <p class="availability-line">Contact Peyton to confirm availability or schedule an appointment.</p>\n        <a class="detail-link original-link" target="_blank" rel="noopener">Original dealer listing</a>\n      </div>\n    </article>\n  </template>\n\n  <script>\n    window.SALES_CONTACT = {\n      name: {{ person.name|tojson }},\n      phoneDisplay: {{ person.phone_display|tojson }},\n      phoneTel: {{ person.phone_tel|tojson }}\n    };\n  </script>\n  <script src="/assets/app.js" defer></script>\n</body>\n</html>\n'
STYLES_CSS = ':root {\n  --ink: #16202a;\n  --muted: #5e6872;\n  --line: #d9dee3;\n  --soft: #f4f6f8;\n  --navy: #10283f;\n  --navy-dark: #0b1b2a;\n  --white: #ffffff;\n  --max: 1240px;\n  --radius: 10px;\n}\n\n* { box-sizing: border-box; }\nhtml { scroll-behavior: smooth; }\nbody {\n  margin: 0;\n  font-family: Arial, Helvetica, sans-serif;\n  color: var(--ink);\n  background: var(--white);\n  line-height: 1.5;\n}\na { color: inherit; }\n.shell { width: min(var(--max), calc(100% - 40px)); margin: 0 auto; }\n.site-header {\n  position: sticky;\n  top: 0;\n  z-index: 20;\n  background: rgba(255,255,255,.97);\n  border-bottom: 1px solid var(--line);\n}\n.nav-wrap { min-height: 72px; display: flex; align-items: center; justify-content: space-between; gap: 24px; }\n.brand { text-decoration: none; display: flex; flex-direction: column; }\n.brand-name { font-size: 18px; font-weight: 700; letter-spacing: .01em; }\n.brand-sub { color: var(--muted); font-size: 13px; }\n.header-actions { display: flex; align-items: center; gap: 18px; }\n.plain-link { text-decoration: none; font-weight: 700; font-size: 14px; }\n.button {\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  min-height: 46px;\n  padding: 0 20px;\n  border-radius: 6px;\n  border: 1px solid var(--navy);\n  font-weight: 700;\n  font-size: 14px;\n  text-decoration: none;\n  cursor: pointer;\n}\n.button.compact { min-height: 40px; padding: 0 16px; }\n.button-primary { background: var(--navy); color: var(--white); }\n.button-primary:hover { background: var(--navy-dark); }\n.button-secondary { background: var(--white); color: var(--navy); }\n.button-secondary:hover { background: var(--soft); }\n.button-secondary.light { border-color: var(--white); color: var(--white); background: transparent; }\n.hero { padding: 72px 0; background: linear-gradient(180deg, #f7f8fa, #fff); border-bottom: 1px solid var(--line); }\n.hero-grid { display: grid; grid-template-columns: 1.45fr .75fr; gap: 64px; align-items: center; }\n.eyebrow { margin: 0 0 10px; text-transform: uppercase; letter-spacing: .11em; font-size: 12px; font-weight: 700; color: var(--muted); }\nh1, h2, h3 { line-height: 1.12; margin-top: 0; }\nh1 { font-size: clamp(38px, 5vw, 64px); max-width: 850px; margin-bottom: 22px; letter-spacing: -.035em; }\nh2 { font-size: clamp(28px, 3vw, 40px); margin-bottom: 10px; letter-spacing: -.02em; }\nh3 { font-size: 20px; margin-bottom: 8px; }\n.hero-copy { max-width: 760px; font-size: 18px; color: var(--muted); margin: 0 0 28px; }\n.hero-actions, .vehicle-actions { display: flex; flex-wrap: wrap; gap: 10px; }\n.contact-card { border: 1px solid var(--line); border-radius: var(--radius); background: var(--white); padding: 30px; box-shadow: 0 8px 30px rgba(16,40,63,.07); }\n.contact-card p { margin: 4px 0; }\n.contact-name { font-size: 23px; font-weight: 700; }\n.phone { display: inline-block; margin: 14px 0; font-size: 24px; font-weight: 700; color: var(--navy); text-decoration: none; }\n.contact-copy { color: var(--muted); font-size: 14px; }\n.inventory-section { padding: 66px 0 84px; }\n.section-heading { display: flex; align-items: end; justify-content: space-between; gap: 30px; margin-bottom: 26px; }\n.section-heading.simple { margin-bottom: 22px; }\n.section-heading h2 { margin-bottom: 0; }\n.inventory-status { margin: 0; color: var(--muted); font-size: 13px; }\n.filters { display: grid; grid-template-columns: 2fr repeat(4, 1fr); gap: 12px; padding: 18px; background: var(--soft); border: 1px solid var(--line); border-radius: var(--radius); }\n.filters label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; font-weight: 700; color: var(--muted); }\n.filters input, .filters select { width: 100%; min-height: 44px; border: 1px solid #c8cfd6; border-radius: 5px; background: var(--white); color: var(--ink); padding: 0 12px; font-size: 14px; }\n.inventory-summary { min-height: 26px; margin: 18px 0; color: var(--muted); font-size: 14px; }\n.vehicle-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 22px; }\n.vehicle-card { border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; background: var(--white); display: flex; flex-direction: column; min-width: 0; }\n.vehicle-image-wrap { position: relative; aspect-ratio: 4 / 3; background: #eef1f4; overflow: hidden; }\n.vehicle-image { width: 100%; height: 100%; object-fit: cover; display: block; }\n.vehicle-image.is-empty { object-fit: contain; padding: 18%; opacity: .4; }\n.condition-badge { position: absolute; top: 12px; left: 12px; max-width: calc(100% - 24px); background: var(--navy); color: var(--white); padding: 6px 9px; border-radius: 4px; font-size: 11px; font-weight: 700; }\n.vehicle-body { padding: 20px; display: flex; flex-direction: column; flex: 1; }\n.vehicle-dealer { margin: 0 0 6px; color: var(--muted); font-size: 12px; font-weight: 700; }\n.vehicle-title { font-size: 21px; margin-bottom: 14px; }\n.vehicle-price { font-size: 25px; font-weight: 700; margin: 0 0 15px; }\n.price-label { display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px; }\n.vehicle-meta { border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); padding: 12px 0; margin-bottom: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; color: var(--muted); font-size: 12px; }\n.vehicle-meta span { overflow-wrap: anywhere; }\n.warranty-line { margin: 0 0 15px; font-size: 13px; font-weight: 700; }\n.vehicle-actions { margin-top: auto; }\n.vehicle-actions .button { flex: 1 1 130px; }\n.call-line { display: block; text-align: center; margin-top: 12px; color: var(--navy); font-size: 13px; font-weight: 700; text-decoration: none; }\n.empty-state { text-align: center; padding: 60px 20px; border: 1px solid var(--line); border-radius: var(--radius); }\n.hidden { display: none !important; }\n.certification-section { background: var(--soft); padding: 64px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }\n.cert-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }\n.cert-grid article { background: var(--white); padding: 26px; border: 1px solid var(--line); border-radius: var(--radius); }\n.cert-grid p { margin: 0; color: var(--muted); }\n.fine-print { color: var(--muted); font-size: 12px; margin: 18px 0 0; }\n.contact-section { background: var(--navy); color: var(--white); padding: 68px 0; }\n.contact-section .eyebrow { color: #b9c8d5; }\n.contact-layout { display: grid; grid-template-columns: 1.2fr .8fr; gap: 80px; align-items: center; }\n.contact-layout > div > p:not(.eyebrow) { color: #d4dde5; max-width: 700px; }\n.contact-actions { display: flex; flex-wrap: wrap; gap: 10px; }\n.contact-actions p { flex-basis: 100%; margin: 7px 0 0; font-size: 13px; }\nfooter { background: var(--navy-dark); color: #bcc8d1; padding: 28px 0; font-size: 12px; }\n.footer-wrap { display: flex; justify-content: space-between; gap: 30px; }\n.footer-wrap p { margin: 0; max-width: 660px; }\n.availability-line { margin: 12px 0 7px; color: var(--muted); font-size: 13px; }\n.original-link { display: inline-block; font-size: 12px; color: var(--muted); }\n@media (max-width: 980px) {\n  .hero-grid, .contact-layout { grid-template-columns: 1fr; gap: 36px; }\n  .filters { grid-template-columns: 1fr 1fr 1fr; }\n  .search-field { grid-column: span 2; }\n  .vehicle-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }\n}\n@media (max-width: 680px) {\n  .shell { width: min(100% - 24px, var(--max)); }\n  .site-header { position: static; }\n  .nav-wrap { min-height: 82px; }\n  .brand-sub, .plain-link { display: none; }\n  .hero { padding: 46px 0; }\n  h1 { font-size: 39px; }\n  .header-actions { gap: 8px; }\n  .filters { grid-template-columns: 1fr 1fr; }\n  .search-field { grid-column: 1 / -1; }\n  .vehicle-grid, .cert-grid { grid-template-columns: 1fr; }\n  .section-heading { align-items: start; flex-direction: column; gap: 8px; }\n  .footer-wrap { flex-direction: column; }\n}\n\n.load-more-wrap { text-align: center; margin: 28px 0 8px; }\n.load-more-wrap.hidden { display: none; }\n'
APP_JS = r'''const state = { all: [], filtered: [], visibleLimit: 60 };
const detailState = { active: 0, maxActive: 6, queue: [], queued: new Set(), completed: new Set() };
const $ = (id) => document.getElementById(id);

function money(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'Contact for Price';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}
function number(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return new Intl.NumberFormat('en-US').format(value);
}
function escapeSms(text) { return encodeURIComponent(text); }

function populateMakes() {
  const select = $('makeFilter');
  select.innerHTML = '<option value="all">All Makes</option>';
  const makes = [...new Set(state.all.map(v => v.make).filter(Boolean))].sort((a,b) => a.localeCompare(b));
  for (const make of makes) {
    const option = document.createElement('option');
    option.value = make.toLowerCase();
    option.textContent = make;
    select.appendChild(option);
  }
}

function applyFilters(resetLimit = true) {
  if (resetLimit) state.visibleLimit = 60;
  const q = $('searchInput').value.trim().toLowerCase();
  const condition = $('conditionFilter').value;
  const make = $('makeFilter').value;
  const maxPrice = $('priceFilter').value;
  const sort = $('sortFilter').value;

  let rows = state.all.filter(v => {
    const haystack = [v.title, v.make, v.model, v.trim, v.stock, v.vin, v.dealer].join(' ').toLowerCase();
    if (q && !haystack.includes(q)) return false;
    if (condition !== 'all' && v.condition !== condition) return false;
    if (make !== 'all' && String(v.make || '').toLowerCase() !== make) return false;
    if (maxPrice !== 'all' && v.price !== null && Number(v.price) > Number(maxPrice)) return false;
    if (maxPrice !== 'all' && v.price === null) return false;
    return true;
  });

  rows.sort((a,b) => {
    if (sort === 'price-low') return (a.price ?? Infinity) - (b.price ?? Infinity);
    if (sort === 'price-high') return (b.price ?? -1) - (a.price ?? -1);
    if (sort === 'year-new') return Number(b.year || 0) - Number(a.year || 0);
    if (sort === 'miles-low') return (a.mileage ?? Infinity) - (b.mileage ?? Infinity);
    const priority = { new: 0, certified: 1, preowned: 2 };
    return (priority[a.condition] ?? 9) - (priority[b.condition] ?? 9)
      || Number(b.year || 0) - Number(a.year || 0)
      || String(a.make || '').localeCompare(String(b.make || ''));
  });
  state.filtered = rows;
  renderVehicles();
}

function placeholderDataUrl() {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><rect width="800" height="600" fill="#eef1f4"/><text x="400" y="300" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="28" fill="#697580">Vehicle photo</text></svg>`;
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
}

function applyVehicleToCard(card, v) {
  if (!card) return;
  card.dataset.vin = v.vin || '';

  const img = card.querySelector('.vehicle-image');
  const imageUrl = v.image || (Array.isArray(v.images) && v.images.length ? v.images[0] : '');
  img.src = imageUrl || placeholderDataUrl();
  img.alt = v.title || 'Vehicle';
  img.classList.toggle('is-empty', !imageUrl);
  img.onerror = () => { img.onerror = null; img.src = placeholderDataUrl(); img.classList.add('is-empty'); };

  card.querySelector('.condition-badge').textContent = v.condition_label || 'Inventory';
  card.querySelector('.vehicle-dealer').textContent = v.dealer || '';
  card.querySelector('.vehicle-title').textContent = v.title || [v.year, v.make, v.model, v.trim].filter(Boolean).join(' ');

  const price = card.querySelector('.vehicle-price');
  price.innerHTML = v.price !== null
    ? `<span class="price-label">${v.price_label || 'Price'}</span>${money(v.price)}`
    : 'Contact for Price';

  const meta = card.querySelector('.vehicle-meta');
  const parts = [];
  parts.push(`<span>Mileage: ${v.mileage !== null && v.mileage !== undefined ? number(v.mileage) : 'Contact Peyton'}</span>`);
  if (v.vin) parts.push(`<span>VIN: ${v.vin}</span>`);
  meta.innerHTML = parts.join('');

  const warranty = card.querySelector('.warranty-line');
  warranty.textContent = v.warranty || '';
  warranty.classList.toggle('hidden', !v.warranty);

  const detail = card.querySelector('.detail-link');
  detail.href = v.url;
  const call = card.querySelector('.call-button');
  call.href = `tel:${window.SALES_CONTACT.phoneTel}`;
  const sms = card.querySelector('.text-link');
  const message = `Hi Peyton, I'm interested in ${v.title}${v.stock ? ` (stock ${v.stock})` : ''}${v.vin ? ` (VIN ${v.vin})` : ''}. Can you confirm availability and help me schedule an appointment?`;
  sms.href = `sms:${window.SALES_CONTACT.phoneTel}?body=${escapeSms(message)}`;
}

function needsDetail(v) {
  if (!v || !v.vin) return false;
  if (!v.image && !(Array.isArray(v.images) && v.images.length)) return true;
  if (v.price === null || v.price === undefined) return true;
  if (!v.stock) return true;
  if (v.condition !== 'new' && (v.mileage === null || v.mileage === undefined)) return true;
  return false;
}

function queueVehicleDetail(v) {
  if (!needsDetail(v) || detailState.completed.has(v.vin) || detailState.queued.has(v.vin)) return;
  detailState.queue.push(v);
  detailState.queued.add(v.vin);
  pumpVehicleDetails();
}

function pumpVehicleDetails() {
  while (detailState.active < detailState.maxActive && detailState.queue.length) {
    const v = detailState.queue.shift();
    detailState.queued.delete(v.vin);
    detailState.active += 1;
    fetch(`/api/vehicle-detail?vin=${encodeURIComponent(v.vin)}`, { headers: { 'Accept': 'application/json' } })
      .then(response => response.ok ? response.json() : null)
      .then(data => {
        if (!data || !data.vehicle) return;
        const updated = data.vehicle;
        const target = state.all.find(row => row.vin === updated.vin);
        if (target) Object.assign(target, updated);
        const filteredTarget = state.filtered.find(row => row.vin === updated.vin);
        if (filteredTarget && filteredTarget !== target) Object.assign(filteredTarget, updated);
        const card = document.querySelector(`.vehicle-card[data-vin="${updated.vin}"]`);
        applyVehicleToCard(card, updated);
      })
      .catch(() => {})
      .finally(() => {
        detailState.completed.add(v.vin);
        detailState.active -= 1;
        pumpVehicleDetails();
      });
  }
}

function renderVehicles() {
  const grid = $('vehicleGrid');
  const template = $('vehicleTemplate');
  const empty = $('emptyState');
  const loadMoreWrap = $('loadMoreWrap');
  grid.innerHTML = '';

  const visibleRows = state.filtered.slice(0, state.visibleLimit);
  const shown = visibleRows.length;
  const total = state.filtered.length;
  $('inventorySummary').textContent = total === 0 ? '0 vehicles shown' : `Showing ${shown} of ${total} vehicles`;
  empty.classList.toggle('hidden', total !== 0);
  loadMoreWrap.classList.toggle('hidden', shown >= total || total === 0);

  for (const v of visibleRows) {
    const fragment = template.content.cloneNode(true);
    const card = fragment.querySelector('.vehicle-card');
    applyVehicleToCard(card, v);
    grid.appendChild(fragment);
    queueVehicleDetail(v);
  }
}

async function loadInventory() {
  const status = $('inventoryStatus');
  try {
    const response = await fetch('/api/inventory', { headers: { 'Accept': 'application/json' } });
    if (!response.ok) throw new Error('Inventory request failed');
    const data = await response.json();
    state.all = Array.isArray(data.vehicles) ? data.vehicles : [];
    populateMakes();
    applyFilters(true);

    if (data.updated_at) {
      const date = new Date(data.updated_at);
      status.textContent = `Inventory checked ${date.toLocaleString()}. Contact Peyton to confirm availability.`;
    } else {
      status.textContent = 'Contact Peyton to confirm current availability.';
    }
    if (data.errors && data.errors.length) {
      status.textContent += ' Some dealership details may be temporarily unavailable.';
    }
  } catch (error) {
    status.textContent = 'Current inventory could not be loaded. Contact Peyton directly for availability.';
    state.all = [];
    state.filtered = [];
    renderVehicles();
  }
}

['searchInput','conditionFilter','makeFilter','priceFilter','sortFilter'].forEach(id => {
  $(id).addEventListener(id === 'searchInput' ? 'input' : 'change', () => applyFilters(true));
});
$('loadMoreButton').addEventListener('click', () => {
  state.visibleLimit += 60;
  renderVehicles();
});
loadInventory();
'''

PERSON = {
    "name": "Peyton Gaskins",
    "title": "Sales Associate",
    "phone_display": "803-542-1353",
    "phone_tel": "+18035421353",
    "dealership": "Jim Hudson Cadillac / Buick GMC",
    "address": "4035 Kaiser Hill Rd, Columbia, SC 29203",
}

SOURCES = [
    {
        "dealer": "Jim Hudson Buick GMC",
        "domain": "https://www.jimhudsongm.com",
        "sitemap": "/dealer-inspire-inventory/inventory_sitemap",
    },
    {
        "dealer": "Jim Hudson Cadillac",
        "domain": "https://www.jimhudsoncadillac.com",
        "sitemap": "/dealer-inspire-inventory/inventory_sitemap",
    },
]

VIN_RE = re.compile(r"[A-HJ-NPR-Z0-9]{17}", re.I)
VEHICLE_URL_RE = re.compile(
    r"https?://[^/\s<>\"']+/inventory/(?:new|certified-used|used)-.*?-[A-HJ-NPR-Z0-9]{17}/",
    re.I,
)
SITEMAP_SLUG_RE = re.compile(
    r"^(?P<condition>new|certified-used|used)-(?P<body>.+)-(?P<vin>[A-HJ-NPR-Z0-9]{17})$",
    re.I,
)
CACHE_TTL_SECONDS = int(os.getenv("INVENTORY_CACHE_SECONDS", "1800"))
DIRECT_SITEMAP_TIMEOUT_SECONDS = int(os.getenv("INVENTORY_DIRECT_TIMEOUT", "7"))
READER_TIMEOUT_SECONDS = int(os.getenv("INVENTORY_READER_TIMEOUT", "18"))
DETAIL_TIMEOUT_SECONDS = int(os.getenv("INVENTORY_DETAIL_TIMEOUT", "9"))
MAX_LISTING_PAGES = int(os.getenv("INVENTORY_MAX_LISTING_PAGES", "100"))
DETAIL_WORKERS = int(os.getenv("INVENTORY_DETAIL_WORKERS", "12"))

_cache_lock = threading.Lock()
_cache = {"timestamp": 0.0, "payload": None}


@dataclass
class Vehicle:
    title: str
    year: str
    make: str
    model: str
    trim: str
    condition: str
    condition_label: str
    warranty: str
    price: int | None
    price_label: str
    mileage: int | None
    stock: str
    vin: str
    image: str
    url: str
    dealer: str
    source_domain: str
    images: list[str] = field(default_factory=list)


MAKE_FORMAT = {
    "gmc": "GMC", "bmw": "BMW", "audi": "Audi", "ram": "RAM", "mini": "MINI",
    "acura": "Acura", "buick": "Buick", "cadillac": "Cadillac", "chevrolet": "Chevrolet",
    "chrysler": "Chrysler", "dodge": "Dodge", "ford": "Ford", "genesis": "Genesis",
    "honda": "Honda", "hyundai": "Hyundai", "ineos": "INEOS", "infiniti": "INFINITI",
    "jeep": "Jeep", "kia": "Kia", "lexus": "Lexus", "lincoln": "Lincoln",
    "mazda": "Mazda", "mitsubishi": "Mitsubishi", "nissan": "Nissan", "porsche": "Porsche",
    "subaru": "Subaru", "tesla": "Tesla", "toyota": "Toyota", "volkswagen": "Volkswagen",
    "volvo": "Volvo", "fiat": "FIAT",
}
MULTIWORD_MAKES = {
    ("land", "rover"): "Land Rover",
    ("mercedes", "benz"): "Mercedes-Benz",
    ("alfa", "romeo"): "Alfa Romeo",
    ("aston", "martin"): "Aston Martin",
    ("rolls", "royce"): "Rolls-Royce",
}
ACRONYM_WORDS = {
    "awd": "AWD", "fwd": "FWD", "rwd": "RWD", "4wd": "4WD", "hd": "HD", "at4": "AT4", "at4x": "AT4X",
    "ev": "EV", "gx": "GX", "rx": "RX", "nx": "NX", "lx": "LX", "es": "ES",
    "is": "IS", "tx": "TX", "ct4": "CT4", "ct5": "CT5", "xt4": "XT4", "xt5": "XT5",
    "xt6": "XT6", "lyriq": "LYRIQ", "optiq": "OPTIQ", "vistiq": "VISTIQ",
    "suv": "SUV", "drw": "DRW", "sr5": "SR5", "trd": "TRD", "rt": "R/T",
}


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/xml,text/xml,text/html;q=0.9,*/*;q=0.8",
    })
    return s


def pretty_word(word: str) -> str:
    low = word.lower()
    if low in ACRONYM_WORDS:
        return ACRONYM_WORDS[low]
    if re.fullmatch(r"\d+(?:\.\d+)?[a-z]?", low):
        return low.upper()
    return word[:1].upper() + word[1:]


def parse_make(tokens: list[str]) -> tuple[str, int]:
    lowered = [t.lower() for t in tokens]
    if len(lowered) >= 2 and tuple(lowered[:2]) in MULTIWORD_MAKES:
        return MULTIWORD_MAKES[tuple(lowered[:2])], 2
    if not lowered:
        return "", 0
    return MAKE_FORMAT.get(lowered[0], pretty_word(tokens[0])), 1


EXTRA_TITLE_PHRASES = [
    r"front wheel drive", r"rear wheel drive", r"all wheel drive", r"four wheel drive",
    r"4 wheel drive", r"2 wheel drive", r"crew cab", r"double cab", r"extended cab",
    r"regular cab", r"quad cab", r"supercrew", r"super cab", r"mega cab",
    r"extended wheelbase", r"short wheelbase", r"sport utility", r"4 dr", r"2 dr",
    r"awd", r"fwd", r"rwd", r"4wd", r"2wd",
]


def clean_display_title(title: str) -> str:
    text = html_lib.unescape(title or "")
    text = re.sub(r"\s+", " ", text).strip(" -|,")
    text = re.sub(r"^(?:new|used|pre[- ]owned(?:\s*/\s*used)?|carbravo|certified pre[- ]owned|cadillac certified pre[- ]owned)\s+", "", text, flags=re.I)
    text = re.sub(r"\s+(?:MSRP|Internet Price|Sale Price|Final Price|Market Value)\s*\$.*$", "", text, flags=re.I)
    for phrase in EXTRA_TITLE_PHRASES:
        text = re.sub(rf"\b{phrase}\b", " ", text, flags=re.I)
    # Dealer slugs often end with generic body-style words after drivetrain/cab wording.
    # Preserve Hummer EV SUV because SUV is part of that model name.
    if not re.search(r"\bHummer EV SUV$", text, flags=re.I):
        text = re.sub(r"\s+SUV$", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" -|,")
    # Collapse adjacent duplicates that can remain after drivetrain words are removed.
    text = re.sub(r"\b([A-Za-z0-9.]+)\s+\1\b", r"\1", text, flags=re.I)
    return text


def humanize_vehicle_body(body: str) -> tuple[str, str, str, str, str]:
    body = unquote(body).replace("\\_", "-").replace("_", "-")
    raw_tokens = [t for t in body.split("-") if t]
    if not raw_tokens:
        return "", "", "", "", ""
    year = raw_tokens[0] if re.fullmatch(r"(?:19|20)\d{2}", raw_tokens[0]) else ""
    remaining = raw_tokens[1:] if year else raw_tokens
    make, used = parse_make(remaining)
    descriptor_tokens = remaining[used:]
    descriptor = " ".join(pretty_word(t) for t in descriptor_tokens)
    raw_title = " ".join(x for x in (year, make, descriptor) if x)
    core_title = clean_display_title(raw_title)

    # Model/trim are best-effort search fields. The customer-facing title is the cleaned title above.
    after_make = core_title
    prefix = " ".join(x for x in (year, make) if x).strip()
    if prefix and after_make.lower().startswith(prefix.lower()):
        after_make = after_make[len(prefix):].strip()
    clean_tokens = after_make.split()
    model = " ".join(clean_tokens[:2]) if clean_tokens else ""
    trim = " ".join(clean_tokens[2:]) if len(clean_tokens) > 2 else ""
    return year, make, model, trim, core_title


def source_preference(vehicle: Vehicle) -> int:
    make = vehicle.make.lower()
    domain = vehicle.source_domain.lower()
    score = 1
    if make == "cadillac" and "jimhudsoncadillac.com" in domain:
        score += 5
    if make in {"buick", "gmc"} and "jimhudsongm.com" in domain:
        score += 5
    if vehicle.condition == "certified":
        score += 2
    return score


def vehicle_from_url(url: str, source: dict) -> Vehicle | None:
    clean_url = html_lib.unescape(url.strip()).split("?")[0]
    path = unquote(urlparse(clean_url).path).rstrip("/")
    slug = path.split("/")[-1]
    match = SITEMAP_SLUG_RE.match(slug)
    if not match:
        return None

    raw_condition = match.group("condition").lower()
    body = match.group("body")
    vin = match.group("vin").upper()
    year, make, model, trim, core_title = humanize_vehicle_body(body)

    if raw_condition == "new":
        condition, condition_label, prefix, warranty = "new", "New", "New", ""
    elif raw_condition == "certified-used":
        condition, condition_label, prefix = "certified", "Certified Pre-Owned", "Certified Pre-Owned"
        if make.lower() == "cadillac" and "jimhudsoncadillac.com" in source["domain"].lower():
            condition_label = "Cadillac Certified Pre-Owned"
            warranty = "12-month unlimited-mile bumper-to-bumper warranty"
        else:
            warranty = ""
    else:
        condition, condition_label, prefix, warranty = "preowned", "Pre-Owned / Used", "Pre-Owned", ""

    dealer = source["dealer"]
    if make.lower() == "cadillac":
        dealer = "Jim Hudson Cadillac"
    elif make.lower() in {"buick", "gmc"}:
        dealer = "Jim Hudson Buick GMC"

    return Vehicle(
        title=core_title,
        year=year,
        make=make,
        model=model,
        trim=trim,
        condition=condition,
        condition_label=condition_label,
        warranty=warranty,
        price=None,
        price_label="Contact for Price",
        mileage=None,
        stock="",
        vin=vin,
        image="",
        url=clean_url,
        dealer=dealer,
        source_domain=source["domain"],
        images=[],
    )


def extract_inventory_urls(text: str) -> list[str]:
    text = html_lib.unescape(text or "")
    urls: list[str] = []
    seen: set[str] = set()
    for match in VEHICLE_URL_RE.finditer(text):
        url = match.group(0).replace("\\\\_", "_").replace("\\_", "_")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def fetch_sitemap(source: dict) -> tuple[list[Vehicle], str, str | None]:
    sitemap_url = source["domain"] + source["sitemap"]
    s = session()
    attempts = [
        (sitemap_url, "dealer sitemap", DIRECT_SITEMAP_TIMEOUT_SECONDS),
        ("https://r.jina.ai/" + sitemap_url, "dealer sitemap reader fallback", READER_TIMEOUT_SECONDS),
    ]
    last_error = None
    for target, mode, timeout_seconds in attempts:
        try:
            response = s.get(target, timeout=timeout_seconds)
            response.raise_for_status()
            urls = extract_inventory_urls(response.text)
            if urls:
                vehicles = [v for v in (vehicle_from_url(url, source) for url in urls) if v is not None]
                if vehicles:
                    return vehicles, mode, None
            last_error = "no vehicle URLs found"
        except requests.RequestException as exc:
            last_error = type(exc).__name__
    return [], "unavailable", last_error


PRICE_PATTERNS = [
    ("Internet Price", re.compile(r"Internet Price\s*\$\s*([\d,]+)", re.I)),
    ("Sale Price", re.compile(r"Sale Price\s*\$\s*([\d,]+)", re.I)),
    ("Final Price", re.compile(r"Final Price\s*\$\s*([\d,]+)", re.I)),
    ("Price", re.compile(r"(?:^|\s)Price\s*\$\s*([\d,]+)", re.I)),
    ("MSRP", re.compile(r"MSRP\s*\$\s*([\d,]+)", re.I)),
    ("Market Value", re.compile(r"Market Value\s*\$\s*([\d,]+)", re.I)),
]


def parse_int(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def find_price(text: str) -> tuple[int | None, str]:
    for label, pattern in PRICE_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return parse_int(match.group(1)), label
    return None, "Contact for Price"


def collect_image_urls(node) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    candidates = []
    for img in node.find_all("img") if hasattr(node, "find_all") else []:
        for attr in ("data-src", "data-lazy-src", "data-original", "src"):
            if img.get(attr):
                candidates.append(img.get(attr))
        for attr in ("data-srcset", "srcset"):
            value = img.get(attr)
            if value:
                candidates.extend(part.strip().split(" ")[0] for part in value.split(","))
    if hasattr(node, "find_all"):
        for source in node.find_all("source"):
            value = source.get("srcset") or source.get("data-srcset")
            if value:
                candidates.extend(part.strip().split(" ")[0] for part in value.split(","))
        for meta in node.find_all("meta"):
            if (meta.get("property") or "").lower() in {"og:image", "og:image:url"} and meta.get("content"):
                candidates.append(meta.get("content"))
    raw_blob = str(node)
    candidates.extend(re.findall(r"https?://[^\s\"'<>]+", raw_blob))
    for raw in candidates:
        url = html_lib.unescape(str(raw or "")).strip()
        if not url or url.startswith("data:") or not url.startswith(("http://", "https://")):
            continue
        low = url.lower()
        if not any(host in low for host in ("vehicle-images.carscommerce.inc", "vini.gm.com", "cgi.gmc.com", "images.cars.com")):
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def title_from_node(node, fallback: str) -> str:
    if hasattr(node, "find_all"):
        for tag in node.find_all(["h1", "h2", "h3", "h4"]):
            text = " ".join(tag.stripped_strings)
            if re.search(r"\b(?:19|20)\d{2}\b", text):
                return clean_display_title(text)
    return clean_display_title(fallback)


def detail_vehicle_from_html(html: str, base: Vehicle) -> Vehicle:
    soup = BeautifulSoup(html or "", "html.parser")
    text = " ".join(soup.stripped_strings)
    title = title_from_node(soup, base.title)
    vin_match = VIN_RE.search(text)
    stock_match = re.search(r"\bStock\s*:?\s*([A-Z0-9-]{2,20})\b", text, re.I)
    mileage_match = re.search(r"\b(?:Mileage|Odometer)\s*:?\s*([\d,]{1,10})\s*(?:miles?)?\b", text, re.I)
    price, price_label = find_price(text)
    images = collect_image_urls(soup)

    # Keep year/make from the sitemap URL, but improve model/trim search text from the shorter page heading.
    short = clean_display_title(title)
    after_prefix = short
    prefix = " ".join(x for x in (base.year, base.make) if x).strip()
    if prefix and after_prefix.lower().startswith(prefix.lower()):
        after_prefix = after_prefix[len(prefix):].strip()
    tokens = after_prefix.split()
    model = " ".join(tokens[:2]) if tokens else base.model
    trim = " ".join(tokens[2:]) if len(tokens) > 2 else (base.trim if len(tokens) < 2 else "")

    return Vehicle(
        title=short or base.title,
        year=base.year,
        make=base.make,
        model=model or base.model,
        trim=trim,
        condition=base.condition,
        condition_label=base.condition_label,
        warranty=base.warranty,
        price=price,
        price_label=price_label if price is not None else base.price_label,
        mileage=parse_int(mileage_match.group(1)) if mileage_match else None,
        stock=stock_match.group(1).upper() if stock_match else "",
        vin=(vin_match.group(0).upper() if vin_match else base.vin),
        image=images[0] if images else "",
        url=base.url,
        dealer=base.dealer,
        source_domain=base.source_domain,
        images=images,
    )


def fetch_vehicle_detail(vehicle: Vehicle) -> Vehicle:
    s = session()
    attempts = [
        (vehicle.url, DETAIL_TIMEOUT_SECONDS),
        ("https://r.jina.ai/" + vehicle.url, READER_TIMEOUT_SECONDS),
    ]
    for target, timeout_seconds in attempts:
        try:
            response = s.get(target, timeout=timeout_seconds)
            response.raise_for_status()
            detail = detail_vehicle_from_html(response.text, vehicle)
            if detail.image or detail.price is not None or detail.stock or detail.mileage is not None or detail.title != vehicle.title:
                return detail
        except requests.RequestException:
            continue
    return vehicle


def card_vehicle_from_anchor(anchor, source: dict) -> Vehicle | None:
    href = anchor.get("href") or ""
    if "/inventory/" not in href:
        return None
    if href.startswith("/"):
        href = source["domain"] + href
    base = vehicle_from_url(href, source)
    if base is None:
        return None

    card = anchor
    for parent in anchor.parents:
        card = parent
        text = " ".join(parent.stripped_strings)
        if base.vin in text or re.search(r"\bVIN\s*:?", text, re.I):
            break
        if getattr(parent, "name", "") in {"body", "html"}:
            card = anchor.parent or anchor
            break

    text = " ".join(card.stripped_strings) if hasattr(card, "stripped_strings") else ""
    title = title_from_node(card, base.title)
    vin_match = VIN_RE.search(text)
    stock_match = re.search(r"\bStock\s*:?\s*([A-Z0-9-]{2,20})\b", text, re.I)
    mileage_match = re.search(r"\b(?:Mileage|Odometer)\s*:?\s*([\d,]{1,10})\s*(?:miles?)?\b", text, re.I)
    price, price_label = find_price(text)
    images = collect_image_urls(card)

    return Vehicle(
        title=title or base.title,
        year=base.year,
        make=base.make,
        model=base.model,
        trim=base.trim,
        condition=base.condition,
        condition_label=base.condition_label,
        warranty=base.warranty,
        price=price,
        price_label=price_label if price is not None else base.price_label,
        mileage=parse_int(mileage_match.group(1)) if mileage_match else None,
        stock=stock_match.group(1).upper() if stock_match else "",
        vin=(vin_match.group(0).upper() if vin_match else base.vin),
        image=images[0] if images else "",
        url=base.url,
        dealer=base.dealer,
        source_domain=base.source_domain,
        images=images,
    )


def fetch_listing_feed(source: dict, path: str) -> tuple[list[Vehicle], str | None]:
    s = session()
    rows: list[Vehicle] = []
    seen_vins: set[str] = set()
    last_error = None
    for page in range(1, MAX_LISTING_PAGES + 1):
        url = f"{source['domain']}{path}?_p={page}"
        try:
            response = s.get(url, timeout=DETAIL_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.RequestException as exc:
            last_error = type(exc).__name__
            break
        soup = BeautifulSoup(response.text, "html.parser")
        page_rows: list[Vehicle] = []
        page_seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href") or ""
            if "/inventory/" not in href:
                continue
            vehicle = card_vehicle_from_anchor(anchor, source)
            if vehicle is None or not vehicle.vin or vehicle.vin in page_seen:
                continue
            page_seen.add(vehicle.vin)
            page_rows.append(vehicle)
        new_rows = [v for v in page_rows if v.vin not in seen_vins]
        if not new_rows:
            break
        rows.extend(new_rows)
        seen_vins.update(v.vin for v in new_rows)
    return rows, last_error


def merge_vehicle(existing: Vehicle, incoming: Vehicle) -> Vehicle:
    fields = asdict(existing)
    incoming_fields = asdict(incoming)

    # Fill missing card/detail information such as price, photo, mileage and stock.
    for key, value in incoming_fields.items():
        if key == "images":
            combined = []
            for image_url in list(fields.get("images") or []) + list(value or []):
                if image_url and image_url not in combined:
                    combined.append(image_url)
            fields["images"] = combined
            if not fields.get("image") and combined:
                fields["image"] = combined[0]
            continue
        if fields.get(key) in (None, "", 0) and value not in (None, "", 0):
            fields[key] = value

    incoming_title = clean_display_title(incoming.title)
    existing_title = clean_display_title(existing.title)
    if incoming_title and (len(incoming_title) < len(existing_title) or incoming.price is not None or incoming.image):
        fields["title"] = incoming_title

    priority = {"new": 1, "preowned": 2, "certified": 3}
    if priority.get(incoming.condition, 0) > priority.get(existing.condition, 0):
        fields["condition"] = incoming.condition
        fields["condition_label"] = incoming.condition_label
        fields["warranty"] = incoming.warranty

    # Prefer the brand's own Jim Hudson site when a VIN appears on both websites.
    if source_preference(incoming) > source_preference(existing):
        fields["url"] = incoming.url
        fields["dealer"] = incoming.dealer
        fields["source_domain"] = incoming.source_domain
        if incoming.condition == "certified":
            fields["condition"] = incoming.condition
            fields["condition_label"] = incoming.condition_label
            fields["warranty"] = incoming.warranty

    return Vehicle(**fields)


KNOWN_DETAILS = [
    Vehicle("Pre-Owned 2021 Chevrolet Express Cargo 2500 RWD 2500 Extended Wheelbase WT", "2021", "Chevrolet", "Express Cargo 2500", "RWD 2500 Extended Wheelbase WT", "preowned", "Pre-Owned", "", 14099, "$14,099", 148728, "B28956A", "1GCWGBFP2M1213442", "https://vehicle-images.carscommerce.inc/be95-110011505/1GCWGBFP2M1213442/9a5b91fed7015a023c70156417e9f04f.jpg", "https://www.jimhudsongm.com/inventory/used-2021-chevrolet-express-cargo-2500-rwd-2500-extended-wheelbase-wt-rear-wheel-drive-extended-wheelbase-1gcwgbfp2m1213442/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2017 Buick Encore Premium", "2017", "Buick", "Encore", "Premium", "preowned", "Pre-Owned", "", 14425, "$14,425", 93097, "B5692A", "KL4CJDSB3HB013352", "https://vehicle-images.carscommerce.inc/ccdf-110011505/KL4CJDSB3HB013352/030b160ecc5e342d836d3448ff3a1df5.jpg", "https://www.jimhudsongm.com/inventory/used-2017-buick-encore-premium-front-wheel-drive-suv-kl4cjdsb3hb013352/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2024 Volkswagen Jetta SE", "2024", "Volkswagen", "Jetta", "SE", "preowned", "Pre-Owned", "", 18087, "$18,087", 35380, "JB2235", "3VW7M7BU9RM049359", "https://vehicle-images.carscommerce.inc/3ffd-110011505/3VW7M7BU9RM049359/eb81525d72a40485ed5549524476ed0b.jpg", "https://www.jimhudsongm.com/inventory/used-2024-volkswagen-jetta-se-front-wheel-drive-sedan-4-dr-3vw7m7bu9rm049359/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2018 Toyota RAV4 LE", "2018", "Toyota", "RAV4", "LE", "preowned", "Pre-Owned", "", 18463, "$18,463", 140051, "B29561A", "2T3ZFREV6JW501549", "https://vehicle-images.carscommerce.inc/486a-110011505/2T3ZFREV6JW501549/245491b9ec3ed58b27354e4100329db8.jpg", "https://www.jimhudsongm.com/inventory/used-2018-toyota-rav4-le-front-wheel-drive-sport-utility-2t3zfrev6jw501549/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2013 GMC Sierra 1500 SLT", "2013", "GMC", "Sierra 1500", "SLT", "preowned", "Pre-Owned", "", 18590, "$18,590", 110934, "B6051B", "1GTR2WE74DZ333944", "https://vehicle-images.carscommerce.inc/dde8-110011505/1GTR2WE74DZ333944/36d695e2424fa647ab7dce1a53ca85dc.jpg", "https://www.jimhudsongm.com/inventory/used-2013-gmc-sierra-1500-slt-four-wheel-drive-extended-cab-1gtr2we74dz333944/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2016 Land Rover Range Rover 5.0L V8 Supercharged", "2016", "Land Rover", "Range Rover", "5.0L V8 Supercharged", "preowned", "Pre-Owned", "", 19068, "$19,068", 119418, "B29533B", "SALGS2EF3GA298137", "https://vehicle-images.carscommerce.inc/a596-110011505/SALGS2EF3GA298137/931b57790ff778b97a6504715284c6f7.jpg", "https://www.jimhudsongm.com/inventory/used-2016-land-rover-range-rover-5-0l-v8-supercharged-4-wheel-drive-sport-utility-salgs2ef3ga298137/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("CarBravo 2025 Hyundai Elantra SEL Convenience", "2025", "Hyundai", "Elantra", "SEL Convenience", "certified", "Certified Pre-Owned", "12-month / 12,000-mile warranty", 19863, "$19,863", 19863, "JB2251", "KMHLS4DG2SU906664", "https://vehicle-images.carscommerce.inc/fa1f-110011505/KMHLS4DG2SU906664/f9dae897c377d8a6f28e7f20830fae6a.jpg", "https://www.jimhudsongm.com/inventory/used-2025-hyundai-elantra-sel-convenience-front-wheel-drive-sedan-4-dr-kmhls4dg2su906664/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2020 Buick Envision Premium II", "2020", "Buick", "Envision", "Premium II", "preowned", "Pre-Owned", "", 23095, "$23,095", 62090, "JB2188A", "LRBFX4SX5LD147465", "https://vehicle-images.carscommerce.inc/ca9d-110011505/LRBFX4SX5LD147465/659840ea10f8ed8ee35ccaada5395fbb.jpg", "https://www.jimhudsongm.com/inventory/used-2020-buick-envision-premium-ii-all-wheel-drive-suv-lrbfx4sx5ld147465/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2023 Buick Encore GX Essence", "2023", "Buick", "Encore GX", "Essence", "preowned", "Pre-Owned", "", 23435, "$23,435", 35380, "B5958A", "KL4MMFSL3PB123364", "https://vehicle-images.carscommerce.inc/4ba5-110011505/KL4MMFSL3PB123364/1958cf2bfe195834ee3463335d3d5aed.jpg", "https://www.jimhudsongm.com/inventory/used-2023-buick-encore-gx-essence-front-wheel-drive-suv-kl4mmfsl3pb123364/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2022 Ford Edge ST-Line", "2022", "Ford", "Edge", "ST-Line", "preowned", "Pre-Owned", "", 23537, "$23,537", 37831, "B5747B", "2FMPK4J92NBA47139", "https://vehicle-images.carscommerce.inc/8faf-110011505/2FMPK4J92NBA47139/ca9ac5dba60125a377e5e84331be43e6.jpg", "https://www.jimhudsongm.com/inventory/used-2022-ford-edge-st-line-all-wheel-drive-sport-utility-2fmpk4j92nba47139/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2025 Mitsubishi Outlander SE", "2025", "Mitsubishi", "Outlander", "SE", "preowned", "Pre-Owned", "", 23987, "$23,987", 91567, "JB2238", "JA4J3VA81SZ028749", "https://vehicle-images.carscommerce.inc/6824-110011505/JA4J3VA81SZ028749/acc7d23f82f54a24024c3a398de555f9.jpg", "https://www.jimhudsongm.com/inventory/used-2025-mitsubishi-outlander-se-front-wheel-drive-suv-ja4j3va81sz028749/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2022 Volvo S60 Momentum", "2022", "Volvo", "S60", "Momentum", "preowned", "Pre-Owned", "", 24387, "$24,387", 55097, "B29537A", "7JRL12TZ8NG177685", "https://vehicle-images.carscommerce.inc/cd72-110011505/7JRL12TZ8NG177685/ab0cafc55ee891d194b41b80f19e3302.jpg", "https://www.jimhudsongm.com/inventory/used-2022-volvo-s60-momentum-all-wheel-drive-sedan-7jrl12tz8ng177685/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2017 Cadillac XTS Platinum", "2017", "Cadillac", "XTS", "Platinum", "preowned", "Pre-Owned", "", 25097, "$25,097", 73574, "B5788A", "2G61S5S34H9198637", "https://vehicle-images.carscommerce.inc/6b22-110011505/2G61S5S34H9198637/b7afe41609ae4829f35d528316a2a7a8.jpg", "https://www.jimhudsongm.com/inventory/used-2017-cadillac-xts-platinum-front-wheel-drive-sedan-2g61s5s34h9198637/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2023 Dodge Charger GT", "2023", "Dodge", "Charger", "GT", "preowned", "Pre-Owned", "", 26397, "$26,397", 65596, "JB2208A", "2C3CDXHG0PH554726", "https://vehicle-images.carscommerce.inc/1b21-110011505/2C3CDXHG0PH554726/7fb6dfc4a8b3b64341682ee6b2e580b9.jpg", "https://www.jimhudsongm.com/inventory/used-2023-dodge-charger-gt-rear-wheel-drive-sedan-2c3cdxhg0ph554726/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
    Vehicle("Pre-Owned 2025 Volkswagen Atlas 2.0T SE w/Technology", "2025", "Volkswagen", "Atlas", "2.0T SE w/Technology", "preowned", "Pre-Owned", "", 26582, "$26,582", 26582, "JB2239", "1V2WR2CA9SC501534", "https://vehicle-images.carscommerce.inc/c12a-110011505/1V2WR2CA9SC501534/9d50c30670fb5ec3398718a6a680cd40.jpg", "https://www.jimhudsongm.com/inventory/used-2025-volkswagen-atlas-2-0t-se-wtechnology-front-wheel-drive-sport-utility-1v2wr2ca9sc501534/", "Jim Hudson Buick GMC", "https://www.jimhudsongm.com"),
]

def refresh_inventory() -> dict:
    raw: list[Vehicle] = []
    errors: list[str] = []
    source_modes: dict[str, str] = {}

    # Sitemaps guarantee broad inventory coverage. Listing pages add price, mileage, stock and dealership photos in bulk.
    jobs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for source in SOURCES:
            jobs.append(("sitemap", source, None, executor.submit(fetch_sitemap, source)))
            jobs.append(("listing", source, "/new-vehicles/", executor.submit(fetch_listing_feed, source, "/new-vehicles/")))
            jobs.append(("listing", source, "/used-vehicles/", executor.submit(fetch_listing_feed, source, "/used-vehicles/")))

        for kind, source, path, future in jobs:
            try:
                if kind == "sitemap":
                    vehicles, mode, error = future.result()
                    raw.extend(vehicles)
                    source_modes[source["dealer"]] = mode
                    if error and not vehicles:
                        errors.append(f"{source['dealer']} inventory sitemap unavailable")
                else:
                    vehicles, error = future.result()
                    raw.extend(vehicles)
                    if error and not vehicles:
                        errors.append(f"{source['dealer']} {path.strip('/')} details temporarily unavailable")
            except Exception as exc:
                errors.append(f"{source['dealer']}: {type(exc).__name__}")

    deduped: dict[str, Vehicle] = {}
    for vehicle in raw:
        key = vehicle.vin or vehicle.url
        if key in deduped:
            deduped[key] = merge_vehicle(deduped[key], vehicle)
        else:
            deduped[key] = vehicle

    # Preserve verified snapshot details only for VINs that are still in the current live inventory.
    if deduped:
        for known in KNOWN_DETAILS:
            if known.vin and known.vin in deduped:
                deduped[known.vin] = merge_vehicle(deduped[known.vin], known)
    else:
        for known in KNOWN_DETAILS:
            deduped[known.vin or known.url] = known
        errors.append("Live inventory feeds unavailable; showing a limited emergency snapshot")

    # Missing card details are enriched lazily for visible vehicles through /api/vehicle-detail.
    # This keeps the full inventory list fast even when there are hundreds of vehicles.

    vehicles = list(deduped.values())
    for vehicle in vehicles:
        vehicle.title = clean_display_title(vehicle.title or " ".join(x for x in (vehicle.year, vehicle.make, vehicle.model, vehicle.trim) if x))
        if vehicle.images and not vehicle.image:
            vehicle.image = vehicle.images[0]
        if vehicle.image and vehicle.image not in vehicle.images:
            vehicle.images.insert(0, vehicle.image)

    condition_order = {"new": 0, "certified": 1, "preowned": 2}
    vehicles.sort(key=lambda v: (
        condition_order.get(v.condition, 9),
        -(int(v.year) if v.year.isdigit() else 0),
        v.make.lower(),
        v.title.lower(),
    ))

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(vehicles),
        "counts": {
            "new": sum(v.condition == "new" for v in vehicles),
            "certified": sum(v.condition == "certified" for v in vehicles),
            "preowned": sum(v.condition == "preowned" for v in vehicles),
        },
        "vehicles": [asdict(v) for v in vehicles],
        "errors": errors,
        "source_modes": source_modes,
        "rules": {
            "coverage": "all vehicles discovered from both dealer inventory sitemaps",
            "details": "price, mileage, stock and available dealership photos are merged from inventory cards and vehicle detail pages",
            "title_format": "Year + Make + Model + Trim only",
            "categories": ["New", "Certified Pre-Owned", "Pre-Owned / Used"],
            "deduplication": "VIN",
            "carbravo_warranty": "12-month / 12,000-mile warranty when CarBravo status is verified",
            "cadillac_cpo_warranty": "12-month unlimited-mile bumper-to-bumper warranty when Cadillac CPO status is verified",
        },
    }


def get_inventory(force: bool = False) -> dict:
    now = time.time()
    with _cache_lock:
        payload = _cache["payload"]
        if not force and payload is not None and now - _cache["timestamp"] < CACHE_TTL_SECONDS:
            return payload

    payload = refresh_inventory()
    with _cache_lock:
        _cache["payload"] = payload
        _cache["timestamp"] = time.time()
    return payload


@app.route("/assets/styles.css")
def styles_asset():
    return Response(STYLES_CSS, mimetype="text/css")


@app.route("/assets/app.js")
def js_asset():
    return Response(APP_JS, mimetype="application/javascript")


@app.route("/")
def home():
    return render_template_string(INDEX_HTML, person=PERSON)


@app.route("/api/inventory")
def inventory_api():
    force = request.args.get("force") == "1" and app.debug
    try:
        return jsonify(get_inventory(force=force))
    except Exception as exc:
        return jsonify({"updated_at": None, "count": 0, "counts": {}, "vehicles": [], "errors": [type(exc).__name__]}), 503


@app.route("/api/vehicle-detail")
def vehicle_detail_api():
    vin = (request.args.get("vin") or "").strip().upper()
    if not VIN_RE.fullmatch(vin):
        return jsonify({"error": "invalid VIN"}), 400

    payload = get_inventory()
    row = next((item for item in payload.get("vehicles", []) if item.get("vin") == vin), None)
    if row is None:
        return jsonify({"error": "vehicle not found"}), 404

    try:
        base = Vehicle(**row)
        enriched = merge_vehicle(base, fetch_vehicle_detail(base))
        enriched.title = clean_display_title(enriched.title)
        if enriched.images and not enriched.image:
            enriched.image = enriched.images[0]
        if enriched.image and enriched.image not in enriched.images:
            enriched.images.insert(0, enriched.image)
        updated = asdict(enriched)

        with _cache_lock:
            cached = _cache.get("payload")
            if cached:
                for i, item in enumerate(cached.get("vehicles", [])):
                    if item.get("vin") == vin:
                        cached["vehicles"][i] = updated
                        break
        return jsonify({"vehicle": updated})
    except Exception as exc:
        return jsonify({"vehicle": row, "warning": type(exc).__name__})


@app.route("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
