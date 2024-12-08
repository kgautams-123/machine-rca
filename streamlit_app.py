import re
import streamlit as st
import boto3
import json
import plotly
import plotly.graph_objects as go
import plotly.express as px
import io
import pandas as pd

# Set page config and layout
st.set_page_config(layout="centered")

# Custom CSS for central alignment
st.markdown("""
    <style>
        .main-header {
            text-align: center;
            padding: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Centrally aligned header
st.markdown("<h1 class='main-header'>Machine Data Analysis 💬 🧠</h1>", unsafe_allow_html=True)

# Sample questions dropdown
SAMPLE_QUESTIONS = [
    "Select a sample question",
    "Which 5 machine has got the highest dry cycle time??",
    "What is the average dry cycle time for SKUs cured using machines from HF supplier?",
    "Can you provide a list of SKUs that used steam as the curing medium in February 2024?",
    "Which five SKUs had the longest total curing time in February 2024?",
    "How many SKUs were processed using machines from LF supplier in February 2024?",
    "Which machine number had the longest dry cycle time across all SKUs in February 2024?",
    "What is the total curing time for each SKU processed in February 2024?",
    "Show me all records for SKU001, including its dry cycle and curing times."
]

# AWS Configuration
region = boto3.Session().region_name
session = boto3.Session(region_name="us-east-1")
lambda_client = session.client('lambda')

# Create columns for dropdown and checkbox
col1, col2 = st.columns([4, 1])

# Display sample questions dropdown in first column
with col1:
    selected_question = st.selectbox("Select a sample question:", SAMPLE_QUESTIONS)

# Add visualization checkbox in second column
with col2:
    enable_viz = st.checkbox('Enable Visualization', value=False)

# Get user input
prompt = st.chat_input("Ask a Question?") if not selected_question or selected_question == SAMPLE_QUESTIONS[0] else selected_question

if prompt:
    # Display user question
    st.chat_message("user").markdown(prompt)
    
    # Prepare and send request to Lambda
    payload = json.dumps({
        "agent": {
            "name": "RedshiftAnalyst",
            "version": "DRAFT",
            "id": "ZGTPTZ9GQJ",
            "alias": "TSTALIASID"
        },
        "parameters": [],
        "promptSessionAttributes": {},
        "sessionId": "863323984774850",
        "sessionAttributes": {},
        "inputText": prompt,
        "apiPath": "/generate_query_and_get_data_from_redshift",
        "httpMethod": "POST",
        "messageVersion": "1.0",
        "actionGroup": "generate_query_and_get_data_from_redshift"
    })

    # Call Lambda function
    result = lambda_client.invoke(
        FunctionName='genai-redshift-poc-k',
        Payload=payload
    )
    
    # Process response
    result = json.loads(result['Payload'].read().decode("utf-8"))
    
    # Extract response and script
    response_text = result['application/json']['answer']
    script_text = result['application/json']['script']
    
    # Clean and display response
    response_value = re.sub(r'<.*?>', '', response_text).strip()
    
    # Create assistant message container
    with st.chat_message("assistant"):
        st.markdown(response_value)
        
        # Execute script only if visualization is enabled
        if enable_viz:
            script_match = re.search(r'<Script>(.*?)</Script>', script_text, re.DOTALL)
            if script_match:
                script_content = script_match.group(1).strip()
                try:
                    exec(script_content)
                except Exception as e:
                    st.error(f"Error executing visualization: {str(e)}")