from __future__ import print_function, absolute_import, unicode_literals

__all__ = ["TLSSMTPHandler"]

import logging
import logging.handlers

from .email_utils import send_msg


class TLSSMTPHandler(logging.handlers.SMTPHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            to = ", ".join(self.toaddrs)
            subj = self.getSubject(record)
            send_msg(to, msg, subj)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
