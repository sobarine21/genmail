import os
import pickle
import streamlit as st
import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.compose']

# Configure the API key securely from Streamlit's secrets
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def authenticate_gmail():
    """Authenticate and create the Gmail service."""
    creds = None
    # Using Streamlit Secrets to fetch the Gmail OAuth credentials
    if "google_credentials" in st.secrets:
        creds = Credentials.from_authorized_user_info(st.secrets["google_credentials"], SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(st.secrets["google_credentials"], SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials to a token file
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def get_latest_email(service):
    """Get the most recent unread email."""
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
    messages = results.get('messages', [])
    
    if not messages:
        return None
    
    message = service.users().messages().get(userId='me', messageId=messages[0]['id']).execute()
    return message

def create_draft_reply(service, message, reply_text):
    """Create a draft reply for the received email."""
    reply = {
        'message': {
            'threadId': message['threadId'],
            'labelIds': ['INBOX'],
            'payload': {
                'headers': [{'name': 'To', 'value': message['payload']['headers'][0]['value']}],
                'body': {
                    'data': reply_text
                }
            }
        }
    }
    draft = service.users().messages().create(userId='me', body=reply).execute()
    return draft

# Streamlit UI setup
st.title("Email Reply Generator")
st.write("This app fetches unread emails, generates a reply using AI, and saves the draft.")

# Initialize Gmail service
service = authenticate_gmail()

# Fetch latest unread email
latest_email = get_latest_email(service)

if latest_email:
    st.write("Latest Email:")
    st.write(f"Subject: {latest_email['payload']['headers'][1]['value']}")
    st.write(f"From: {latest_email['payload']['headers'][0]['value']}")
    
    # Prompt input field
    prompt = st.text_input("Generate Reply to Email:", "Write a polite response to this email.")
    
    # Button to generate response
    if st.button("Generate Reply"):
        try:
            # Load and configure the model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Generate response from the model
            response = model.generate_content(prompt)
            
            # Display response in Streamlit
            st.write("Generated Reply:")
            st.write(response.text)
            
            # Option to save the reply as a draft
            if st.button("Save Draft"):
                draft = create_draft_reply(service, latest_email, response.text)
                st.success(f"Draft saved successfully with ID: {draft['id']}")
        
        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.write("No new unread emails.")
