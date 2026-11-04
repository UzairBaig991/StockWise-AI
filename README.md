# StockWise AI

StockWise AI is a Windows-friendly Streamlit project for importing retail sales data, cleaning daily demand, comparing forecast models, and recommending inventory replenishment.

## Quick start on Windows 11

Open PowerShell in the project folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Dataset

The app supports CSV and Excel uploads. For real-world retail demand modeling, use the UCI Online Retail dataset:

- https://archive.ics.uci.edu/dataset/352/online+retail

Download the dataset separately and upload it through the Data Import page. Do not assume it is already in the project folder.

## What the app does

- Provides a dark, responsive inventory dashboard with stock-health indicators and sales activity
- Imports CSV/Excel transaction files
- Validates required columns and filters invalid or cancelled rows
- Aggregates daily demand per product
- Trains and compares regression models with time-based splits
- Produces a 7-day forecast and reorder recommendation logic
- Stores product and inventory settings in SQLite

## Data schema

The app expects these canonical fields for upload:

- invoice_no
- product_code
- invoice_date
- quantity

Optional fields include: description, unit_price, customer_id, country.

The importer will map common UCI Online Retail names such as `InvoiceNo`, `StockCode`, and `InvoiceDate` automatically.

## Demo data

Synthetic demo files are kept in `data/demo/` and clearly labeled as demo data. They are useful for smoke testing without using the real public dataset.

## Project structure

- `app.py` - main Streamlit app entry point
- `pages/` - multipage dashboard modules
- `src/` - project logic for database, preprocessing, forecasting, inventory, and UI helpers
- `ml/` - model training wrappers
- `tests/` - unit tests
- `docs/` - methodology and data format notes

## Notes

- The project is designed for an intermediate Python team and a 4-week academic timeline.
- The inventory logic uses user-maintained stock values, safety stock, and lead time; it does not infer supplier data from the sales history.
- Forecasts are time-aware and must be interpreted as estimates rather than guarantees.
