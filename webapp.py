"""
Simple Chat — single-file Python web app (Flask) that hosts a web client chat UI.

How it works
- Frontend (served at /) is a simple HTML + CSS + JavaScript single page app.
- Conversation history is kept in the browser's session (localStorage) so memory is per-browser session.
- Each time the user sends a message the whole conversation (history) is POSTed to /api/chat where
  the server forwards it to OpenAI using the Python SDK. The response is returned and appended by the client.

Security & setup
- Do NOT hardcode your API key. Export it as an environment variable:
    export OPENAI_API_KEY="sk-..."
- Optional: set MODEL env var to your preferred chat model (defaults to "gpt-4o-mini").
- Install requirements: pip install flask openai python-dotenv
- Run: python cute_pastel_chat_app.py

Notes
- This file is intentionally self-contained for demo/learning. For production, add rate-limiting, auth,
  improved error handling, and do not send very long conversation histories without trimming.

"""
from flask import Flask, request, jsonify, render_template_string
import os
import openai

app = Flask(__name__)

# Read API key from environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Please set the OPENAI_API_KEY environment variable before running this app.")
openai.api_key = OPENAI_API_KEY

MODEL = os.environ.get("MODEL", "gpt-4o-mini")

INDEX_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>My AI</title>
  <style>
    :root{
      --bg:#FFF8FD;
      --card:#FFF;
      --accent:#F6D6FF;
      --muted:#8A7E86;
      --bubble-user:#D0F4FF;
      --bubble-bot:#FFF1D6;
      --radius:14px;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
    }
    html,body{height:100%;margin:0;background:linear-gradient(180deg,var(--bg),#FFF);}
    .app{max-width:820px;margin:28px auto;height:calc(100vh - 56px);display:flex;flex-direction:column;gap:12px;padding:18px}
    header{display:flex;align-items:center;gap:12px}
    .logo{width:54px;height:54px;border-radius:12px;background:linear-gradient(135deg,var(--accent),#FFE8F0);display:flex;align-items:center;justify-content:center;box-shadow:0 6px 18px rgba(0,0,0,0.06)}
    .logo span{font-weight:700;color:#7B4DAF}
    h1{font-size:20px;margin:0}
    p.lead{margin:0;color:var(--muted);font-size:13px}

    .chat-window{flex:1;background:var(--card);border-radius:18px;padding:18px;box-shadow:0 8px 30px rgba(124, 82, 153, 0.06);display:flex;flex-direction:column;overflow:hidden}
    .messages{flex:1;overflow:auto;padding-right:6px;display:flex;flex-direction:column;gap:12px}
    .msg{max-width:78%;padding:12px 14px;border-radius:12px;line-height:1.4}
    .msg.user{margin-left:auto;background:var(--bubble-user);border-bottom-right-radius:6px}
    .msg.bot{margin-right:auto;background:var(--bubble-bot);border-bottom-left-radius:6px}
    .meta{font-size:11px;color:var(--muted);margin-bottom:6px}

    .composer{display:flex;gap:8px;padding-top:10px}
    .input{flex:1;display:flex;background:linear-gradient(0deg,#fff,#fff);border-radius:12px;padding:8px}
    textarea{resize:none;border:0;outline:none;background:transparent;padding:8px;font-size:14px;width:100%;min-height:44px}
    button.send{background:linear-gradient(135deg,#8EC5FF,#BBA6FF);border:0;color:white;padding:10px 14px;border-radius:12px;font-weight:600;cursor:pointer}
    .small{font-size:12px;color:var(--muted)}

    footer{display:flex;justify-content:space-between;align-items:center}

    /* cute floating pet */
    .pet{position:absolute;right:28px;bottom:28px;width:86px;height:86px;border-radius:50%;background:linear-gradient(135deg,#FFF0F7,#FFF9E6);display:flex;align-items:center;justify-content:center;box-shadow:0 10px 30px rgba(124,82,153,0.08)}
    .pet .face{font-size:28px}

    @media(max-width:600px){.app{margin:12px;padding:12px}}
  </style>
</head>
<body>
  <div class="app">
    <header>
      <div class="logo"><span>✦</span></div>
      <div>
        <h1>My AI</h1>
        <p class="lead">Conversation is stored in your browser session and handled locally.</p>
      </div>
    </header>

    <main class="chat-window" role="main">
      <div id="messages" class="messages" aria-live="polite"></div>

      <div class="composer" role="region" aria-label="Message composer">
        <div class="input">
          <textarea id="input" placeholder="Say hi..." rows="1"></textarea>
        </div>
        <button id="send" class="send">Send</button>
      </div>
    </main>

    <footer>
      <div class="small">Model: <span id="model-name">%MODEL%</span></div>
      <div class="small">Session memory: localStorage</div>
    </footer>

    <div class="pet" title="Cute helper"><div class="face">(◕‿◕)</div></div>
  </div>

<script>
const apiBase = '/api/chat';
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send');
const modelNameEl = document.getElementById('model-name');
modelNameEl.textContent = '%MODEL%';

// Load history from session (localStorage)
function loadHistory(){
  const raw = localStorage.getItem('cute_chat_history');
  if(!raw) return [];
  try{ return JSON.parse(raw);}catch(e){return []}
}

function saveHistory(history){
  localStorage.setItem('cute_chat_history', JSON.stringify(history));
}

function renderMessages(history){
  messagesEl.innerHTML='';
  history.forEach((m)=>{
    const div = document.createElement('div');
    div.className = 'msg ' + (m.role === 'user' ? 'user' : 'bot');
    const meta = document.createElement('div'); meta.className='meta';
    meta.textContent = m.role === 'user' ? 'You' : 'Assistant';
    const content = document.createElement('div'); content.innerHTML = linkify(escapeHtml(m.content)).replace(/\n/g,'<br>');
    div.appendChild(meta);
    div.appendChild(content);
    messagesEl.appendChild(div);
  });
  // auto-scroll to bottom
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(unsafe){return unsafe.replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#039;"}[c];});}
function linkify(text){ return text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>'); }

async function sendMessage(){
  const raw = inputEl.value.trim();
  if(!raw) return;
  inputEl.value='';
  // append to local history and render
  const history = loadHistory();
  history.push({role:'user', content: raw});
  renderMessages(history);
  saveHistory(history);

  // show typing placeholder
  const typingPlaceholder = {role:'assistant', content:'…'};
  history.push(typingPlaceholder);
  renderMessages(history);

  try{
    const resp = await fetch(apiBase, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({messages: history.filter(m=>m.content !== '…')})
    });
    if(!resp.ok){
      throw new Error('Server error: '+resp.statusText);
    }
    const data = await resp.json();
    // replace last placeholder with assistant message
    history.pop();
    history.push({role:'assistant', content: data.reply});
    saveHistory(history);
    renderMessages(history);
  }catch(err){
    history.pop();
    history.push({role:'assistant', content: 'Error: '+err.message});
    saveHistory(history);
    renderMessages(history);
  }
}

sendBtn.addEventListener('click', sendMessage);
inputEl.addEventListener('keydown', (e)=>{
  if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); sendMessage(); }
});

// initialize
renderMessages(loadHistory());
</script>
</body>
</html>
"""

@app.route('/')
def index():
    # Inject model name into HTML for display
    return render_template_string(INDEX_HTML.replace('%MODEL%', MODEL))

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    messages = data.get('messages', [])
    # Validate messages: must be list of {role, content}
    if not isinstance(messages, list):
        return jsonify({'error':'invalid messages'}), 400

    # Convert browser history into OpenAI-style message list.
    # We will add a friendly system prompt to keep tone cute.
    system_prompt = (
        "You are a friendly, concise, cute assistant that replies helpfully and briefly. "
        "Keep responses pleasant and slightly playful, suitable for a pastel-themed chat UI."
    )
    openai_messages = [{'role':'system', 'content': system_prompt}]
    for m in messages:
        role = m.get('role')
        content = m.get('content')
        if role not in ('user','assistant') or not isinstance(content, str):
            continue
        openai_messages.append({'role': role, 'content': content})

    try:
        # Call OpenAI ChatCompletion
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=MODEL,
            messages=openai_messages,
            max_tokens=512,
            temperature=0.7,
        )

        reply = resp.choices[0].message.content.strip()
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # For local demo use simple server
    app.run(host='0.0.0.0', port=7860, debug=True)
