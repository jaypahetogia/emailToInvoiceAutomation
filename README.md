# emailToInvoiceAutomation
Sendgrid is used to parse inbound emails into json.
A subdomain is setup with a dedicated mx record to forward to Sendgrid.
A server (Namecheap) hosts the created app that recieves json data from Sendgrid and reformats to a format acceptable to Xero.
Access Xero via Oauth2.0 and creates the invoice.
