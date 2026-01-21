"""
Module to suppress MongoDB SSL errors globally
This should be imported at the start of training scripts
"""

import logging
import warnings
import ssl
import sys
import io
from pymongo.errors import AutoReconnect

# Suppress all SSL-related warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pymongo')
warnings.filterwarnings('ignore', message='.*SSL.*')
warnings.filterwarnings('ignore', message='.*TLS.*')
warnings.filterwarnings('ignore', message='.*handshake.*')

# Suppress pymongo background task errors completely
logging.getLogger('pymongo').setLevel(logging.CRITICAL)
logging.getLogger('pymongo.monitoring').setLevel(logging.CRITICAL)
logging.getLogger('pymongo.pool').setLevel(logging.CRITICAL)
logging.getLogger('pymongo.server_selection').setLevel(logging.CRITICAL)
logging.getLogger('pymongo.topology').setLevel(logging.CRITICAL)

# Redirect stderr for pymongo to suppress tracebacks
_original_stderr = sys.stderr

class SSLFilteredStderr:
    """Filter stderr to suppress SSL error tracebacks"""
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        self.buffer = io.StringIO()
    
    def write(self, text):
        # Filter out SSL-related error messages
        if any(keyword in text for keyword in ['SSL', 'TLS', 'handshake', 'MongoClient background task', 
                                                'tlsv1 alert', 'SSLError', 'AutoReconnect']):
            # Write to buffer instead of stderr
            self.buffer.write(text)
        else:
            self.original_stderr.write(text)
    
    def flush(self):
        self.original_stderr.flush()
        self.buffer.seek(0)
        self.buffer.truncate(0)
    
    def __getattr__(self, name):
        return getattr(self.original_stderr, name)

# Only filter if not already filtered
if not isinstance(sys.stderr, SSLFilteredStderr):
    sys.stderr = SSLFilteredStderr(sys.stderr)

# Suppress threading exceptions for SSL errors
import threading

_original_excepthook = threading.excepthook

def _suppress_ssl_threading_errors(args):
    """Suppress SSL errors from background threads"""
    exc_type, exc_value, exc_traceback, thread = args
    if exc_type and issubclass(exc_type, (ssl.SSLError, AutoReconnect)):
        # Suppress SSL errors - they're expected with Python 3.14 and don't affect functionality
        return
    # Call original handler for other exceptions
    if _original_excepthook:
        _original_excepthook(args)
    else:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

threading.excepthook = _suppress_ssl_threading_errors
