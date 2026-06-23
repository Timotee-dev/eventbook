"""
Real Paystack API integration.
Handles: initialize, verify, webhook signature, transfers (payouts), refunds.
"""
import hashlib, hmac, logging, requests
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger('apps')

class PaystackError(Exception):
    pass

class Paystack:
    def __init__(self):
        self.key = settings.PAYSTACK_SECRET_KEY
        self.base = settings.PAYSTACK_BASE_URL

    def _h(self):
        return {'Authorization': f'Bearer {self.key}', 'Content-Type': 'application/json'}

    def _call(self, method, path, **kw):
        url = self.base + path
        try:
            r = requests.request(method, url, headers=self._h(), timeout=15, **kw)
            d = r.json()
        except requests.RequestException as e:
            logger.error(f'Paystack network error: {e}')
            raise PaystackError('Payment gateway unreachable. Try again.')
        except Exception:
            raise PaystackError('Unexpected gateway response.')
        if not d.get('status'):
            logger.error(f'Paystack error: {d.get("message")}')
            raise PaystackError(d.get('message', 'Gateway error.'))
        return d.get('data', {})

    def initialize(self, email, amount_ngn: Decimal, reference: str, callback_url: str, metadata=None):
        """Returns {authorization_url, access_code, reference}"""
        return self._call('POST', '/transaction/initialize', json={
            'email': email,
            'amount': int(Decimal(str(amount_ngn)) * 100),
            'reference': reference,
            'callback_url': callback_url,
            'metadata': metadata or {},
        })

    def verify(self, reference: str):
        """Returns full transaction data. Check data['status'] == 'success'."""
        return self._call('GET', f'/transaction/verify/{reference}')

    def create_recipient(self, name, account_number, bank_code):
        return self._call('POST', '/transferrecipient', json={
            'type': 'nuban', 'name': name,
            'account_number': account_number,
            'bank_code': bank_code, 'currency': 'NGN',
        })

    def transfer(self, amount_ngn: Decimal, recipient_code: str, reason: str, reference: str):
        return self._call('POST', '/transfer', json={
            'source': 'balance',
            'amount': int(Decimal(str(amount_ngn)) * 100),
            'recipient': recipient_code,
            'reason': reason, 'reference': reference,
        })

    def refund(self, transaction_ref: str, amount_ngn: Decimal = None):
        body = {'transaction': transaction_ref}
        if amount_ngn:
            body['amount'] = int(Decimal(str(amount_ngn)) * 100)
        return self._call('POST', '/refund', json=body)

    def list_banks(self):
        return self._call('GET', '/bank?currency=NGN&perPage=100')

    @staticmethod
    def verify_signature(raw_body: bytes, signature: str) -> bool:
        if not signature:
            return False
        secret = settings.PAYSTACK_SECRET_KEY.encode()
        computed = hmac.new(secret, raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed, signature)
