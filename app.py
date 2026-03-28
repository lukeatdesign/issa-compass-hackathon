from flask import Flask, request, jsonify
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

app = Flask(__name__)
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

def get_prompt():
    print("TESTCASE1")
    print(f"URL: {SUPABASE_URL}/rest/v1/ai_prompts?limit=1")
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/ai_prompts",
        headers=supabase_headers()
    )
    
    data = response.json()
    print(f"DATA: {data}")
    return data[0]["prompt"]

def save_prompt(new_prompt):
    requests.post(
        f"{SUPABASE_URL}/rest/v1/ai_prompts",
        headers=supabase_headers(),
        json={"prompt": new_prompt}
    )

@app.route('/')
def hello():
    return 'Issa Compass AI Server is running!!'

@app.route('/generate-reply', methods=['POST'])
def generate_reply():
    data = request.json
    client_message = data.get('clientSequence', '')
    chat_history = data.get('chatHistory', [])

    system_prompt = get_prompt()

    messages = []
    for msg in chat_history:
        role = 'assistant' if msg['role'] == 'consultant' else 'user'
        messages.append({'role': role, 'content': msg['message']})
    messages.append({'role': 'user', 'content': client_message})

    response = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=1024,
        system=system_prompt,
        messages=messages
    )

    return jsonify({'aiReply': response.content[0].text})

@app.route('/improve-ai', methods=['POST'])
def improve_ai():
    data = request.json
    client_message = data.get('clientSequence', '')
    chat_history = data.get('chatHistory', [])
    consultant_reply = data.get('consultantReply', '')

    current_prompt = get_prompt()

    messages = []
    for msg in chat_history:
        role = 'assistant' if msg['role'] == 'consultant' else 'user'
        messages.append({'role': role, 'content': msg['message']})
    messages.append({'role': 'user', 'content': client_message})

    predicted = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=1024,
        system=current_prompt,
        messages=messages
    )
    predicted_reply = predicted.content[0].text

    editor_prompt = f"""You are an AI prompt editor. Compare these two replies and improve the system prompt.

CURRENT SYSTEM PROMPT:
{current_prompt}

CLIENT MESSAGE:
{client_message}

PREDICTED AI REPLY:
{predicted_reply}

REAL CONSULTANT REPLY:
{consultant_reply}

Analyze the differences. Update the system prompt to be better.
Return ONLY valid JSON like this: {{"prompt": "updated prompt here"}}"""

    editor_response = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=2048,
        messages=[{'role': 'user', 'content': editor_prompt}]
    )

    clean = editor_response.content[0].text.replace('```json', '').replace('```', '').strip()
    updated = json.loads(clean)
    new_prompt = updated['prompt']
    save_prompt(new_prompt)

    return jsonify({
        'predictedReply': predicted_reply,
        'updatedPrompt': new_prompt
    })

@app.route('/improve-ai-manually', methods=['POST'])
def improve_ai_manually():
    data = request.json
    instructions = data.get('instructions', '')
    current_prompt = get_prompt()

    editor_prompt = f"""You are an AI prompt editor.

CURRENT PROMPT:
{current_prompt}

INSTRUCTIONS TO APPLY:
{instructions}

Update the prompt based on these instructions.
Return ONLY valid JSON like this: {{"prompt": "updated prompt here"}}"""

    response = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=2048,
        messages=[{'role': 'user', 'content': editor_prompt}]
    )

    clean = response.content[0].text.replace('```json', '').replace('```', '').strip()
    updated = json.loads(clean)
    new_prompt = updated['prompt']
    save_prompt(new_prompt)

    return jsonify({'updatedPrompt': new_prompt})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 