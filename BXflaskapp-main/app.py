from flask import Flask, request, redirect, url_for
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from contact import Contact
from invoice import Invoice
import re
import webbrowser
import csv
import base64
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from flask import Flask
import requests
import base64

app = Flask(__name__)

if __name__ == "__main__":
    file_path = 'messages.txt'
   


# Define your Xero API credentials and redirect URI
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = "https://bx.richardbaldwin.nz/callback"

# Set up logging for debugging
app.logger.setLevel(logging.INFO)
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)
   



# Make the WSGI interface available at the top level so wfastcgi can get it.
wsgi_app = app.wsgi_app

# The Main Page which does nothing
@app.route('/')
def index():
    app.logger.info(f'Info Log')
    app.logger.error("Error Log")
    return "Hello World!"



def serialize_form_data(form_data):
    # Serialize form data in a consistent order
    items = sorted(form_data.items())
    serialized = ";".join(f"{key}={value}" for key, value in items)
    return serialized

# The endpoint to which SendGrid will send the parsed email
@app.route('/append-message', methods=['POST'])
def sendgrid_parser():
    file_path = 'messages.txt'
    if request.method == 'POST':
        try:
            # Serialize the current request form data
            current_form_serialized = serialize_form_data(request.form)
           
            # Initialize a flag to check if the form data is new
            form_data_is_new = True

            # Check if the file exists to avoid FileNotFoundError
            if os.path.exists(file_path):
                # Read the file and check if the serialized form data has appeared previously
                with open(file_path, 'r') as file:
                    file_contents = file.read()
                    if current_form_serialized in file_contents:
                        form_data_is_new = False

            if form_data_is_new:
                # Open the file and append the message
                with open(file_path, 'a') as file:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    file.write(f"Called at: {current_time}\n")
                    file.write("Form Data:" + '\n')
                    file.write(current_form_serialized + '\n\n')

                # Calls function to send file name and start the Xero API process
                # finding_source function is defined on line 447-ish
                result = finding_source(file_path)  # Result currently isn't used
               
                return "Data Added", 200
            else:
                return "Duplicate Form Data, not added", 200
        except Exception as e:
            # Handle exceptions
            return f"An error occurred: {e}", 500


# Working Test Email Code
# @app.route('/send_test_email')
def send_email():
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    from_email = Email("richard@monument.page")  # Change to your verified sender
    to_email = To("richard@empyre.co")  # Change to your recipient
    subject = "Sending with SendGrid is Fun"
    content = Content("text/plain", "and easy to do anywhere, even with Python")
    mail = Mail(from_email, to_email, subject, content)

    # Get a JSON-ready representation of the Mail object
    mail_json = mail.get()

    # Send an HTTP POST request to /mail/send
    response = sg.client.mail.send.post(request_body=mail_json)

    # This is the response from the SendGrid API, but it's not strictly required
    #print(response.status_code)
    #print(response.headers)


#================================================================================================
    #Xero Code
#================================================================================================



# Define the path to the file where tokens will be stored
TOKEN_FILE_PATH = 'xero_tokens2.txt'
RECORDS_FILE_PATH = 'records.txt'

# Saves tokens to a file
def save_tokens(access_token, refresh_token, tenant_id):
    print("tenantID: ", tenant_id)
    with open(TOKEN_FILE_PATH, 'w') as f:
        f.write(f"access_token={access_token}\n")
        f.write(f"refresh_token={refresh_token}\n")
        f.write(f"tenant_id={tenant_id}\n")

# Records Data in a file
def record_data(data):

    with open(RECORDS_FILE_PATH, 'w') as f:
        f.write(f"data={data}\n")
       

def get_refresh_token():
    if os.path.exists(TOKEN_FILE_PATH):
        with open(TOKEN_FILE_PATH, 'r') as f:
            tokens = f.readlines()
            for token in tokens:
                if token.startswith("refresh_token="):
                    refresh_token = token.split("=")[1].strip()
                    return refresh_token
    return None

def get_tenant_id():
    if os.path.exists(TOKEN_FILE_PATH):
        with open(TOKEN_FILE_PATH, 'r') as f:
            tokens = f.readlines()
            for token in tokens:
                if token.startswith("tenant_id="):
                    tenant_id = token.split("=")[1].strip()
                    return tenant_id
    return None

