export const viewerStyles = `:root {
  --bg: #f4f4f4;
  --panel: #ffffff;
  --panel-2: #ededed;
  --sidebar: rgba(247, 247, 247, .96);
  --sidebar-2: #eeeeee;
  --ink: #171717;
  --muted: #6f6f6f;
  --hair: #d1d1d1;
  --accent: #4b5563;
  --accent-2: #3f3f46;
  --tool: #525252;
  --ok: #525252;
  --warn: #737373;
  --user-bubble: #e9e9e9;
  --mark: #d9d9d9;
  --shadow: 0 1px 2px rgba(0, 0, 0, .05), 0 10px 30px rgba(0, 0, 0, .07);
  --control: #ffffff;
  --control-hover: #efefef;
  --radius: 10px;
  --radius-sm: 7px;
  --ring: color-mix(in srgb, var(--accent) 28%, transparent);
}
:root[data-theme="dark"] {
  --bg: #151515;
  --panel: #1f1f1f;
  --panel-2: #242424;
  --sidebar: rgba(22, 22, 22, .96);
  --sidebar-2: #1b1b1b;
  --ink: #ededed;
  --muted: #a3a3a3;
  --hair: #343434;
  --accent: #c4c4c4;
  --accent-2: #e5e5e5;
  --tool: #c2c2c2;
  --ok: #a3a3a3;
  --warn: #b8b8b8;
  --user-bubble: #262626;
  --mark: #3a3a3a;
  --shadow: 0 1px 2px rgba(0, 0, 0, .25), 0 14px 34px rgba(0, 0, 0, .32);
  --control: #262626;
  --control-hover: #303030;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--ink);
  background:
    linear-gradient(90deg, rgba(0,0,0,.035) 1px, transparent 1px) 0 0/28px 28px,
    linear-gradient(0deg, rgba(0,0,0,.03) 1px, transparent 1px) 0 0/28px 28px,
    var(--bg);
  font-family: Avenir Next, Aptos, ui-sans-serif, system-ui, sans-serif;
  letter-spacing: 0;
}
button, input, select { font: inherit; letter-spacing: 0; }
#app { display: grid; grid-template-columns: 324px minmax(0, 1fr); min-height: 100vh; }
aside {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
  border-right: 1px solid var(--hair);
  background: var(--sidebar);
  backdrop-filter: blur(14px);
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
aside::-webkit-scrollbar { width: 10px; }
aside::-webkit-scrollbar-thumb { background: color-mix(in srgb, var(--muted) 32%, transparent); border-radius: 999px; border: 3px solid transparent; background-clip: padding-box; }
aside::-webkit-scrollbar-thumb:hover { background: color-mix(in srgb, var(--muted) 55%, transparent); background-clip: padding-box; }
main { min-width: 0; padding: 22px clamp(16px, 4vw, 56px) 80px; }
.brand { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.brand h1 { margin: 0; font-size: 15px; font-weight: 700; line-height: 1.1; letter-spacing: .01em; }
.brand span {
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
  padding: 3px 8px;
  border: 1px solid var(--hair);
  border-radius: 999px;
  background: var(--panel-2);
}
.brand span:empty { display: none; }
.loader {
  border: 1px dashed var(--hair);
  border-radius: var(--radius);
  background: var(--sidebar-2);
  padding: 10px;
}
#file-input { width: 100%; font-size: 12px; color: var(--muted); cursor: pointer; }
#file-input::file-selector-button {
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
  background: var(--control);
  border: 1px solid var(--hair);
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  margin-right: 10px;
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease;
}
#file-input::file-selector-button:hover { background: var(--control-hover); border-color: var(--muted); }
.controls { display: grid; gap: 9px; }
.search-row { display: flex; gap: 7px; }
#search {
  width: 100%;
  border: 1px solid var(--hair);
  background: var(--control);
  color: var(--ink);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  min-height: 36px;
  transition: border-color .15s ease, box-shadow .15s ease;
}
#search::placeholder { color: var(--muted); }
.theme-select {
  width: 100%;
  border: 1px solid var(--hair);
  background: var(--control);
  color: var(--ink);
  padding: 8px 34px 8px 12px;
  min-height: 36px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23999' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.filters { display: flex; flex-wrap: wrap; gap: 6px; }
.show-system { width: 100%; }
.chip, .icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--hair);
  background: var(--control);
  color: var(--ink);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  min-height: 30px;
  font-size: 12px;
  font-weight: 500;
  transition: background .15s ease, border-color .15s ease, color .15s ease, transform .08s ease;
}
.chip:hover, .icon-btn:hover { background: var(--control-hover); border-color: var(--muted); }
.chip:active, .icon-btn:active { transform: translateY(1px); }
.chip[aria-pressed="true"] { background: var(--ink); color: var(--panel); border-color: var(--ink); }
.chip[aria-pressed="true"]:hover { background: var(--ink); border-color: var(--ink); }
.icon-btn { min-width: 36px; padding: 6px; border-radius: var(--radius-sm); color: var(--muted); }
.chip:focus-visible, .icon-btn:focus-visible, #search:focus-visible, .theme-select:focus-visible, #file-input:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--ring);
}
.meta, .stats {
  border: 1px solid var(--hair);
  border-radius: var(--radius);
  background: var(--sidebar-2);
  padding: 11px 12px;
  font-size: 11px;
  color: var(--ink);
  display: grid;
  gap: 6px;
}
.meta div, .stats div { display: flex; align-items: baseline; gap: 10px; overflow-wrap: anywhere; }
.stats div { justify-content: space-between; font-variant-numeric: tabular-nums; }
.meta div b, .stats div b {
  flex: none;
  color: var(--muted);
  font-weight: 600;
  font-size: 9.5px;
  text-transform: uppercase;
  letter-spacing: .06em;
  white-space: nowrap;
}
.timeline { display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  position: relative;
  width: 100%;
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 9px;
  align-items: baseline;
  text-align: left;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink);
  padding: 6px 9px;
  cursor: pointer;
  transition: background .12s ease;
}
.nav-item::before {
  content: "";
  position: absolute;
  left: 1px;
  top: 6px;
  bottom: 6px;
  width: 2px;
  border-radius: 2px;
  background: transparent;
  transition: background .12s ease;
}
.nav-item:hover { background: color-mix(in srgb, var(--accent) 11%, transparent); }
.nav-item:hover::before { background: var(--accent); }
.nav-item:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--ring); }
.nav-kind { color: var(--muted); font-size: 9px; text-transform: uppercase; font-weight: 700; letter-spacing: .04em; }
.nav-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11.5px; color: var(--muted); }
.nav-item:hover .nav-title { color: var(--ink); }
.header {
  max-width: 920px;
  margin: 0 auto 30px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: start;
}
.header h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.25;
  max-width: 42ch;
  overflow-wrap: anywhere;
}
.header p { margin: 5px 0 0; color: var(--muted); font-size: 12px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: end; }
.event-list { max-width: 920px; margin: 0 auto; display: grid; gap: 0; }
.event {
  background: transparent;
  border: 0;
  box-shadow: none;
  margin: 0 0 18px;
  scroll-margin-top: 18px;
}
.event:not(.reader-message):not(.work-card) {
  background: var(--panel);
  border: 1px solid var(--hair);
  box-shadow: var(--shadow);
}
.reader-message {
  display: flex;
  flex-direction: column;
}
.reader-message .event-header { display: none; }
.reader-message .body { padding: 0; }
.reader-message .body pre {
  font: 16px/1.62 Avenir Next, Aptos, ui-sans-serif, system-ui, sans-serif;
}
.message-images {
  display: grid;
  gap: 10px;
  margin: 0 0 12px;
}
.message-image {
  display: block;
  width: auto;
  max-width: min(100%, 760px);
  max-height: 560px;
  object-fit: contain;
  border: 1px solid var(--hair);
  border-radius: 14px;
  background: var(--panel-2);
  box-shadow: var(--shadow);
}
.message-image-link {
  display: inline-flex;
  width: max-content;
  max-width: 100%;
  color: var(--accent);
  border: 1px solid var(--hair);
  border-radius: 8px;
  padding: 7px 10px;
  overflow-wrap: anywhere;
}
.reader-message[data-speaker="user"] .message-images {
  justify-items: end;
}
.reader-message[data-speaker="user"] .message-image {
  max-width: 100%;
  box-shadow: none;
}
.markdown {
  font: 16px/1.62 Avenir Next, Aptos, ui-sans-serif, system-ui, sans-serif;
  overflow-wrap: anywhere;
}
.markdown > :first-child { margin-top: 0; }
.markdown > :last-child { margin-bottom: 0; }
.markdown p { margin: 0 0 14px; }
.markdown h1, .markdown h2, .markdown h3 {
  margin: 24px 0 10px;
  line-height: 1.25;
  font-size: 1.08em;
}
.markdown ul, .markdown ol {
  margin: 0 0 14px;
  padding-left: 1.35em;
}
.markdown li { margin: 3px 0; }
.markdown code {
  font: .92em/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--panel-2);
  border-radius: 5px;
  padding: 1px 5px;
}
.markdown pre {
  margin: 0 0 14px;
  padding: 10px 12px;
  background: var(--panel-2);
  border: 1px solid var(--hair);
  border-radius: 6px;
  overflow: auto;
  white-space: pre-wrap;
}
.markdown pre code {
  background: transparent;
  border-radius: 0;
  padding: 0;
}
.markdown a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }
.reader-message[data-speaker="user"] {
  align-items: flex-end;
  margin: 6px 0 34px;
}
.reader-message[data-speaker="user"] .body {
  max-width: min(720px, 78%);
  background: var(--user-bubble);
  border-radius: 20px;
  padding: 12px 16px;
}
.reader-message[data-speaker="assistant"] {
  margin: 0 0 20px;
}
.reader-message[data-speaker="assistant"] .body {
  max-width: 900px;
}
.work-card {
  color: var(--muted);
  margin: -2px 0 18px;
  box-shadow: none;
}
.work-card details { border-top: 0; }
.work-card summary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  padding: 2px 0 8px;
  font-size: 14px;
}
.work-card summary:hover { color: var(--ink); }
.work-summary { font-weight: 600; color: inherit; }
.work-counts { color: var(--muted); font-size: 12px; }
.work-items {
  display: grid;
  gap: 6px;
  padding: 6px 0 12px 22px;
  border-left: 1px solid var(--hair);
}
.work-item {
  background: transparent;
}
.work-item-head {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 8px;
  align-items: baseline;
  padding: 4px 0;
  color: var(--muted);
}
.work-item .badge {
  border: 0;
  justify-content: start;
  padding: 0;
  min-height: 0;
}
.work-item .body { padding: 2px 0 10px; }
.work-item pre { color: var(--muted); }
.event.hidden { display: none; }
.event-header {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: baseline;
  padding: 10px 12px;
  border-bottom: 1px solid var(--hair);
}
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  border: 1px solid var(--hair);
  color: var(--muted);
  padding: 3px 7px;
  font-size: 11px;
  text-transform: uppercase;
}
.event[data-kind="tool_call"] .badge, .event[data-kind="tool_result"] .badge { color: var(--tool); border-color: var(--muted); }
.event[data-kind="reasoning"] .badge { color: var(--warn); border-color: var(--muted); }
.event[data-status="error"] .badge { color: var(--accent-2); border-color: var(--accent-2); }
.event-title { min-width: 0; font-weight: 700; overflow-wrap: anywhere; }
.time { color: var(--muted); font-size: 12px; white-space: nowrap; }
.body { padding: 14px 16px; }
.body.system-preview pre {
  max-height: 48vh;
  overflow: auto;
}
details { border-top: 1px solid var(--hair); }
summary { cursor: pointer; color: var(--accent); padding: 10px 16px; }
pre {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 12px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.body pre { font-size: 13px; }
.raw pre { padding: 0 16px 16px; color: var(--muted); }
.warnings {
  margin-bottom: 20px;
  padding: 16px;
  border: 1px solid var(--hair);
  border-radius: var(--radius-sm);
  background: var(--panel-2);
  overflow-wrap: anywhere;
}
.warnings ul { margin: 8px 0 0; padding-left: 20px; }
mark { background: var(--mark); color: var(--ink); padding: 0 1px; }
.empty {
  max-width: 760px;
  margin: 100px auto;
  border: 1px dashed var(--hair);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 28px;
}
@media (max-width: 860px) {
  #app { grid-template-columns: 1fr; }
  aside { position: relative; height: auto; border-right: 0; border-bottom: 1px solid var(--hair); }
  .event-header { grid-template-columns: 1fr; gap: 6px; }
  .header { display: block; }
  .actions { justify-content: start; margin-top: 12px; }
}
`;
