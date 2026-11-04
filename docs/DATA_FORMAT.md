# Data format

Accepted upload columns:

- invoice_no (or InvoiceNo)
- product_code (or StockCode)
- invoice_date (or InvoiceDate)
- quantity (or Quantity)

Optional fields:

- description
- unit_price
- customer_id
- country

This project excludes cancelled invoices (InvoiceNo begins with "C") and drops invalid or zero quantities before aggregation.
