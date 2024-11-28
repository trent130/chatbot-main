import requests
import base64
from datetime import datetime
import json
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

class MpesaAPI:
    def __init__(self):
        self.business_shortcode = os.getenv('MPESA_BUSINESS_SHORTCODE')
        self.consumer_key = os.getenv('MPESA_CONSUMER_KEY')
        self.consumer_secret = os.getenv('MPESA_CONSUMER_SECRET')
        self.passkey = os.getenv('MPESA_PASSKEY')
        self.callback_url = os.getenv('MPESA_CALLBACK_URL')
        
        # API endpoints
        self.auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        self.stk_push_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        self.query_url = "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query"

    def generate_auth_token(self):
        """Generate OAuth token for API authentication"""
        auth_string = f"{self.consumer_key}:{self.consumer_secret}"
        auth_bytes = auth_string.encode("ascii")
        encoded_auth = base64.b64encode(auth_bytes).decode('ascii')

        headers = {
            'Authorization': f'Basic {encoded_auth}'
        }

        try:
            response = requests.get(self.auth_url, headers=headers)
            response.raise_for_status()
            token = response.json()['access_token']
            return token
        except requests.exceptions.RequestException as e:
            print(f"Error generating auth token: {e}")
            return None

    def generate_password(self):
        """Generate password for STK push"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{self.business_shortcode}{self.passkey}{timestamp}"
        encoded_password = base64.b64encode(password_string.encode()).decode('ascii')
        return encoded_password, timestamp

    async def initiate_stk_push(self, phone_number: str, amount: int, reference: str):
        """
        Initiate STK push to customer's phone
        
        Args:
            phone_number (str): Customer's phone number (format: 254XXXXXXXXX)
            amount (int): Amount to be paid
            reference (str): Reference for the transaction
        """
        token = self.generate_auth_token()
        if not token:
            return {"status": "error", "message": "Failed to generate auth token"}

        password, timestamp = self.generate_password()

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.business_shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": f"{self.callback_url}/mpesa-callback",
            "AccountReference": reference,
            "TransactionDesc": f"Payment for {reference}"
        }

        try:
            response = requests.post(self.stk_push_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    async def query_transaction_status(self, checkout_request_id: str):
        """Query the status of a transaction"""
        token = self.generate_auth_token()
        if not token:
            return {"status": "error", "message": "Failed to generate auth token"}

        password, timestamp = self.generate_password()

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }

        try:
            response = requests.post(self.query_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def process_callback(self, callback_data: dict):
        """Process callback data from M-PESA"""
        try:
            result_code = callback_data['Body']['stkCallback']['ResultCode']
            result_desc = callback_data['Body']['stkCallback']['ResultDesc']
            
            if result_code == 0:
                # Payment successful
                merchant_request_id = callback_data['Body']['stkCallback']['MerchantRequestID']
                checkout_request_id = callback_data['Body']['stkCallback']['CheckoutRequestID']
                amount = callback_data['Body']['stkCallback']['CallbackMetadata']['Item'][0]['Value']
                transaction_id = callback_data['Body']['stkCallback']['CallbackMetadata']['Item'][1]['Value']
                
                return {
                    "status": "success",
                    "message": result_desc,
                    "merchant_request_id": merchant_request_id,
                    "checkout_request_id": checkout_request_id,
                    "amount": amount,
                    "transaction_id": transaction_id
                }
            else:
                # Payment failed
                return {
                    "status": "failed",
                    "message": result_desc
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing callback: {str(e)}"
            }
