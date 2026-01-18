import os

from twilio.rest import Client


def send_sms(message, to_number=None):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    to_number = to_number or os.environ.get("TWILIO_TO_NUMBER")

    if not (account_sid and auth_token and from_number and to_number):
        raise ValueError("Missing Twilio credentials or destination number.")

    client = Client(account_sid, auth_token)
    sms = client.messages.create(body=message, from_=from_number, to=to_number)
    return {"sid": sms.sid, "status": sms.status}
