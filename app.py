from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from twilio.rest import Client
from twilio.request_validator import RequestValidator
import openai
from datetime import datetime
import os
from dotenv import load_dotenv
from models import Base, Appointment, engine, SessionLocal
from transformers import pipeline
import json
from mpesa_integration import MpesaAPI

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Initialize Twilio client
twilio_client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize M-PESA
mpesa = MpesaAPI()

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
            # Format phone number for M-PESA (remove WhatsApp prefix and format for Kenyan number)
            phone_number = sender.replace('whatsapp:', '').replace('+', '')
            if phone_number.startswith('254'):
                # Initiate M-PESA payment
                amount = 1000  # Amount in KES
                reference = f"APPT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                payment_result = await mpesa.initiate_stk_push(
                    phone_number=phone_number,
                    amount=amount,
                    reference=reference
                )
                
                if payment_result.get('ResponseCode') == '0':
                    response = (
                        "I've sent an M-PESA payment request to your phone. "
                        "Please enter your PIN to complete the payment. "
                        "Once confirmed, we'll help you schedule your appointment."
                    )
                else:
                    response = (
                        "Sorry, there was an issue initiating the payment. "
                        "Please try again later or contact support."
                    )
            else:
                response = (
                    "Sorry, M-PESA payments are only available for Kenyan phone numbers. "
                    "Please provide a valid Kenyan phone number."
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

@app.post("/mpesa-callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    """Handle M-PESA payment callbacks"""
    try:
        callback_data = await request.json()
        result = mpesa.process_callback(callback_data)
        
        if result['status'] == 'success':
            # Create appointment record
            new_appointment = Appointment(
                user_phone=callback_data['Body']['stkCallback']['CallbackMetadata']['Item'][4]['Value'],
                payment_status='completed',
                amount_paid=result['amount']
            )
            db.add(new_appointment)
            db.commit()

            # Send confirmation message via WhatsApp
            twilio_client.messages.create(
                body="Your payment has been confirmed! Please reply with your preferred appointment date and time.",
                from_=os.getenv('TWILIO_PHONE_NUMBER'),
                to=f"whatsapp:+{new_appointment.user_phone}"
            )

        return {"status": "success", "message": result['message']}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
