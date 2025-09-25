#!/usr/bin/env python3
"""
Telegram Web App for Speech-to-Text
برای deploy کردن روی سرویس‌های ابری مثل Render.com
"""

import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# HTML برای Telegram Web App
TELEGRAM_WEBAPP_HTML = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تبدیل گفتار به متن</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f2f5;
            color: #333;
            direction: rtl;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #0088cc;
            margin: 0;
            font-size: 24px;
        }
        .controls {
            text-align: center;
            margin-bottom: 20px;
        }
        .btn {
            background: #0088cc;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            margin: 5px;
        }
        .btn:hover {
            background: #006699;
        }
        .btn-danger {
            background: #dc3545;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .status {
            text-align: center;
            margin: 20px 0;
            font-size: 16px;
            color: #666;
        }
        .text-area {
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 15px;
            margin: 10px 0;
            min-height: 100px;
            background: #f9f9f9;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }
        .stat {
            text-align: center;
            background: #e9ecef;
            padding: 10px;
            border-radius: 6px;
            flex: 1;
            margin: 0 5px;
        }
        .stat-number {
            font-size: 20px;
            font-weight: bold;
            color: #0088cc;
        }
        .pulse {
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 تبدیل گفتار به متن</h1>
            <p>ربات تلگرام هوشمند</p>
        </div>

        <div class="controls">
            <button id="startBtn" class="btn">🎙️ شروع به صحبت</button>
            <button id="stopBtn" class="btn btn-danger" style="display:none;">⏹️ توقف</button>
        </div>

        <div id="status" class="status">وضعیت: آماده 🟢</div>

        <div>
            <label>📝 متن تشخیص داده شده:</label>
            <div id="transcription" class="text-area"></div>
        </div>

        <div>
            <label>🔄 متن در حال تشخیص:</label>
            <div id="interimTranscription" class="text-area" style="min-height: 60px;"></div>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="stat-number" id="wordCount">0</div>
                <div>کلمه</div>
            </div>
            <div class="stat">
                <div class="stat-number" id="charCount">0</div>
                <div>کاراکتر</div>
            </div>
            <div class="stat">
                <div class="stat-number" id="timeCount">0</div>
                <div>ثانیه</div>
            </div>
        </div>

        <div class="controls">
            <button id="sendBtn" class="btn">📤 ارسال به تلگرام</button>
            <button id="clearBtn" class="btn btn-danger">🗑️ پاک کردن</button>
        </div>
    </div>

    <script>
        // تنظیم Telegram Web App
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();

        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const statusEl = document.getElementById('status');
        const transcriptionEl = document.getElementById('transcription');
        const interimTranscriptionEl = document.getElementById('interimTranscription');
        const sendBtn = document.getElementById('sendBtn');
        const clearBtn = document.getElementById('clearBtn');
        const wordCountEl = document.getElementById('wordCount');
        const charCountEl = document.getElementById('charCount');
        const timeCountEl = document.getElementById('timeCount');

        let isRecognizing = false;
        let final_transcript = '';
        let startTime = null;
        let recognition = null;

        // بررسی پشتیبانی مرورگر
        window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!window.SpeechRecognition) {
            statusEl.textContent = 'متأسفانه مرورگر شما از Web Speech API پشتیبانی نمی‌کند.';
            startBtn.disabled = true;
        } else {
            recognition = new SpeechRecognition();
            recognition.interimResults = true;
            recognition.lang = 'fa-IR';
            recognition.continuous = true;

            recognition.onstart = () => {
                isRecognizing = true;
                startTime = Date.now();
                statusEl.textContent = 'وضعیت: در حال گوش دادن... 🔴';
                startBtn.style.display = 'none';
                stopBtn.style.display = 'inline-block';
                stopBtn.classList.add('pulse');
            };

            recognition.onend = () => {
                if (isRecognizing) {
                    recognition.start();
                } else {
                    statusEl.textContent = 'وضعیت: آماده 🟢';
                    startBtn.style.display = 'inline-block';
                    stopBtn.style.display = 'none';
                    stopBtn.classList.remove('pulse');
                }
            };
            
            recognition.onerror = (event) => {
                statusEl.textContent = `خطا: ${event.error}`;
                console.error('Speech Recognition Error:', event);
                isRecognizing = false;
                startBtn.style.display = 'inline-block';
                stopBtn.style.display = 'none';
                stopBtn.classList.remove('pulse');
            };

            recognition.onresult = (event) => {
                let interim_transcript = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        final_transcript += event.results[i][0].transcript + ' ';
                        interimTranscriptionEl.textContent = '';
                    } else {
                        interim_transcript += event.results[i][0].transcript;
                    }
                }
                transcriptionEl.textContent = final_transcript;
                interimTranscriptionEl.textContent = interim_transcript;
                updateStats();
            };
        }

        startBtn.onclick = () => {
            final_transcript = '';
            interimTranscriptionEl.textContent = '';
            recognition.start();
        };

        stopBtn.onclick = () => {
            recognition.stop();
            isRecognizing = false;
        };

        clearBtn.onclick = () => {
            final_transcript = '';
            transcriptionEl.textContent = '';
            interimTranscriptionEl.textContent = '';
            updateStats();
        };

        sendBtn.onclick = () => {
            if (final_transcript.trim()) {
                // ارسال به تلگرام
                tg.sendData(JSON.stringify({
                    type: 'speech_to_text',
                    text: final_transcript.trim(),
                    timestamp: Date.now()
                }));
                
                tg.showAlert('✅ متن با موفقیت ارسال شد!');
                console.log('Sent to Telegram:', final_transcript.trim());
            } else {
                tg.showAlert('لطفاً ابتدا متن را تشخیص دهید!');
            }
        };

        function updateStats() {
            const text = final_transcript.trim();
            const words = text.split(/\\s+/).filter(word => word.length > 0);
            const chars = text.length;
            const time = startTime ? Math.floor((Date.now() - startTime) / 1000) : 0;
            
            wordCountEl.textContent = words.length;
            charCountEl.textContent = chars;
            timeCountEl.textContent = time;
        }

        setInterval(updateStats, 1000);

        // تنظیم تم تلگرام
        document.body.style.backgroundColor = tg.themeParams.bg_color || '#f0f2f5';
        document.body.style.color = tg.themeParams.text_color || '#333';
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """صفحه اصلی"""
    return TELEGRAM_WEBAPP_HTML

@app.route('/telegram_webapp.html')
def telegram_webapp():
    """Telegram Web App"""
    return TELEGRAM_WEBAPP_HTML

@app.route('/api/status')
def status():
    """وضعیت سرور"""
    return jsonify({'status': 'running', 'message': 'سرور Telegram Web App فعال است'})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
