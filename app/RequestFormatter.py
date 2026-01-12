import logging


class RequestFormatter(logging.Formatter):
    def format(self, record):
        from flask import g, has_request_context

        if has_request_context():
            record.request_token = getattr(g, "request_token", "anon")
        else:
            record.request_token = "no-request"
        return super().format(record)