def refresh_access_token():
    token_url = "https://identity.xero.com/connect/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": get_refresh_token()
    }
    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        new_access_token = response.json().get("access_token")
        new_refresh_token = response.json().get("refresh_token")
        print(new_refresh_token)
        tenant_id = get_tenant_id()  # Retrieve tenant ID from storage
        # Save tokens and tenantID for future use
        save_tokens(new_access_token, new_refresh_token, tenant_id)
        return new_access_token
    else:
        # Handle the case where token refreshing fails
        print("Token refreshing failed")
        return "Token refreshing failed"
   
def get_access_token():
    if os.path.exists(TOKEN_FILE_PATH):
        with open(TOKEN_FILE_PATH, 'r') as f:
            tokens = f.readlines()
            access_token = None
            for token in tokens:
                if token.startswith("access_token="):
                    access_token = token.split("=")[1].strip()
                    break
            return access_token
    return None
#No tenant ID saved
#Implement the create_invoice function to create an invoice in Xero
def create_invoice(xero_invoice, access_token, tenant_id):
    create_invoice_url = "https://api.xero.com/api.xro/2.0/Invoices"
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
        "xero-tenant-id": tenant_id
    }
    response = requests.post(create_invoice_url, headers=headers, json=xero_invoice)
    if response.status_code == 200:
        return "Invoice created successfully"
    else:
        error_message = f"Failed to create invoice: {response.text}"
        print(error_message)
        return error_message

# Define the home route    
@app.route('/')
def home():
    print("request args: ", request.args)
    return "Welcome to the Invoice Creation App!!"

# Define the login route to start the OAuth 2.0 flow
@app.route('/login')
def login():
    # Redirect the user to the Xero authorization URL (same as before)
    xero_authorization_url = (
        "https://login.xero.com/identity/connect/authorize?"
        f"response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
        "&scope=openid offline_access profile email accounting.transactions&state=123"
    )
    print("xero_authorization_url: ", xero_authorization_url)
    return redirect(xero_authorization_url)

# Define the callback route to handle the authorization code automatically
@app.route('/callback')
def callback():
    # Get the authorization code from the query parameters
    code = request.args.get('code')
    print("request args: ", request.args)
    # Make a POST request to exchange the authorization code for an access token
    token_url = "https://identity.xero.com/connect/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(token_url, headers=headers, data=data)
    print("response: ", response.json())
    # Handle the response
    if response.status_code == 200:
        access_token = response.json().get("access_token")
        refresh_token = response.json().get("refresh_token")
        tenant_id = check_tenants(access_token)
        save_tokens(access_token, refresh_token, tenant_id)
       
        return "Authorization successful. You can now create invoices."
    else:
        return "Failed to exchange the authorization code for an access token. Response Error: " + response.text


def check_tenants(access_t):
    t_response = requests.get("https://api.xero.com/connections", headers={"Authorization": "Bearer " + access_t, "Content-Type": "application/json"})
    print("tenants: ", t_response.json())
    response_data = t_response.json()
    record_data(response_data)

    # Iterate over the list to find the dictionary with 'tenantName' as 'Book Express Ltd'
    for item in response_data:
        if item['tenantName'] == 'Book Express Ltd':
            tenant_id_demo = item['tenantId']
            print("Demo ID: ", tenant_id_demo)
            return tenant_id_demo
    return None

# Define the create_invoice route to create an invoice in Xero once authorized
#@app.route('/create_invoice')
def create_invoice_route():
    # Check if access token is expired or about to expire
    access_token = get_access_token()
    if access_token is None:
        access_token = refresh_access_token()
    if access_token:
        # Proceed with invoice creation using the refreshed access token
        tenant_id = get_tenant_id()

        # Replace this example invoice data with your actual data
        xero_invoice = {
            "Type": "ACCREC",
            "Contact": {
                "Name": "Customer Name",
                "Addresses": [{
                    "AddressType": "STREET",
                    "AddressLine1": "123 Main Street",
                    "PostalCode": "12345"
                }]
            },
            "Date": "2023-01-01",
            "DueDate": "2023-01-15",
            "LineItems": [{
                "Description": "Example Item",
                "Quantity": 1,
                "UnitAmount": 100.00,
                "AccountCode": "200"
            }],
            "Reference": "INV-001"
        }
        result = create_invoice(xero_invoice, access_token, tenant_id)
        return result
    else:
        return "Failed to create invoice. Unable to obtain access token."


