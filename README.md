# Peyton Gaskins Inventory Website

Personal vehicle inventory website for Peyton Gaskins at Jim Hudson Cadillac / Buick GMC.

## Current version

Version: `2026-09-11-photo-price-fix-2`

This build fixes the two live-data problems from the prior deployment:

- Vehicle photos now recognize Jim Hudson's current dealership-hosted gallery URLs under `/det-content/uploads/stock-images/`, as well as the older vehicle-image hosts.
- Current price and mileage are read from Jim Hudson's lightweight `/llm/inventory/` feed and merged by VIN. A vehicle detail page is still checked in the background for gallery photos, stock number, and stronger dealer price labels such as Jim Hudson Price or Internet Price.
- JSON-LD gallery images and stock/SKU data are also parsed from vehicle detail pages as a fallback.
- Pre-owned inventory is restricted to stock numbers beginning with `JB` followed by numbers or `B` followed by numbers. Examples that qualify: `JB2238`, `B5788A`. Example that does not qualify: `BP2265A`.
- New inventory remains brand-specific: Buick/GMC from Jim Hudson Buick GMC and Cadillac from Jim Hudson Cadillac.
- Snapshot data is never used as a current price source.

The `/health` endpoint returns the deployed version so you can confirm that the hosting service is running this build.

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.

## Production / Render

The included Procfile runs the app with Gunicorn. The hosting service must allow outbound HTTPS requests to the Jim Hudson dealership websites because the inventory is live rather than hard-coded.

After replacing the deployed code, trigger a new deploy/restart so the previous in-memory inventory cache is cleared.

Useful optional environment variables:

- `PORT` - web server port.
- `INVENTORY_CACHE_SECONDS` - inventory cache time; default 1800 seconds.
- `INVENTORY_DIRECT_TIMEOUT` - sitemap request timeout; default 7 seconds.
- `INVENTORY_READER_TIMEOUT` - fallback reader timeout; default 18 seconds.
- `INVENTORY_DETAIL_TIMEOUT` - vehicle/list page request timeout; default 9 seconds.
- `INVENTORY_MAX_LISTING_PAGES` - maximum inventory pages checked per listing feed; default 100.

## Contact shown on the website

Peyton Gaskins  
Sales Associate  
Jim Hudson Cadillac / Buick GMC  
803-542-1353  
4035 Kaiser Hill Rd, Columbia, SC 29203
