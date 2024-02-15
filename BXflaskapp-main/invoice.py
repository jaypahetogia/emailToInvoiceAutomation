from contact import Contact

class Invoice:
    def __init__(self, contact, sub_total, total, currency_code, invoice_id, invoice_number):
        self.contact = contact  
        self.sub_total = sub_total
        self.total = total
        self.currency_code = currency_code
        self.invoice_id = invoice_id
        self.invoice_number = invoice_number

    def __repr__(self):
        return (f"Invoice(Contact={self.contact}, SubTotal='{self.sub_total}', Total='{self.total}', "
                f"CurrencyCode='{self.currency_code}', InvoiceID='{self.invoice_id}', InvoiceNumber='{self.invoice_number}')")
