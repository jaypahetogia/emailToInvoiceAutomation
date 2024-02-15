class Contact:
    def __init__(self, ContactID, Name, Phone,EmailAddress, Addresses=None):
        self.ContactID = ContactID
        self.Name = Name
        self.Phone = Phone
        self.EmailAddress = EmailAddress
        self.Addresses = Addresses if Addresses is not None else []

    def add_address(self, AddressType, AddressLine1, City, PostalCode):
        address = {
            "AddressType": AddressType,
            "AddressLine1": AddressLine1,
            "City": City,
            "PostalCode": PostalCode
        }
        self.Addresses.append(address)

    def __repr__(self):
        return f"Contact(ContactID={self.ContactID}, Name={self.Name},Phone={self.Phone},EmailAddress={self.EmailAddress}, Addresses={self.Addresses})"
