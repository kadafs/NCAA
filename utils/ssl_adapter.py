import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class RobustSSLAdapter(HTTPAdapter):
    """
    Custom HTTPAdapter that configures a more resilient SSL Context.
    Specifically targets 'BAD_RECORD_MAC' errors by:
    1. Forcing TLS 1.2+
    2. Attempting to disable TLS Session Tickets (OP_NO_TICKET)
    """
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        # Force modern TLS
        ctx.options |= ssl.OP_NO_SSLv2
        ctx.options |= ssl.OP_NO_SSLv3
        ctx.options |= ssl.OP_NO_TLSv1
        ctx.options |= ssl.OP_NO_TLSv1_1
        
        # Disable Session Tickets - can resolve MAC errors in some network environments
        try:
            ctx.options |= getattr(ssl, "OP_NO_TICKET", 0)
        except: pass
        
        kwargs['ssl_context'] = ctx
        return super(RobustSSLAdapter, self).init_poolmanager(*args, **kwargs)

def get_robust_session(retries=3):
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = RobustSSLAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
