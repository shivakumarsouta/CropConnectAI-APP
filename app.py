from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import random
from gtts import gTTS
import io
import os
import google.generativeai as genai
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Configure Gemini API
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBTdhCdp4WShV0NTdokIBp0CZIaXmgqy80")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")
chat = model.start_chat()

# In-memory storage for OTPs and registered users
otp_storage = {}
registered_users = set()

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/prices')
def login():
    return render_template('prices.html')

@app.route('/about')
def terms():
    return render_template('about.html')

@app.route('/rotation')
def rotation():
    return render_template('rotate.html')

@app.route('/fertilizers')
def fertilizers():
    return render_template('fertilizers.html')

@app.route('/weather')
def weather():
    return render_template('weather.html')

@app.route('/account')
def account():
    return render_template('account.html')

@app.route('/community')
def community():
    return render_template('community.html')

@app.route('/bot')
def bot():
    return render_template('bot.html')

# OTP routes
@app.route('/send_otp_register', methods=['POST'])
def send_otp_register():
    data = request.get_json()
    mobile = data['mobile']
    otp = random.randint(100000, 999999)
    otp_storage[mobile] = otp
    return jsonify({'success': True, 'otp': otp})

@app.route('/verify_otp_register', methods=['POST'])
def verify_otp_register():
    data = request.get_json()
    mobile = data['mobile']
    entered_otp = data['otp']
    if otp_storage.get(mobile) == int(entered_otp):
        registered_users.add(mobile)
        del otp_storage[mobile]
        return jsonify({'success': True, 'message': 'Registration completed'})
    return jsonify({'success': False, 'message': 'Invalid OTP'})

@app.route('/send_otp_login', methods=['POST'])
def send_otp_login():
    data = request.get_json()
    mobile = data['mobile']
    if mobile not in registered_users:
        return jsonify({'success': False, 'message': 'No account found, Register now'})
    otp = random.randint(100000, 999999)
    otp_storage[mobile] = otp
    return jsonify({'success': True, 'otp': otp})

@app.route('/verify_otp_login', methods=['POST'])
def verify_otp_login():
    data = request.get_json()
    mobile = data['mobile']
    entered_otp = data['otp']
    if otp_storage.get(mobile) == int(entered_otp):
        del otp_storage[mobile]
        return jsonify({'success': True, 'message': 'Login successful'})
    return jsonify({'success': False, 'message': 'Invalid OTP'})

# TTS API
@app.route('/tts', methods=['POST'])
def tts():
    data = request.get_json()
    text = data['text']
    lang = data['lang'].split('-')[0]
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        audio = io.BytesIO()
        tts.write_to_fp(audio)
        audio.seek(0)
        return send_file(audio, mimetype='audio/mp3')
    except Exception as e:
        print(f"TTS error: {e}")
        return jsonify({'success': False, 'message': 'TTS failed'}), 500

# Gemini API for Q&A
@app.route('/api/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question')
    language = data.get('language', 'en-IN')

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    try:
        # Craft prompt for structured, clean response
        prompt = (
            f"You are an agricultural expert focused on crops grown in India. "
            f"Provide concise and accurate information about fertilizers and pest management for the crop mentioned in the question. "
            f"Return the response as a JSON object with fields: fertilizers, application_time, common_pests, prevention. "
            f"Do not use Markdown symbols like ** or * in the response. "
            f"Answer in {'Telugu' if language == 'te-IN' else 'English'}: {question}"
        )
        response = chat.send_message(prompt)
        response_text = response.text.strip()

        # Clean and parse response
        response_text = re.sub(r'```json|```', '', response_text).strip()
        try:
            data = eval(response_text)  # Safely parse JSON-like string
            if not all(key in data for key in ['fertilizers', 'application_time', 'common_pests', 'prevention']):
                raise ValueError("Incomplete response")
            return jsonify(data)
        except:
            # Fallback: parse text manually if JSON parsing fails
            lines = response_text.split('\n')
            data = {
                'fertilizers': 'Not available',
                'application_time': 'Not available',
                'common_pests': 'Not available',
                'prevention': 'Not available'
            }
            for line in lines:
                line = line.strip()
                if line.startswith('Fertilizers:'):
                    data['fertilizers'] = line.replace('Fertilizers:', '').strip()
                elif line.startswith('Application Time:'):
                    data['application_time'] = line.replace('Application Time:', '').strip()
                elif line.startswith('Common Pests:'):
                    data['common_pests'] = line.replace('Common Pests:', '').strip()
                elif line.startswith('Prevention:'):
                    data['prevention'] = line.replace('Prevention:', '').strip()
            return jsonify(data)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return jsonify({'error': f'Failed to fetch answer: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)