"""Professional UI for the Digital Twin: header bar, profile sidebar, chat panel.
Edit PROFILE to change what visitors see. Everything else is styling."""

import html

import gradio as gr

PROFILE = {
    "name": "Agha Umair Ahmed",
    "initials": "AU",
    "title": "Technical Lead · AI Engineer",
    "location": "Pakistan · Remote (US / EU overlap)",
    "bio": (
        "14+ years building and scaling e-commerce platforms, web apps and backend systems. "
        "I lead teams on multi-brand Shopify + CodeIgniter platforms and build agentic AI tools."
    ),
    "stats": [("14+", "Years exp."), ("7", "Brands built"), ("2012", "Coding since")],
    "skills": ["Laravel", "CodeIgniter", "Shopify", "GraphQL", "React", "Next.js", "Python", "FastAPI", "LLM Agents", "RAG"],
    "email": "aghaumairahmed@gmail.com",
    "linkedin": "",  # e.g. "https://www.linkedin.com/in/your-handle" - leave empty to hide
    "github": "",    # e.g. "https://github.com/your-handle" - leave empty to hide
}

EXAMPLES = [
    "Give me a quick overview of your experience",
    "What's the most complex Shopify integration you've built?",
    "What AI and agentic work have you done?",
    "I'd like to discuss a role - how do we connect?",
]


def _e(s: str) -> str:
    return html.escape(s, quote=True)


def header_html() -> str:
    p = PROFILE
    return f"""
<div class="tw-header">
  <div class="tw-brand">
    <div class="tw-mono">{_e(p['initials'])}</div>
    <div>
      <div class="tw-brand-name">{_e(p['name'])}</div>
      <div class="tw-brand-sub">AI Career Assistant</div>
    </div>
  </div>
  <div class="tw-status"><span class="tw-dot"></span>Online · replies instantly</div>
</div>
"""


def sidebar_html() -> str:
    p = PROFILE
    stats = "".join(
        f'<div class="tw-stat"><div class="tw-stat-num">{_e(n)}</div><div class="tw-stat-label">{_e(l)}</div></div>'
        for n, l in p["stats"]
    )
    skills = "".join(f'<span class="tw-chip">{_e(s)}</span>' for s in p["skills"])
    links = f'<a class="tw-btn tw-btn-primary" href="mailto:{_e(p["email"])}">Email me</a>'
    if p["linkedin"]:
        links += f'<a class="tw-btn" href="{_e(p["linkedin"])}" target="_blank" rel="noopener">LinkedIn</a>'
    if p["github"]:
        links += f'<a class="tw-btn" href="{_e(p["github"])}" target="_blank" rel="noopener">GitHub</a>'
    return f"""
<div class="tw-card">
  <div class="tw-avatar">{_e(p['initials'])}</div>
  <h2 class="tw-name">{_e(p['name'])}</h2>
  <div class="tw-title">{_e(p['title'])}</div>
  <div class="tw-loc">📍 {_e(p['location'])}</div>
  <p class="tw-bio">{_e(p['bio'])}</p>
  <div class="tw-stats">{stats}</div>
  <div class="tw-section-label">Core stack</div>
  <div class="tw-chips">{skills}</div>
  <div class="tw-links">{links}</div>
  <div class="tw-note">
    <strong>About this chat</strong>
    This AI twin answers from my real experience. Anything it can't answer is sent to me directly.
    Share your email in the chat and I'll follow up personally.
  </div>
</div>
"""


def chat_placeholder() -> str:
    return f"""
<div class="tw-empty">
  <div class="tw-empty-icon">{_e(PROFILE['initials'])}</div>
  <div class="tw-empty-title">Hi, I'm {_e(PROFILE['name'].split()[0])}'s AI twin 👋</div>
  <div class="tw-empty-sub">Ask me about my experience, projects, tech stack or availability.</div>
</div>
"""


THEME = gr.themes.Base(
    primary_hue="indigo",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    radius_size="lg",
)

