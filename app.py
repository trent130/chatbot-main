from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from twilio.rest import Client
from twilio.request_validator import RequestValidator
import openai
import stripe
from datetime import datetime
import os
from dotenv import load_dotenv
from models import Base, Appointment, engine, SessionLocal
from transformers import pipeline
import json

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Initialize Twilio client
twilio_client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Initialize the medical QA model
medical_qa = pipeline('question-answering', model='microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext')

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create database tables
Base.metadata.create_all(bind=engine)

def validate_twilio_request(request: Request):
    validator = RequestValidator(os.getenv('TWILIO_AUTH_TOKEN'))
    form_data = await request.form()
    signature = request.headers.get('X-Twilio-Signature', '')
    url = str(request.url)
    return validator.validate(url, form_data, signature)

def process_medical_query(query: str):
    # Use the medical QA model to process general medical queries
    context = "Medical knowledge base context here..."  # You would need to provide appropriate medical context
    result = medical_qa(question=query, context=context)
    return result['answer']

def create_payment_session(amount: float):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'Medical Appointment',
                },
                'unit_amount': int(amount * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url='https://your-domain.com/success',
        cancel_url='https://your-domain.com/cancel',
    )
    return session

@app.post("/webhook")
async def webhook_handler(request: Request, db: Session = Depends(get_db)):
    # Validate the request is from Twilio
    if not validate_twilio_request(request):
        raise HTTPException(status_code=400, detail="Invalid Twilio signature")

    form_data = await request.form()
    incoming_msg = form_data.get('Body', '').lower()
    sender = form_data.get('From', '')

    # Initialize response
    response = ""

    try:
        if "appointment" in incoming_msg:
            # Handle appointment request
            payment_session = create_payment_session(50.00)  # $50 appointment fee
            response = (
                "To book an appointment, please complete the payment using this link: "
                f"{payment_session.url}\n"
                "Once payment is confirmed, we'll help you schedule your appointment."
            )
        
        elif any(keyword in incoming_msg for keyword in ["symptom", "disease", "medical", "health"]):
            # Handle medical query
            response = process_medical_query(incoming_msg)
        
        else:
            # Use OpenAI for general conversation
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful medical assistant."},
                    {"role": "user", "content": incoming_msg}
                ]
            )
            response = completion.choices[0].message.content

        # Send response via Twilio
        twilio_client.messages.create(
            body=response,
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            to=sender
        )

        return {"status": "success"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stripe-webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            # Here you would implement the logic to confirm the appointment
            # and send a WhatsApp message to the user with next steps
            
            # Create appointment record
            new_appointment = Appointment(
                user_phone=session['metadata'].get('phone'),
                payment_status='completed',
                amount_paid=session['amount_total'] / 100
            )
            db.add(new_appointment)
            db.commit()

            # Send confirmation message via WhatsApp
            twilio_client.messages.create(
                body="Your payment has been confirmed! Please reply with your preferred appointment date and time.",
                from_=os.getenv('TWILIO_PHONE_NUMBER'),
                to=session['metadata'].get('phone')
            )

        return {"status": "success"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