#================================================================================================
    #Process the Emails
#================================================================================================
    


# Process Fishpond Emails to extract the relevant data
def process_fishpond(text):
    name_pattern = r"Send to:\s*\n\n(\w+ \w+)"
    email_pattern = r"(\w+@\w+\.\w+)"
    phone_pattern = r"(\+\d{2} \d{2} \d{6})"
    address_patterns = {
        'AddressLine1': r"Send to:\s*[\s\S]*?\n\n.*\n(.*?)\n",
        'AddressLine2': r"Send to:\s*[\s\S]*?\n\n.*\n.*\n(.*?)\n",
        'AddressLine3': r"Send to:\s*[\s\S]*?\n\n.*\n.*\n.*\n(.*?)\n",
        'City': r"Send to:\s*[\s\S]*?\n\n.*\n.*\n.*\n.*\n(\D+),",
        'PostalCode': r"Send to:\s*[\s\S]*?\n\n.*\n.*\n.*\n.*\n.*,\s*(\d+)"
    }
    total_pattern = r"=\s*\$(\d+\.\d{2})"

    extracted_address = {}
    for key, pattern in address_patterns.items():
        match = re.search(pattern, text)
        if match:
            extracted_address[key] = match.group(1).strip()

    name_match = re.search(name_pattern, text)
    email_match = re.search(email_pattern, text)
    phone_match = re.search(phone_pattern, text)
    total_match = re.search(total_pattern, text)
    Name = name_match.group(1)
    EmailAddress = email_match.group(1)
    Phone = phone_match.group(1)
    Total = total_match.group(1)

    data=['fishpond','null',Name,EmailAddress,Total]
    save_to_csv(data)

    access_token = get_access_token()
    if access_token is None:
        access_token = refresh_access_token()
    if access_token:
        tenant_id = get_tenant_id()
        xero_invoice = format_to_json(Name, extracted_address.get('AddressLine1'), extracted_address.get('AddressLine2'), extracted_address.get('City'), extracted_address.get('PostalCode'), Total, "Fishpond Sale")
        result = create_invoice(xero_invoice, access_token, tenant_id)
        # erase the contents of the messages.txt file
        open('messages.txt', 'w').close()
        return result
    else:
        return "Failed to create invoice. Unable to obtain access token."


# Process Chrisland Emails to extract the relevant data
def process_christland(text):
    orderid_pattern = r"\*Order ID: \*(\d+)"
    name_pattern = r"Shipping Info\n\n(.+)"
    address_line1_pattern = r"Shipping Info\n\n.+\n\n(.+)"
    address_line2_pattern = r"Shipping Info\n\n.+\n\n.+\n\n(.+)"
    city_pattern = r"Shipping Info\n\n.+\n\n.+\n\n.+\n\n(.+)"
    email_pattern = r"(\S+@\S+)"
    phone_pattern = r"Phone: (\d+)"
    subtotal_pattern = r"Subtotal\s+NZ\$(\d+\.\d{2})"
    total_pattern = r"Total\s+NZ\$(\d+\.\d{2})"
    order_id = re.search(orderid_pattern, text).group(1)
    name = re.search(name_pattern, text).group(1)
    address_line1 = re.search(address_line1_pattern, text).group(1)
    address_line2 = re.search(address_line2_pattern, text).group(1)
    cityText = re.search(city_pattern, text).group(1)
    city, postal_code = cityText.split(" ", 1)
    email_address = re.search(email_pattern, text).group(1)
    phone = re.search(phone_pattern, text).group(1)
    subtotal_match = re.search(subtotal_pattern, text)
    sub_total = subtotal_match.group(1)
   
    total_match = re.search(total_pattern, text)
    total = total_match.group(1)

    data = ['chrisland',order_id,name,email_address,total]
    save_to_csv(data)

    access_token = get_access_token()
    if access_token is None:
        access_token = refresh_access_token()
    if access_token:
        tenant_id = get_tenant_id()
        xero_invoice = format_to_json(name, address_line1, address_line2, city, postal_code, total, "Chrisland Sale")
        result = create_invoice(xero_invoice, access_token, tenant_id)
        # erase the contents of the messages.txt file
        open('messages.txt', 'w').close()
        return result
    else:
        return "Failed to create invoice. Unable to obtain access token."
   

