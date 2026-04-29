from datetime import datetime, timezone


class PaymentBlockedError(Exception):
    def __init__(self, result: dict):
        self.result = result
        super().__init__(result["reason"])
