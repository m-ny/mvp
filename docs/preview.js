/**
 * Demo workspace: select clients, then expand generated outreach output.
 */

const clientList = document.getElementById("client-list");
const outputList = document.getElementById("output-list");
const outputEmpty = document.getElementById("output-empty");
const emptyState = document.getElementById("empty-state");
const selectedCount = document.getElementById("selected-count");
const totalCount = document.getElementById("total-count");
const generateBtn = document.getElementById("generate-outreach");
const selectFirstBtn = document.getElementById("select-first");
const clearSelectionBtn = document.getElementById("clear-selection");

let allItems = [];
let hasGenerated = false;
const selectedIds = new Set();

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

function shortText(value, max = 86) {
  const text = String(value || "").trim();
  if (text.length <= max) return text;
  return `${text.slice(0, max)}...`;
}

function renderDrafts(item) {
  const drafts = item.wechat_drafts || [];
  if (drafts.length === 0) {
    return '<p class="muted-copy">No draft available in this sample.</p>';
  }
  return drafts
    .map(
      (d, i) => `
        <div class="draft-block">
          <div class="draft-label">Draft ${i + 1}${d.tone ? ` · ${esc(d.tone)}` : ""}</div>
          <p class="draft-text">${esc(d.message || "")}</p>
        </div>`
    )
    .join("");
}

function renderEvidence(item) {
  const ev = item.evidence_used || [];
  if (ev.length === 0) {
    return '<p class="muted-copy">The suggestion is based on the client profile and recent interests.</p>';
  }
  return `<ul class="evidence-list">${ev.slice(0, 3).map((x) => `<li>${esc(String(x))}</li>`).join("")}</ul>`;
}

function setSelected(id, value) {
  if (value) selectedIds.add(id);
  else selectedIds.delete(id);
  hasGenerated = false;
  render();
}

function renderClientList(items) {
  clientList.innerHTML = "";
  items.forEach((item, idx) => {
    const selected = selectedIds.has(item.client_id);
    const row = document.createElement("label");
    row.className = `client-row${selected ? " is-selected" : ""}`;
    row.innerHTML = `
      <input type="checkbox" ${selected ? "checked" : ""} aria-label="Select ${esc(item.name || item.client_id)}" />
      <span class="client-index">${String(idx + 1).padStart(2, "0")}</span>
      <span class="client-copy">
        <span class="client-name-line">
          <strong>${esc(item.name || item.client_id)}</strong>
          ${item.vip_tier ? `<em>${esc(item.vip_tier)}</em>` : ""}
        </span>
        <span class="client-meta">${esc(item.persona_tag || "Client profile")}</span>
        <span class="client-summary">${esc(shortText(item.summary || item.best_angle || "", 70))}</span>
      </span>
    `;
    row.querySelector("input").addEventListener("change", (e) => {
      setSelected(item.client_id, e.target.checked);
    });
    clientList.appendChild(row);
  });
}

function renderOutput(items) {
  const selectedItems = items.filter((item) => selectedIds.has(item.client_id));
  selectedCount.textContent = selectedItems.length;
  generateBtn.disabled = selectedItems.length === 0;
  outputEmpty.hidden = hasGenerated && selectedItems.length > 0;
  if (!hasGenerated || selectedItems.length === 0) {
    outputList.innerHTML = "";
    return;
  }
  outputList.innerHTML = selectedItems
    .map(
      (item) => `
        <article class="output-card">
          <div class="output-top">
            <div>
              <p class="output-client">${esc(item.name || item.client_id)}</p>
              <p class="output-meta">${esc(item.persona_tag || "Client profile")}</p>
            </div>
            <span class="confidence ${esc(String(item.confidence || "medium").toLowerCase())}">
              Ready to review
            </span>
          </div>

          <div class="strategy-box">
            <p class="label">Recommended approach</p>
            <h3>${esc(item.best_angle || "Personalized follow-up")}</h3>
            <p>${esc(item.angle_summary || "No strategy summary available.")}</p>
          </div>

          <div class="split">
            <section>
              <p class="label">Message options</p>
              ${renderDrafts(item)}
            </section>
            <section>
              <p class="label">Why this feels relevant</p>
              <p class="client-note">${esc(item.summary || "Based on the client profile, recent interest, and preferred communication context.")}</p>
              ${renderEvidence(item)}
            </section>
          </div>

          <div class="next-step">
            <span>Suggested next action</span>
            <p>${esc(item.next_step || "Follow up based on client response.")}</p>
          </div>
        </article>`
    )
    .join("");
}

function render() {
  renderClientList(allItems);
  renderOutput(allItems);
}

async function load() {
  try {
    const res = await fetch("preview_data.json", { cache: "no-store" });
    if (!res.ok) throw new Error(String(res.status));
    const items = await res.json();
    if (!Array.isArray(items) || items.length === 0) {
      emptyState.hidden = false;
      emptyState.textContent = "preview_data.json 为空，请先运行 python3 build_preview_data.py";
      return;
    }
    emptyState.hidden = true;
    allItems = items;
    totalCount.textContent = items.length;
    render();
  } catch (e) {
    emptyState.hidden = false;
    emptyState.innerHTML =
      "无法加载 preview_data.json。<br/>请在本目录执行 <code>python3 build_preview_data.py</code>，再用 <code>python3 -m http.server 8765</code> 打开本页。";
    console.error(e);
  }
}

selectFirstBtn.addEventListener("click", () => {
  selectedIds.clear();
  allItems.slice(0, 3).forEach((item) => selectedIds.add(item.client_id));
  hasGenerated = false;
  render();
});

generateBtn.addEventListener("click", () => {
  if (selectedIds.size === 0) return;
  hasGenerated = true;
  render();
});

clearSelectionBtn.addEventListener("click", () => {
  selectedIds.clear();
  hasGenerated = false;
  render();
});

load();
