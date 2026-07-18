import logging
import threading

logger = logging.getLogger(__name__)


def send_in_background(fn, *args, **kwargs):
    """
    Run an email-sending callable in a daemon thread so the API responds
    immediately instead of blocking on SMTP. Failures are logged, not raised.
    """
    def _run():
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception('Background email send failed')

    threading.Thread(target=_run, daemon=True).start()
