# Peyton Gaskins Inventory Website

Personal vehicle inventory website for Peyton Gaskins at Jim Hudson Cadillac / Buick GMC.

## What this version does

- Uses both Jim Hudson Cadillac and Jim Hudson Buick GMC inventory sitemaps so every discovered vehicle can appear.
- Pulls vehicle-card details in bulk from the new and used inventory pages.
- Shows a short customer-facing vehicle name in the format: Year + Make + Model + Trim.
- Removes drivetrain/body wording such as Front Wheel Drive, All Wheel Drive, Four Wheel Drive, Crew Cab, Sport Utility, and similar extra wording from the visible title.
- Shows price, mileage, VIN and an available dealership photo on each card when those details are available.
- Keeps stock numbers searchable and includes them in the prefilled text message without cluttering the card.
- If a visible vehicle is still missing price, photo, stock or used-vehicle mileage, the site automatically checks that exact dealer detail page in the background and updates the card.
- Makes Call Peyton and Text Peyton the main actions. The original dealership listing is a smaller secondary link.
- Keeps the previously requested CarBravo and Cadillac Certified Pre-Owned warranty wording.

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.

## Production

The included Procfile runs the app with Gunicorn. The hosting service must allow outbound HTTPS requests to the Jim Hudson dealership websites because the inventory is live rather than hard-coded.

Useful optional environment variables:

- `PORT` - web server port.
- `INVENTORY_CACHE_SECONDS` - inventory cache time; default 1800 seconds.
- `INVENTORY_DIRECT_TIMEOUT` - sitemap request timeout; default 7 seconds.
- `INVENTORY_READER_TIMEOUT` - fallback reader timeout; default 18 seconds.
- `INVENTORY_DETAIL_TIMEOUT` - vehicle/list page request timeout; default 9 seconds.
- `INVENTORY_MAX_LISTING_PAGES` - maximum inventory pages checked per feed; default 100.

## Contact shown on the website

Peyton Gaskins  
Sales Associate  
Jim Hudson Cadillac / Buick GMC  
803-542-1353  
4035 Kaiser Hill Rd, Columbia, SC 29203