CSS = """
:root {
  --tw-bg: #f6f7fb;
  --tw-surface: #ffffff;
  --tw-border: #e6e8ef;
  --tw-text: #0f172a;
  --tw-muted: #64748b;
  --tw-accent: #4f46e5;
  --tw-accent-2: #0ea5e9;
  --tw-accent-soft: #eef2ff;
}
footer, .built-with, .show-api, .api-docs { display: none !important; }
html, body, gradio-app { background: var(--tw-bg) !important; }
.gradio-container {
  max-width: 1180px !important; margin: 0 auto !important; padding: 20px 24px 32px !important;
  background: transparent !important; color: var(--tw-text) !important;
}

/* Header */
.tw-header {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--tw-surface); border: 1px solid var(--tw-border); border-radius: 16px;
  padding: 14px 20px; box-shadow: 0 1px 2px rgba(15,23,42,.04);
}
.tw-brand { display: flex; align-items: center; gap: 12px; }
.tw-mono {
  width: 38px; height: 38px; border-radius: 10px; display: grid; place-items: center;
  background: linear-gradient(135deg, var(--tw-accent), var(--tw-accent-2));
  color: #fff; font-weight: 700; font-size: 14px; letter-spacing: .5px;
}
.tw-brand-name { font-weight: 700; font-size: 15px; color: var(--tw-text); }
.tw-brand-sub { font-size: 12px; color: var(--tw-muted); }
.tw-status {
  display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: #047857;
  background: #ecfdf5; border: 1px solid #a7f3d0; padding: 6px 12px; border-radius: 999px; font-weight: 500;
}
.tw-dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 0 3px rgba(16,185,129,.2); }

/* Layout */
.gradio-container .main > .wrap > .column, .gradio-container .contain > .column { gap: 16px !important; }
.tw-main { gap: 20px !important; margin-top: 0 !important; align-items: stretch !important; }
.tw-side, .tw-chat-col { padding: 0 !important; }

/* Profile card */
.tw-card {
  background: var(--tw-surface); border: 1px solid var(--tw-border); border-radius: 16px;
  padding: 26px 22px; box-shadow: 0 1px 2px rgba(15,23,42,.04); height: 100%;
}
.tw-avatar {
  width: 84px; height: 84px; border-radius: 50%; display: grid; place-items: center;
  background: linear-gradient(135deg, var(--tw-accent), var(--tw-accent-2));
  color: #fff; font-size: 28px; font-weight: 700; margin-bottom: 14px;
  box-shadow: 0 8px 24px rgba(79,70,229,.25);
}
.tw-name { margin: 0 !important; font-size: 21px !important; font-weight: 700 !important; color: var(--tw-text) !important; }
.tw-title { margin-top: 4px; font-size: 14px; font-weight: 600; color: var(--tw-accent); }
.tw-loc { margin-top: 6px; font-size: 13px; color: var(--tw-muted); }
.tw-bio { margin: 14px 0 0 !important; font-size: 13.5px; line-height: 1.6; color: #334155; }
.tw-stats {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 18px 0;
}
.tw-stat { background: #f8fafc; border: 1px solid var(--tw-border); border-radius: 12px; padding: 10px 6px; text-align: center; }
.tw-stat-num { font-size: 18px; font-weight: 700; color: var(--tw-text); }
.tw-stat-label { font-size: 11px; color: var(--tw-muted); margin-top: 2px; }
.tw-section-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: var(--tw-muted); margin-bottom: 8px; }
.tw-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.tw-chip {
  font-size: 12px; padding: 4px 10px; border-radius: 999px;
  background: var(--tw-accent-soft); color: #3730a3; border: 1px solid #e0e7ff; font-weight: 500;
}
.tw-links { display: flex; gap: 8px; margin-top: 18px; flex-wrap: wrap; }
.tw-btn {
  flex: 1; text-align: center; padding: 9px 12px; border-radius: 10px; font-size: 13px; font-weight: 600;
  border: 1px solid var(--tw-border); color: var(--tw-text) !important; text-decoration: none !important;
  background: var(--tw-surface); transition: all .15s ease;
}
.tw-btn:hover { border-color: var(--tw-accent); color: var(--tw-accent) !important; }
.tw-btn-primary { background: var(--tw-accent); border-color: var(--tw-accent); color: #fff !important; }
.tw-btn-primary:hover { background: #4338ca; color: #fff !important; }
.tw-note {
  margin-top: 18px; font-size: 12.5px; line-height: 1.55; color: var(--tw-muted);
  background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px; padding: 12px;
}
.tw-note strong { display: block; color: var(--tw-text); margin-bottom: 4px; font-size: 12.5px; }

/* Chat panel */
.tw-chat-col > div, .tw-chat-col .gr-group, .tw-chat-col .block { border: none !important; }
.tw-chat-col {
  background: var(--tw-surface) !important; border: 1px solid var(--tw-border) !important;
  border-radius: 16px !important; padding: 12px !important; box-shadow: 0 1px 2px rgba(15,23,42,.04);
}
#tw-chatbot { background: transparent !important; border: none !important; }
#tw-chatbot .message-row .message, #tw-chatbot .message { font-size: 14.5px !important; line-height: 1.6 !important; }
#tw-chatbot .bot, #tw-chatbot .message.bot {
  background: #f8fafc !important; border: 1px solid var(--tw-border) !important; color: var(--tw-text) !important;
}
#tw-chatbot .user, #tw-chatbot .message.user {
  background: var(--tw-accent) !important; border: none !important; color: #fff !important;
}
#tw-chatbot .user *, #tw-chatbot .message.user * { color: #fff !important; }
.tw-empty { text-align: center; padding: 40px 20px 10px; }
.tw-empty-icon {
  width: 56px; height: 56px; margin: 0 auto 14px; border-radius: 16px; display: grid; place-items: center;
  background: linear-gradient(135deg, var(--tw-accent), var(--tw-accent-2)); color: #fff; font-weight: 700; font-size: 18px;
}
.tw-empty-title { font-size: 19px; font-weight: 700; color: var(--tw-text); }
.tw-empty-sub { margin-top: 6px; font-size: 14px; color: var(--tw-muted); }

/* Example prompts */
.tw-chat-col .examples button, .tw-chat-col button.example {
  border: 1px solid var(--tw-border) !important; background: var(--tw-surface) !important;
  border-radius: 12px !important; color: #334155 !important; font-size: 13px !important;
  box-shadow: none !important; transition: all .15s ease;
}
.tw-chat-col .examples button:hover, .tw-chat-col button.example:hover {
  border-color: var(--tw-accent) !important; background: var(--tw-accent-soft) !important; color: #3730a3 !important;
}

/* Input */
#tw-input textarea {
  font-size: 14.5px !important; border-radius: 12px !important;
  border: 1px solid var(--tw-border) !important; background: #f8fafc !important; color: var(--tw-text) !important;
}
#tw-input textarea:focus { border-color: var(--tw-accent) !important; box-shadow: 0 0 0 3px rgba(79,70,229,.12) !important; }

.tw-foot { text-align: center; font-size: 12px; color: var(--tw-muted); margin-top: 14px; }

#tw-input { align-items: center !important; }
#tw-input button.submit-button, #tw-input .submit-button {
  background: var(--tw-accent) !important; color: #fff !important; border-radius: 10px !important;
  font-weight: 600 !important; padding: 0 18px !important; min-height: 40px !important;
}

@media (max-width: 860px) {
  .tw-main { flex-direction: column !important; }
  .tw-chat-col { order: -1; }           /* chat first on phones */
  .tw-bio, .tw-note { display: none; }  /* keep profile compact */
  #tw-chatbot { height: 460px !important; }
  .tw-status { display: none; }
  .gradio-container { padding: 12px !important; }
}
"""