# Process Biblio Emails to extract the relevant data
def process_biblio(text):
    email_match = re.search(r"\*Customer Email: \*.*<(.+?)>", text)
    phone_match = re.search(r"\*Customer Phone: \*([0-9 ]+)", text)

    # get order_id
    id_pattern = r"Shipment\s*#\s*([0-9]+-[0-9]+-[0-9]+)"
    id_match = re.search(id_pattern, text)
    order_id = id_match.group(1)
    print("Order ID:", order_id)

    EmailAddress = email_match.group(1) if email_match else None
    Phone = phone_match.group(1) if phone_match else None

    lines = text.strip().split('\n')
    ship_to_index = lines.index("*Ship to:*") + 1
    Name = lines[ship_to_index].strip()
    AddressLine1 = lines[ship_to_index + 1].strip()
    City_PostalCode = lines[ship_to_index + 2].strip()
    City, PostalCode = re.match(r"(.*) (\d+)", City_PostalCode).groups()
    sub_total_match = re.search(r"Subtotal: NZ\$(\d+\.\d+)", text)
    total_match = re.search(r"Total: NZ\$(\d+\.\d+)", text)
    sub_total = sub_total_match.group(1) if sub_total_match else None
    total = total_match.group(1) if total_match else None

    AddressLine2 = None
    if len(lines) > ship_to_index + 2:
        AddressLine2 = lines[ship_to_index + 2].strip()
        if AddressLine2 == City+" "+PostalCode :
            AddressLine2 = ""

    data = ['biblio',order_id,Name,EmailAddress,str(total)]
    save_to_csv(data)

    access_token = get_access_token()
    if access_token is None:
        access_token = refresh_access_token()
    if access_token:
        tenant_id = get_tenant_id()
        xero_invoice = format_to_json(Name, AddressLine1, AddressLine2, City, PostalCode, total, "Biblio Sale")
        result = create_invoice(xero_invoice, access_token, tenant_id)
        # erase the contents of the messages.txt file
        open('messages.txt', 'w').close()

        return result
    else:
        return "Failed to create invoice. Unable to obtain access token."


# Process the file to determine the source of the email
def finding_source(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            if 'Biblio.co.nz' in content:
                print('this is a mail from + Biblio.co.nz')
                return process_biblio(content)
            elif 'Fishpond.co.nz' in content:
                print("this is a mail from fishpond")
                return process_fishpond(content)
            else: # This assumes that only emails from Chrisland are left and would need to be changed if more sources are added
                print("this is a mail from chrisland")
                return process_christland(content)
    except FileNotFoundError:
        return "file not found"


# Test the invoice creation from a file
@app.route('/testInvoiceFromFile')
def testInvoiceFromFile():
    file_path = 'messages.txt'
    result = finding_source(file_path)
    return result
   
   
# creates a Xero invoice object from the data
def format_to_json(name1, address_line11, address_line21, city1, postal_code1, total1, sale_ref1):
    xero_invoice = {
            "Type": "ACCREC",
            "Contact": {
                "Name": name1,
                "Addresses": [{
                    "AddressType": "STREET",
                    "AddressLine1": address_line11,
                    "AddressLine2": address_line21,
                    "City": city1,
                    "PostalCode": postal_code1
                }]
            },
            "Date": "2023-01-01",
            "DueDate": "2023-01-15",
            "LineItems": [{
                "Description": "Example Item",
                "Quantity": 1,
                "UnitAmount": total1,
                "AccountCode": "220"
            }],
            "Reference": sale_ref1
        }
    return xero_invoice


#================================================================================================
    #Save to CSV & Check Duplicate
#================================================================================================


def check_duplicate(filename,data):
    if not os.path.exists(filename):
        return False
    
    with open(filename, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader, None)
        if headers is None:
            return False
        
        order_id_index = headers.index('order_id')
        email_index = headers.index('customer_email')
        total_index = headers.index('total')

        for row in reader:
            if data[0].lower() == 'fishpond':
                 if row[email_index] == data[3] and row[total_index] == data[4]:
                     print('fishpond record exists')
                     return True
            else:
                if row[order_id_index] == data[1]:
                    print("order_id exists")
                    return True
    return False


def save_to_csv(data):
    print(data)
    filename = 'info.csv'
    headers = ['platform', 'order_id', 'customer_name', 'customer_email', 'total']
    file_exists = os.path.exists(filename)
    order_id_exists = check_duplicate(filename, data)
    if not order_id_exists:
        with open(filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(data)
