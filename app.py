from __future__ import annotations

import concurrent.futures
import json
import os
import re
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from flask import Flask, Response, jsonify, render_template_string, request

app = Flask(__name__, static_folder=None)

INDEX_HTML = '<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <meta name="description" content="Shop new Buick, GMC and Cadillac vehicles and qualifying pre-owned inventory with Peyton Gaskins at Jim Hudson Cadillac / Buick GMC in Columbia, South Carolina.">\n  <title>Peyton Gaskins | Jim Hudson Cadillac / Buick GMC</title>\n  <link rel="preconnect" href="https://vehicle-images.carscommerce.inc">\n  <link rel="stylesheet" href="/assets/styles.css">\n</head>\n<body>\n  <header class="site-header">\n    <div class="shell nav-wrap">\n      <a class="brand" href="#top" aria-label="Peyton Gaskins inventory home">\n        <span class="brand-name">Peyton Gaskins</span>\n        <span class="brand-sub">Jim Hudson Cadillac / Buick GMC</span>\n      </a>\n      <div class="header-actions">\n        <a class="plain-link" href="#inventory">Inventory</a>\n        <a class="button button-primary compact" href="tel:{{ person.phone_tel }}">Call {{ person.phone_display }}</a>\n      </div>\n    </div>\n  </header>\n\n  <main id="top">\n    <section class="hero">\n      <div class="shell hero-grid">\n        <div>\n          <p class="eyebrow">Columbia, South Carolina</p>\n          <h1>Find the right vehicle. Work directly with Peyton.</h1>\n          <p class="hero-copy">Browse new Buick, GMC and Cadillac vehicles along with qualifying pre-owned inventory from Jim Hudson Cadillac / Buick GMC.</p>\n          <div class="hero-actions">\n            <a class="button button-primary" href="#inventory">Browse Inventory</a>\n            <a class="button button-secondary" href="sms:{{ person.phone_tel }}?body=Hi%20Peyton%2C%20I%27m%20interested%20in%20a%20vehicle%20I%20saw%20on%20your%20website.">Text Peyton</a>\n          </div>\n        </div>\n        <aside class="contact-card">\n          <p class="contact-name">{{ person.name }}</p>\n          <p>{{ person.title }}</p>\n          <p>{{ person.dealership }}</p>\n          <a class="phone" href="tel:{{ person.phone_tel }}">{{ person.phone_display }}</a>\n          <p class="contact-copy">Contact me directly for additional information, vehicle videos, pricing details, availability, or to schedule an appointment. Please ask for Peyton Gaskins when calling or visiting the dealership.</p>\n        </aside>\n      </div>\n    </section>\n\n    <section class="inventory-section" id="inventory">\n      <div class="shell">\n        <div class="section-heading">\n          <div>\n            <p class="eyebrow">Current Inventory</p>\n            <h2>New and Pre-Owned Vehicles</h2>\n          </div>\n          <p class="inventory-status" id="inventoryStatus">Loading current inventory...</p>\n        </div>\n\n        <div class="filters" aria-label="Inventory filters">\n          <label class="search-field">\n            <span>Search</span>\n            <input id="searchInput" type="search" placeholder="Year, make, model, stock or VIN" autocomplete="off">\n          </label>\n          <label>\n            <span>Type</span>\n            <select id="conditionFilter">\n              <option value="all">All Inventory</option>\n              <option value="new">New</option>\n              <option value="certified">Certified Pre-Owned</option>\n              <option value="preowned">Pre-Owned</option>\n            </select>\n          </label>\n          <label>\n            <span>Make</span>\n            <select id="makeFilter"><option value="all">All Makes</option></select>\n          </label>\n          <label>\n            <span>Maximum Price</span>\n            <select id="priceFilter">\n              <option value="all">Any Price</option>\n              <option value="30000">$30,000</option>\n              <option value="40000">$40,000</option>\n              <option value="50000">$50,000</option>\n              <option value="60000">$60,000</option>\n              <option value="75000">$75,000</option>\n              <option value="100000">$100,000</option>\n            </select>\n          </label>\n          <label>\n            <span>Sort</span>\n            <select id="sortFilter">\n              <option value="recommended">Recommended</option>\n              <option value="price-low">Price: Low to High</option>\n              <option value="price-high">Price: High to Low</option>\n              <option value="year-new">Newest Year</option>\n              <option value="miles-low">Mileage: Low to High</option>\n            </select>\n          </label>\n        </div>\n\n        <div class="inventory-summary" id="inventorySummary"></div>\n        <div class="vehicle-grid" id="vehicleGrid" aria-live="polite"></div>\n        <div class="empty-state hidden" id="emptyState">\n          <h3>No vehicles match those filters.</h3>\n          <p>Change your filters or contact Peyton directly for help finding a vehicle.</p>\n          <a class="button button-primary" href="tel:{{ person.phone_tel }}">Call {{ person.phone_display }}</a>\n        </div>\n      </div>\n    </section>\n\n    <section class="certification-section">\n      <div class="shell">\n        <div class="section-heading simple">\n          <div>\n            <p class="eyebrow">Certification</p>\n            <h2>Certified Pre-Owned Coverage</h2>\n          </div>\n        </div>\n        <div class="cert-grid">\n          <article>\n            <h3>CarBravo Certified Pre-Owned</h3>\n            <p>12-month / 12,000-mile warranty.</p>\n          </article>\n          <article>\n            <h3>Cadillac Certified Pre-Owned</h3>\n            <p>12-month unlimited-mile bumper-to-bumper warranty.</p>\n          </article>\n        </div>\n        <p class="fine-print">Warranty coverage shown is based on the certification information provided for this site. Contact Peyton for vehicle eligibility, complete warranty terms, exclusions and current availability.</p>\n      </div>\n    </section>\n\n    <section class="contact-section" id="contact">\n      <div class="shell contact-layout">\n        <div>\n          <p class="eyebrow">Work With Peyton</p>\n          <h2>Questions about a vehicle?</h2>\n          <p>Contact me directly for additional information, vehicle videos, pricing details, availability, trade questions, or to schedule an appointment.</p>\n        </div>\n        <div class="contact-actions">\n          <a class="button button-primary" href="tel:{{ person.phone_tel }}">Call {{ person.phone_display }}</a>\n          <a class="button button-secondary light" href="sms:{{ person.phone_tel }}?body=Hi%20Peyton%2C%20I%27d%20like%20more%20information%20about%20a%20vehicle.">Send a Text</a>\n          <p>{{ person.address }}</p>\n          <p>Please ask for Peyton Gaskins when you call or visit.</p>\n        </div>\n      </div>\n    </section>\n  </main>\n\n  <footer>\n    <div class="shell footer-wrap">\n      <p>Peyton Gaskins | Jim Hudson Cadillac / Buick GMC</p>\n      <p>Vehicle information, price and availability are subject to change. Contact Peyton to confirm details before visiting.</p>\n    </div>\n  </footer>\n\n  <template id="vehicleTemplate">\n    <article class="vehicle-card">\n      <div class="vehicle-image-wrap">\n        <img class="vehicle-image" alt="" loading="lazy">\n        <span class="condition-badge"></span>\n      </div>\n      <div class="vehicle-body">\n        <p class="vehicle-dealer"></p>\n        <h3 class="vehicle-title"></h3>\n        <p class="vehicle-price"></p>\n        <div class="vehicle-meta"></div>\n        <p class="warranty-line hidden"></p>\n        <div class="vehicle-actions">\n          <a class="button button-primary detail-link" target="_blank" rel="noopener">View Vehicle</a>\n          <a class="button button-secondary text-link">Text Peyton</a>\n        </div>\n        <a class="call-line">Call Peyton: {{ person.phone_display }}</a>\n      </div>\n    </article>\n  </template>\n\n  <script>\n    window.SALES_CONTACT = {\n      name: {{ person.name|tojson }},\n      phoneDisplay: {{ person.phone_display|tojson }},\n      phoneTel: {{ person.phone_tel|tojson }}\n    };\n  </script>\n  <script src="/assets/app.js" defer></script>\n</body>\n</html>\n'
STYLES_CSS = ':root {\n  --ink: #16202a;\n  --muted: #5e6872;\n  --line: #d9dee3;\n  --soft: #f4f6f8;\n  --navy: #10283f;\n  --navy-dark: #0b1b2a;\n  --white: #ffffff;\n  --max: 1240px;\n  --radius: 10px;\n}\n\n* { box-sizing: border-box; }\nhtml { scroll-behavior: smooth; }\nbody {\n  margin: 0;\n  font-family: Arial, Helvetica, sans-serif;\n  color: var(--ink);\n  background: var(--white);\n  line-height: 1.5;\n}\na { color: inherit; }\n.shell { width: min(var(--max), calc(100% - 40px)); margin: 0 auto; }\n.site-header {\n  position: sticky;\n  top: 0;\n  z-index: 20;\n  background: rgba(255,255,255,.97);\n  border-bottom: 1px solid var(--line);\n}\n.nav-wrap { min-height: 72px; display: flex; align-items: center; justify-content: space-between; gap: 24px; }\n.brand { text-decoration: none; display: flex; flex-direction: column; }\n.brand-name { font-size: 18px; font-weight: 700; letter-spacing: .01em; }\n.brand-sub { color: var(--muted); font-size: 13px; }\n.header-actions { display: flex; align-items: center; gap: 18px; }\n.plain-link { text-decoration: none; font-weight: 700; font-size: 14px; }\n.button {\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  min-height: 46px;\n  padding: 0 20px;\n  border-radius: 6px;\n  border: 1px solid var(--navy);\n  font-weight: 700;\n  font-size: 14px;\n  text-decoration: none;\n  cursor: pointer;\n}\n.button.compact { min-height: 40px; padding: 0 16px; }\n.button-primary { background: var(--navy); color: var(--white); }\n.button-primary:hover { background: var(--navy-dark); }\n.button-secondary { background: var(--white); color: var(--navy); }\n.button-secondary:hover { background: var(--soft); }\n.button-secondary.light { border-color: var(--white); color: var(--white); background: transparent; }\n.hero { padding: 72px 0; background: linear-gradient(180deg, #f7f8fa, #fff); border-bottom: 1px solid var(--line); }\n.hero-grid { display: grid; grid-template-columns: 1.45fr .75fr; gap: 64px; align-items: center; }\n.eyebrow { margin: 0 0 10px; text-transform: uppercase; letter-spacing: .11em; font-size: 12px; font-weight: 700; color: var(--muted); }\nh1, h2, h3 { line-height: 1.12; margin-top: 0; }\nh1 { font-size: clamp(38px, 5vw, 64px); max-width: 850px; margin-bottom: 22px; letter-spacing: -.035em; }\nh2 { font-size: clamp(28px, 3vw, 40px); margin-bottom: 10px; letter-spacing: -.02em; }\nh3 { font-size: 20px; margin-bottom: 8px; }\n.hero-copy { max-width: 760px; font-size: 18px; color: var(--muted); margin: 0 0 28px; }\n.hero-actions, .vehicle-actions { display: flex; flex-wrap: wrap; gap: 10px; }\n.contact-card { border: 1px solid var(--line); border-radius: var(--radius); background: var(--white); padding: 30px; box-shadow: 0 8px 30px rgba(16,40,63,.07); }\n.contact-card p { margin: 4px 0; }\n.contact-name { font-size: 23px; font-weight: 700; }\n.phone { display: inline-block; margin: 14px 0; font-size: 24px; font-weight: 700; color: var(--navy); text-decoration: none; }\n.contact-copy { color: var(--muted); font-size: 14px; }\n.inventory-section { padding: 66px 0 84px; }\n.section-heading { display: flex; align-items: end; justify-content: space-between; gap: 30px; margin-bottom: 26px; }\n.section-heading.simple { margin-bottom: 22px; }\n.section-heading h2 { margin-bottom: 0; }\n.inventory-status { margin: 0; color: var(--muted); font-size: 13px; }\n.filters { display: grid; grid-template-columns: 2fr repeat(4, 1fr); gap: 12px; padding: 18px; background: var(--soft); border: 1px solid var(--line); border-radius: var(--radius); }\n.filters label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; font-weight: 700; color: var(--muted); }\n.filters input, .filters select { width: 100%; min-height: 44px; border: 1px solid #c8cfd6; border-radius: 5px; background: var(--white); color: var(--ink); padding: 0 12px; font-size: 14px; }\n.inventory-summary { min-height: 26px; margin: 18px 0; color: var(--muted); font-size: 14px; }\n.vehicle-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 22px; }\n.vehicle-card { border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; background: var(--white); display: flex; flex-direction: column; min-width: 0; }\n.vehicle-image-wrap { position: relative; aspect-ratio: 4 / 3; background: #eef1f4; overflow: hidden; }\n.vehicle-image { width: 100%; height: 100%; object-fit: cover; display: block; }\n.vehicle-image.is-empty { object-fit: contain; padding: 18%; opacity: .4; }\n.condition-badge { position: absolute; top: 12px; left: 12px; max-width: calc(100% - 24px); background: var(--navy); color: var(--white); padding: 6px 9px; border-radius: 4px; font-size: 11px; font-weight: 700; }\n.vehicle-body { padding: 20px; display: flex; flex-direction: column; flex: 1; }\n.vehicle-dealer { margin: 0 0 6px; color: var(--muted); font-size: 12px; font-weight: 700; }\n.vehicle-title { font-size: 21px; margin-bottom: 14px; }\n.vehicle-price { font-size: 25px; font-weight: 700; margin: 0 0 15px; }\n.price-label { display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px; }\n.vehicle-meta { border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); padding: 12px 0; margin-bottom: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; color: var(--muted); font-size: 12px; }\n.vehicle-meta span { overflow-wrap: anywhere; }\n.warranty-line { margin: 0 0 15px; font-size: 13px; font-weight: 700; }\n.vehicle-actions { margin-top: auto; }\n.vehicle-actions .button { flex: 1 1 130px; }\n.call-line { display: block; text-align: center; margin-top: 12px; color: var(--navy); font-size: 13px; font-weight: 700; text-decoration: none; }\n.empty-state { text-align: center; padding: 60px 20px; border: 1px solid var(--line); border-radius: var(--radius); }\n.hidden { display: none !important; }\n.certification-section { background: var(--soft); padding: 64px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }\n.cert-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }\n.cert-grid article { background: var(--white); padding: 26px; border: 1px solid var(--line); border-radius: var(--radius); }\n.cert-grid p { margin: 0; color: var(--muted); }\n.fine-print { color: var(--muted); font-size: 12px; margin: 18px 0 0; }\n.contact-section { background: var(--navy); color: var(--white); padding: 68px 0; }\n.contact-section .eyebrow { color: #b9c8d5; }\n.contact-layout { display: grid; grid-template-columns: 1.2fr .8fr; gap: 80px; align-items: center; }\n.contact-layout > div > p:not(.eyebrow) { color: #d4dde5; max-width: 700px; }\n.contact-actions { display: flex; flex-wrap: wrap; gap: 10px; }\n.contact-actions p { flex-basis: 100%; margin: 7px 0 0; font-size: 13px; }\nfooter { background: var(--navy-dark); color: #bcc8d1; padding: 28px 0; font-size: 12px; }\n.footer-wrap { display: flex; justify-content: space-between; gap: 30px; }\n.footer-wrap p { margin: 0; max-width: 660px; }\n@media (max-width: 980px) {\n  .hero-grid, .contact-layout { grid-template-columns: 1fr; gap: 36px; }\n  .filters { grid-template-columns: 1fr 1fr 1fr; }\n  .search-field { grid-column: span 2; }\n  .vehicle-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }\n}\n@media (max-width: 680px) {\n  .shell { width: min(100% - 24px, var(--max)); }\n  .site-header { position: static; }\n  .nav-wrap { min-height: 82px; }\n  .brand-sub, .plain-link { display: none; }\n  .hero { padding: 46px 0; }\n  h1 { font-size: 39px; }\n  .header-actions { gap: 8px; }\n  .filters { grid-template-columns: 1fr 1fr; }\n  .search-field { grid-column: 1 / -1; }\n  .vehicle-grid, .cert-grid { grid-template-columns: 1fr; }\n  .section-heading { align-items: start; flex-direction: column; gap: 8px; }\n  .footer-wrap { flex-direction: column; }\n}\n'
APP_JS = 'const state = { all: [], filtered: [] };\nconst $ = (id) => document.getElementById(id);\n\nfunction money(value) {\n  if (value === null || value === undefined || Number.isNaN(Number(value))) return \'Contact for Price\';\n  return new Intl.NumberFormat(\'en-US\', { style: \'currency\', currency: \'USD\', maximumFractionDigits: 0 }).format(value);\n}\nfunction number(value) {\n  if (value === null || value === undefined || Number.isNaN(Number(value))) return \'—\';\n  return new Intl.NumberFormat(\'en-US\').format(value);\n}\nfunction escapeSms(text) { return encodeURIComponent(text); }\n\nfunction populateMakes() {\n  const select = $(\'makeFilter\');\n  const makes = [...new Set(state.all.map(v => v.make).filter(Boolean))].sort((a,b) => a.localeCompare(b));\n  for (const make of makes) {\n    const option = document.createElement(\'option\');\n    option.value = make.toLowerCase();\n    option.textContent = make;\n    select.appendChild(option);\n  }\n}\n\nfunction applyFilters() {\n  const q = $(\'searchInput\').value.trim().toLowerCase();\n  const condition = $(\'conditionFilter\').value;\n  const make = $(\'makeFilter\').value;\n  const maxPrice = $(\'priceFilter\').value;\n  const sort = $(\'sortFilter\').value;\n\n  let rows = state.all.filter(v => {\n    const haystack = [v.title, v.make, v.model, v.trim, v.stock, v.vin, v.dealer].join(\' \').toLowerCase();\n    if (q && !haystack.includes(q)) return false;\n    if (condition !== \'all\' && v.condition !== condition) return false;\n    if (make !== \'all\' && String(v.make || \'\').toLowerCase() !== make) return false;\n    if (maxPrice !== \'all\' && v.price !== null && Number(v.price) > Number(maxPrice)) return false;\n    if (maxPrice !== \'all\' && v.price === null) return false;\n    return true;\n  });\n\n  rows.sort((a,b) => {\n    if (sort === \'price-low\') return (a.price ?? Infinity) - (b.price ?? Infinity);\n    if (sort === \'price-high\') return (b.price ?? -1) - (a.price ?? -1);\n    if (sort === \'year-new\') return Number(b.year || 0) - Number(a.year || 0);\n    if (sort === \'miles-low\') return (a.mileage ?? Infinity) - (b.mileage ?? Infinity);\n    const priority = { new: 0, certified: 1, preowned: 2 };\n    return (priority[a.condition] ?? 9) - (priority[b.condition] ?? 9) || Number(b.year || 0) - Number(a.year || 0);\n  });\n  state.filtered = rows;\n  renderVehicles();\n}\n\nfunction placeholderDataUrl() {\n  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><rect width="800" height="600" fill="#eef1f4"/><text x="400" y="300" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="28" fill="#697580">Vehicle photo</text></svg>`;\n  return \'data:image/svg+xml;charset=utf-8,\' + encodeURIComponent(svg);\n}\n\nfunction renderVehicles() {\n  const grid = $(\'vehicleGrid\');\n  const template = $(\'vehicleTemplate\');\n  const empty = $(\'emptyState\');\n  grid.innerHTML = \'\';\n\n  $(\'inventorySummary\').textContent = `${state.filtered.length} vehicle${state.filtered.length === 1 ? \'\' : \'s\'} shown`;\n  empty.classList.toggle(\'hidden\', state.filtered.length !== 0);\n\n  for (const v of state.filtered) {\n    const node = template.content.cloneNode(true);\n    const img = node.querySelector(\'.vehicle-image\');\n    img.src = v.image || placeholderDataUrl();\n    img.alt = v.title || \'Vehicle\';\n    if (!v.image) img.classList.add(\'is-empty\');\n    img.addEventListener(\'error\', () => { img.src = placeholderDataUrl(); img.classList.add(\'is-empty\'); }, { once: true });\n\n    node.querySelector(\'.condition-badge\').textContent = v.condition_label || \'Inventory\';\n    node.querySelector(\'.vehicle-dealer\').textContent = v.dealer || \'\';\n    node.querySelector(\'.vehicle-title\').textContent = v.title || [v.year, v.make, v.model, v.trim].filter(Boolean).join(\' \');\n\n    const price = node.querySelector(\'.vehicle-price\');\n    price.innerHTML = v.price !== null\n      ? `<span class="price-label">${v.price_label || \'Price\'}</span>${money(v.price)}`\n      : \'Contact for Price\';\n\n    const meta = node.querySelector(\'.vehicle-meta\');\n    const parts = [];\n    if (v.mileage !== null && v.mileage !== undefined) parts.push(`<span>Mileage: ${number(v.mileage)}</span>`);\n    if (v.stock) parts.push(`<span>Stock: ${v.stock}</span>`);\n    if (v.vin) parts.push(`<span>VIN: ${v.vin}</span>`);\n    meta.innerHTML = parts.join(\'\');\n\n    const warranty = node.querySelector(\'.warranty-line\');\n    if (v.warranty) { warranty.textContent = v.warranty; warranty.classList.remove(\'hidden\'); }\n\n    const detail = node.querySelector(\'.detail-link\');\n    detail.href = v.url;\n    const sms = node.querySelector(\'.text-link\');\n    const message = `Hi Peyton, I\'m interested in ${v.title}${v.stock ? ` (stock ${v.stock})` : \'\'}. Can you send me more information and confirm availability?`;\n    sms.href = `sms:${window.SALES_CONTACT.phoneTel}?body=${escapeSms(message)}`;\n    node.querySelector(\'.call-line\').href = `tel:${window.SALES_CONTACT.phoneTel}`;\n    grid.appendChild(node);\n  }\n}\n\nasync function loadInventory() {\n  const status = $(\'inventoryStatus\');\n  try {\n    const response = await fetch(\'/api/inventory\', { headers: { \'Accept\': \'application/json\' } });\n    if (!response.ok) throw new Error(\'Inventory request failed\');\n    const data = await response.json();\n    state.all = Array.isArray(data.vehicles) ? data.vehicles : [];\n    populateMakes();\n    applyFilters();\n\n    if (data.updated_at) {\n      const date = new Date(data.updated_at);\n      status.textContent = `Inventory checked ${date.toLocaleString()}`;\n    } else {\n      status.textContent = \'Contact Peyton to confirm current availability.\';\n    }\n    if (data.errors && data.errors.length) {\n      status.textContent += \' One or more inventory sources may be temporarily unavailable.\';\n    }\n  } catch (error) {\n    status.textContent = \'Current inventory could not be loaded. Contact Peyton directly for availability.\';\n    state.all = [];\n    renderVehicles();\n  }\n}\n\n[\'searchInput\',\'conditionFilter\',\'makeFilter\',\'priceFilter\',\'sortFilter\'].forEach(id => {\n  $(id).addEventListener(id === \'searchInput\' ? \'input\' : \'change\', applyFilters);\n});\nloadInventory();\n'

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
        "allowed_new_makes": {"buick", "gmc"},
        "paths": ["/new-vehicles/", "/used-vehicles/"],
    },
    {
        "dealer": "Jim Hudson Cadillac",
        "domain": "https://www.jimhudsoncadillac.com",
        "allowed_new_makes": {"cadillac"},
        "paths": ["/new-vehicles/", "/used-vehicles/"],
    },
]