JS = """
() => {
  document.body.classList.remove('dark');  // always light - looks consistent for recruiters
  document.title = 'Agha Umair Ahmed · AI Twin';
  setTimeout(() => { const t = document.querySelector('#tw-input textarea'); if (t) t.focus(); }, 400);
}
"""


def build_ui(chat_fn) -> gr.Blocks:
    with gr.Blocks(title=f"{PROFILE['name']} · AI Twin") as demo:
        gr.HTML(header_html())
        with gr.Row(elem_classes="tw-main", equal_height=True):
            with gr.Column(scale=4, min_width=300, elem_classes="tw-side"):
                gr.HTML(sidebar_html())
            with gr.Column(scale=7, elem_classes="tw-chat-col"):
                gr.ChatInterface(
                    chat_fn,
                    chatbot=gr.Chatbot(
                        elem_id="tw-chatbot",
                        show_label=False,
                        height=560,
                        placeholder=chat_placeholder(),
                        layout="bubble",
                    ),
                    textbox=gr.Textbox(
                        elem_id="tw-input",
                        placeholder="Ask about my experience, projects or availability…",
                        show_label=False,
                        container=False,
                        autofocus=True,
                        submit_btn="Send",
                    ),
                    examples=EXAMPLES,
                )
        gr.HTML('<div class="tw-foot">AI twin · answers are generated from my real resume and project notes</div>')
    return demo
