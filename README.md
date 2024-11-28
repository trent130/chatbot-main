# WhatsApp Medical AI Assistant

A comprehensive WhatsApp-based AI assistant that handles medical queries, appointment scheduling, and payment processing. The system uses advanced natural language processing and is trained on medical data to provide accurate responses.

## Features

- 🤖 AI-powered medical query handling
- 📅 Appointment scheduling via WhatsApp
- 💳 Integrated payment processing
- 🔒 Secure webhook implementation
- 📊 Database tracking for appointments and chat history

## System Architecture

### Components

1. **WhatsApp Integration**
   - Uses Twilio API for WhatsApp messaging
   - Webhook handling for real-time message processing

2. **AI Model**
   - Based on PubMedBERT for medical query understanding
   - Custom-trained on medical dataset
   - OpenAI integration for general conversation

3. **Payment Processing**
   - Stripe integration for secure payments
   - Webhook confirmation system
   - Automatic appointment confirmation

4. **Database**
   - SQLite database (easily upgradeable to PostgreSQL)
   - Tracks appointments and chat history
   - Maintains payment status

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   - Copy `.env.example` to `.env`
   - Fill in your API keys:
     - Twilio credentials
     - OpenAI API key
     - Stripe API keys

3. **Database Setup**
   ```bash
   # The database will be automatically created when you run the application
   python app.py
   ```

4. **Training the AI Model**

   The system includes a complete AI training pipeline for medical query handling:

   a. **Prepare Training Data**
   ```bash
   python prepare_medical_data.py
   ```
   This script:
   - Collects medical Q&A pairs from various sources
   - Formats data for training
   - Saves processed data to `medical_data/medical_qa_dataset.json`

   b. **Train the Model**
   ```bash
   python train_model.py
   ```
   The training process:
   - Uses the PubMedBERT base model
   - Fine-tunes on medical Q&A data
   - Implements custom data preprocessing
   - Saves the trained model to `medical_qa_model/`

   c. **Training Parameters**
   - Learning rate: 2e-5
   - Batch size: 16
   - Training epochs: 3
   - Weight decay: 0.01

5. **Webhook Configuration**
   - Configure Twilio webhook URL to point to `/webhook`
   - Set up Stripe webhook to point to `/stripe-webhook`
   - Ensure proper SSL certification for production

## Usage

1. **Starting the Server**
   ```bash
   python app.py
   ```

2. **Testing the WhatsApp Integration**
   - Send a message to your Twilio WhatsApp number
   - Try different types of queries:
     - Medical questions
     - Appointment requests
     - General conversation

3. **Appointment Booking Flow**
   1. User requests appointment via WhatsApp
   2. System sends payment link
   3. User completes payment
   4. System confirms and requests preferred time
   5. Appointment is scheduled in database

## Security Considerations

- All API keys stored in environment variables
- Webhook validation for both Twilio and Stripe
- Secure payment processing
- Database session management
- Input validation and sanitization

## Customization

### Training Custom Medical Model

1. **Prepare Your Data**
   - Add your medical Q&A pairs to `prepare_medical_data.py`
   - Format: question, context, and answer
   - Run data preparation script

2. **Modify Training Parameters**
   - Adjust hyperparameters in `train_model.py`
   - Customize model architecture if needed
   - Add additional training data sources

3. **Run Training**
   - Execute training script
   - Monitor training metrics
   - Evaluate model performance

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