# User's inventory rule: qualifying pre-owned stock begins JB + number(s),
# or B + number(s). This intentionally excludes BP..., BU..., etc.
QUALIFYING_USED_STOCK = re.compile(r"^(?:JB\d+|B\d+)", re.I)
VIN_RE = re.compile(r"\b([A-HJ-NPR-Z0-9]{17})\b", re.I)
STOCK_RE = re.compile(r"\bStock\s*:?\s*([A-Z0-9-]+)\b", re.I)
MILEAGE_RE = re.compile(r"\bMileage\s*:?\s*([0-9,]+)\b", re.I)
YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")

CACHE_TTL_SECONDS = int(os.getenv("INVENTORY_CACHE_SECONDS", "1800"))
MAX_PAGES_PER_FEED = int(os.getenv("MAX_PAGES_PER_FEED", "100"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("INVENTORY_REQUEST_TIMEOUT", "18"))

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


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def absolute_url(base: str, value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith("//"):
        return "https:" + value
    return urljoin(base, value)


def parse_money(card_text: str) -> tuple[int | None, str]:
    # Dealer cards can expose several numbers. Prefer the customer-facing price.
    patterns = [
        (r"Internet Price\s*\$?\s*([0-9][0-9,]*)", "Internet Price"),
        (r"Sale Price\s*\$?\s*([0-9][0-9,]*)", "Sale Price"),
        (r"Final Price\s*\$?\s*([0-9][0-9,]*)", "Price"),
        (r"(?:^|\s)Price\s*\$?\s*([0-9][0-9,]*)", "Price"),
        (r"MSRP\s*\$?\s*([0-9][0-9,]*)", "MSRP"),
        (r"Market Value\s*\$?\s*([0-9][0-9,]*)", "Market Value"),
    ]
    for pattern, label in patterns:
        match = re.search(pattern, card_text, re.I)
        if match:
            try:
                return int(match.group(1).replace(",", "")), label
            except ValueError:
                pass
    return None, "Contact for Price"


def choose_image(node: Tag, base: str) -> str:
    candidates: list[str] = []
    for img in node.find_all("img"):
        for attr in ("data-src", "data-lazy-src", "data-original", "src"):
            value = img.get(attr)
            if value and isinstance(value, str):
                candidates.append(value)
        srcset = img.get("srcset") or img.get("data-srcset")
        if srcset and isinstance(srcset, str):
            parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
            candidates.extend(reversed(parts))
    def score(url: str) -> tuple[int, int]:
        u = url.lower()
        points = 0
        if "vehicle-images" in u or "vehicle" in u:
            points += 10
        if any(ext in u for ext in (".jpg", ".jpeg", ".webp", ".png")):
            points += 3
        if any(x in u for x in ("logo", "favicon", "placeholder", "sprite")):
            points -= 20
        return points, len(url)
    if not candidates:
        return ""
    candidates = sorted(set(candidates), key=score, reverse=True)
    return absolute_url(base, candidates[0])


def nearest_vehicle_container(anchor: Tag) -> Tag:
    node: Tag = anchor
    best = anchor
    for _ in range(10):
        text = normalize_space(node.get_text(" ", strip=True))
        if STOCK_RE.search(text) or VIN_RE.search(text):
            best = node
            # Stop at the smallest ancestor that has both core identifiers.
            if STOCK_RE.search(text) and VIN_RE.search(text):
                break
        if not isinstance(node.parent, Tag):
            break
        node = node.parent
    return best


def title_from_node(node: Tag, detail_url: str) -> str:
    strings = [normalize_space(s) for s in node.stripped_strings]
    prefixes = ("new ", "pre-owned ", "preowned ", "certified pre-owned ", "certified preowned ", "carbravo ")
    for s in strings:
        low = s.lower()
        if 12 <= len(s) <= 140 and low.startswith(prefixes) and YEAR_RE.search(s):
            return s
    for tag_name in ("h1", "h2", "h3", "h4"):
        tag = node.find(tag_name)
        if tag:
            text = normalize_space(tag.get_text(" ", strip=True))
            if YEAR_RE.search(text):
                return text
    # Fallback from DealerInspire-style detail URL slug.
    slug = urlparse(detail_url).path.rstrip("/").split("/")[-1]
    slug = re.sub(r"-[A-HJ-NPR-Z0-9]{17}$", "", slug, flags=re.I)
    slug = slug.replace("-", " ")
    return normalize_space(slug).title()


def title_parts(title: str) -> tuple[str, str, str, str]:
    cleaned = re.sub(
        r"^(?:Certified\s+Pre-Owned|Certified\s+Preowned|CarBravo(?:\s+Certified)?|Pre-Owned|Preowned|Used|New)\s+",
        "",
        title,
        flags=re.I,
    )
    match = re.match(r"(?P<year>19\d{2}|20\d{2})\s+(?P<make>\S+)\s+(?P<rest>.+)", cleaned)
    if not match:
        return "", "", cleaned, ""
    year, make, rest = match.group("year"), match.group("make"), match.group("rest")
    pieces = rest.split()
    model = pieces[0] if pieces else rest
    trim = " ".join(pieces[1:]) if len(pieces) > 1 else ""
    return year, make, model, trim


def classify_vehicle(title: str, card_text: str, detail_url: str, dealer: str) -> tuple[str, str, str]:
    haystack = " ".join([title, card_text, detail_url]).lower()
    if "carbravo" in haystack:
        return "certified", "CarBravo Certified Pre-Owned", "12-month / 12,000-mile warranty"
    if "certified pre-owned" in haystack or "certified preowned" in haystack or "cpo" in haystack:
        if "cadillac" in dealer.lower():
            return "certified", "Cadillac Certified Pre-Owned", "12-month unlimited-mile bumper-to-bumper warranty"
        return "certified", "Certified Pre-Owned", "Contact Peyton for warranty details"
    if "pre-owned" in haystack or "preowned" in haystack or "/inventory/used-" in haystack or re.search(r"\bused\b", haystack):
        return "preowned", "Pre-Owned", ""
    if "/inventory/new-" in haystack or re.search(r"\bnew\b", haystack):
        return "new", "New", ""
    return "unknown", "", ""


def allowed_new_make(make: str, allowed: set[str], title: str) -> bool:
    make_l = (make or "").lower()
    if make_l in allowed:
        return True
    low = title.lower()
    return any(re.search(rf"\b{re.escape(m)}\b", low) for m in allowed)


def extract_page_vehicles(html: str, source: dict, page_url: str) -> list[Vehicle]:
    soup = BeautifulSoup(html, "html.parser")
    seen_urls: set[str] = set()
    vehicles: list[Vehicle] = []

    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "")
        if "/inventory/" not in href:
            continue
        detail_url = absolute_url(source["domain"], href).split("?")[0]
        if detail_url in seen_urls:
            continue
        seen_urls.add(detail_url)

        node = nearest_vehicle_container(anchor)
        text = normalize_space(node.get_text(" ", strip=True))
        stock_match = STOCK_RE.search(text)
        vin_match = VIN_RE.search(text)
        stock = stock_match.group(1).upper() if stock_match else ""
        vin = vin_match.group(1).upper() if vin_match else ""
        if not stock and not vin:
            continue

        title = title_from_node(node, detail_url)
        year, make, model, trim = title_parts(title)
        condition, condition_label, warranty = classify_vehicle(title, text, detail_url, source["dealer"])
        if condition == "unknown":
            continue

        # All pre-owned/certified inventory must meet Peyton's stock rule.
        if condition in {"preowned", "certified"} and not QUALIFYING_USED_STOCK.match(stock):
            continue

        # New inventory is limited to brands sold by the two requested stores.
        if condition == "new" and not allowed_new_make(make, source["allowed_new_makes"], title):
            continue

        mileage_match = MILEAGE_RE.search(text)
        mileage = int(mileage_match.group(1).replace(",", "")) if mileage_match else None
        price, price_label = parse_money(text)

        vehicles.append(
            Vehicle(
                title=title,
                year=year,
                make=make,
                model=model,
                trim=trim,
                condition=condition,
                condition_label=condition_label,
                warranty=warranty,
                price=price,
                price_label=price_label,
                mileage=mileage,
                stock=stock,
                vin=vin,
                image=choose_image(node, source["domain"]),
                url=detail_url,
                dealer=source["dealer"],
                source_domain=source["domain"],
            )
        )
    return vehicles


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }
    )
    return s


