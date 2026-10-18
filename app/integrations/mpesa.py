import base64
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import requests

class PaymentProvider(ABC):
    @abstractmethod
    def initiate_stk_push(
        self,
        phone_number: str,
        amount_minor: int,
        account_reference: str,
        transaction_desc: str
    ) -> Dict[str, Any]:
        """
        Initiates an STK push / checkout request.
        Returns dict containing merchant_request_id, checkout_request_id, provider_status.
        """
        pass

    @abstractmethod
    def verify_transaction(self, provider_reference: str) -> Dict[str, Any]:
        """
        Verifies transaction status with the provider.
        """
        pass

class MockPaymentProvider(PaymentProvider):
    def initiate_stk_push(
        self,
        phone_number: str,
        amount_minor: int,
        account_reference: str,
        transaction_desc: str
    ) -> Dict[str, Any]:
        req_id = f"MOCK_REQ_{uuid.uuid4().hex[:12]}"
        chk_id = f"ws_CO_{uuid.uuid4().hex[:16]}"
        return {
            "success": True,
            "merchant_request_id": req_id,
            "checkout_request_id": chk_id,
            "customer_message": "Success. Enter M-Pesa PIN on your phone.",
            "response_code": "0"
        }

    def verify_transaction(self, provider_reference: str) -> Dict[str, Any]:
        return {
            "success": True,
            "provider_reference": provider_reference,
            "status": "confirmed"
        }

class DarajaPaymentProvider(PaymentProvider):
    """
    Safaricom Daraja STK Push (Lipa Na M-Pesa Online).
    NOTE: written against Daraja's documented API but not yet exercised against Safaricom.
    Test end to end in the sandbox (MPESA_ENVIRONMENT=sandbox) before enabling production.
    """
    BASE_URLS = {
        "sandbox": "https://sandbox.safaricom.co.ke",
        "production": "https://api.safaricom.co.ke",
    }

    def __init__(self, consumer_key: str, consumer_secret: str, shortcode: str, passkey: str,
                 callback_url: str, environment: str = "sandbox"):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.shortcode = shortcode
        self.passkey = passkey
        self.callback_url = callback_url
        self.base_url = self.BASE_URLS.get(environment, self.BASE_URLS["sandbox"])

    def _access_token(self) -> str:
        resp = requests.get(
            f"{self.base_url}/oauth/v1/generate",
            params={"grant_type": "client_credentials"},
            auth=(self.consumer_key, self.consumer_secret),
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def initiate_stk_push(
        self,
        phone_number: str,
        amount_minor: int,
        account_reference: str,
        transaction_desc: str
    ) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        msisdn = phone_number.lstrip("+")  # Daraja expects 2547XXXXXXXX
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",  # use CustomerBuyGoodsOnline for a Till number
            "Amount": amount_minor // 100,
            "PartyA": msisdn,
            "PartyB": self.shortcode,
            "PhoneNumber": msisdn,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference[:12],
            "TransactionDesc": transaction_desc[:13],
        }
        resp = requests.post(
            f"{self.base_url}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={"Authorization": f"Bearer {self._access_token()}"},
            timeout=30,
        )
        data = resp.json()
        if resp.status_code != 200 or str(data.get("ResponseCode")) != "0":
            raise RuntimeError(data.get("errorMessage") or data.get("ResponseDescription") or "STK push rejected")
        return {
            "success": True,
            "merchant_request_id": data["MerchantRequestID"],
            "checkout_request_id": data["CheckoutRequestID"],
            "customer_message": data.get("CustomerMessage", ""),
            "response_code": str(data.get("ResponseCode")),
        }

    def verify_transaction(self, provider_reference: str) -> Dict[str, Any]:
        raise NotImplementedError("Transaction status query is not implemented; rely on the callback.")

def get_payment_provider() -> PaymentProvider:
    from app.core.config import settings
    unconfigured = settings.MPESA_ENVIRONMENT == "mock" or "placeholder" in settings.MPESA_CONSUMER_KEY
    if unconfigured:
        if settings.IS_PRODUCTION:
            raise RuntimeError("Payments are not configured: set real MPESA_* credentials.")
        return MockPaymentProvider()
    callback_url = settings.MPESA_CALLBACK_URL
    if settings.MPESA_CALLBACK_TOKEN:
        callback_url += ("&" if "?" in callback_url else "?") + "token=" + settings.MPESA_CALLBACK_TOKEN
    return DarajaPaymentProvider(
        consumer_key=settings.MPESA_CONSUMER_KEY,
        consumer_secret=settings.MPESA_CONSUMER_SECRET,
        shortcode=settings.MPESA_SHORTCODE,
        passkey=settings.MPESA_PASSKEY,
        callback_url=callback_url,
        environment=settings.MPESA_ENVIRONMENT,
    )