def fetch_feed(source: dict, path: str) -> list[Vehicle]:
    s = session()
    all_vehicles: list[Vehicle] = []
    page_seen_keys: set[str] = set()
    empty_or_repeat_streak = 0

    for page in range(1, MAX_PAGES_PER_FEED + 1):
        url = f"{source['domain']}{path}?_p={page}"
        try:
            response = s.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.RequestException:
            # One retry with a small delay; then stop this feed rather than hammering the site.
            time.sleep(1.2)
            try:
                response = s.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
                response.raise_for_status()
            except requests.RequestException:
                break

        parsed = extract_page_vehicles(response.text, source, url)
        page_keys = {v.vin or v.stock or v.url for v in parsed}
        new_keys = page_keys - page_seen_keys

        if not parsed or not new_keys:
            empty_or_repeat_streak += 1
        else:
            empty_or_repeat_streak = 0
            all_vehicles.extend(v for v in parsed if (v.vin or v.stock or v.url) in new_keys)
            page_seen_keys.update(new_keys)

        # Two consecutive empty/repeated pages normally means pagination is exhausted.
        if empty_or_repeat_streak >= 2:
            break
        time.sleep(0.12)

    return all_vehicles


def merge_vehicle(existing: Vehicle, incoming: Vehicle) -> Vehicle:
    # Keep the more complete record while preserving the stronger certification label.
    fields = asdict(existing)
    incoming_fields = asdict(incoming)
    for key, value in incoming_fields.items():
        if fields.get(key) in (None, "", 0) and value not in (None, "", 0):
            fields[key] = value
    priority = {"new": 1, "preowned": 2, "certified": 3}
    if priority.get(incoming.condition, 0) > priority.get(existing.condition, 0):
        fields["condition"] = incoming.condition
        fields["condition_label"] = incoming.condition_label
        fields["warranty"] = incoming.warranty
    return Vehicle(**fields)


def refresh_inventory() -> dict:
    jobs = [(source, path) for source in SOURCES for path in source["paths"]]
    raw: list[Vehicle] = []
    errors: list[str] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_feed, source, path): (source, path) for source, path in jobs}
        for future in concurrent.futures.as_completed(futures):
            source, path = futures[future]
            try:
                raw.extend(future.result())
            except Exception as exc:  # Keep the site usable even if one source changes.
                errors.append(f"{source['dealer']} {path}: {type(exc).__name__}")

    deduped: dict[str, Vehicle] = {}
    for vehicle in raw:
        key = vehicle.vin or vehicle.stock or vehicle.url
        if key in deduped:
            deduped[key] = merge_vehicle(deduped[key], vehicle)
        else:
            deduped[key] = vehicle

    vehicles = list(deduped.values())
    vehicles.sort(key=lambda v: (v.condition != "new", -(int(v.year) if v.year.isdigit() else 0), v.make, v.model))

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
        "rules": {
            "qualifying_preowned_stock": "JB followed by numbers, or B followed by numbers",
            "carbravo_warranty": "12-month / 12,000-mile warranty",
            "cadillac_cpo_warranty": "12-month unlimited-mile bumper-to-bumper warranty",
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
    # Optional force=1 is intentionally limited to local/dev use.
    force = request.args.get("force") == "1" and app.debug
    try:
        return jsonify(get_inventory(force=force))
    except Exception as exc:
        return jsonify({"updated_at": None, "count": 0, "counts": {}, "vehicles": [], "errors": [type(exc).__name__]}), 503


@app.route("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
