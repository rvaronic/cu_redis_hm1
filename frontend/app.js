const result = document.querySelector("#result");
const resultStatus = document.querySelector("#result-status");
const logList = document.querySelector("#log-list");

const escapePart = (value) => encodeURIComponent(String(value).trim());

async function request(method, path, body) {
  const startedAt = performance.now();
  let response;
  let data;
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await response.text();
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  } catch (error) {
    data = { error: error.message };
  }

  const duration = Math.round(performance.now() - startedAt);
  const status = response?.status ?? "NETWORK";
  appendLog({ method, path, status, duration, ok: response?.ok ?? false });
  resultStatus.textContent = `${method} ${path} · ${status}`;
  result.textContent = JSON.stringify(data, null, 2);
}

function appendLog({ method, path, status, duration, ok }) {
  const item = document.createElement("li");
  item.className = "log-entry";
  item.innerHTML = `
    <div class="log-line">
      <span class="method"></span>
      <span class="status${ok ? "" : " error"}"></span>
    </div>
    <div class="path"></div>
    <div class="duration"></div>`;
  item.querySelector(".method").textContent = method;
  item.querySelector(".status").textContent = status;
  item.querySelector(".path").textContent = path;
  item.querySelector(".duration").textContent = `${duration} ms · ${new Date().toLocaleTimeString("ru-RU")}`;
  logList.prepend(item);
}

const actions = {
  "profile-save": (data) => ["POST", `/api/players/${escapePart(data.get("id"))}`, {
    name: data.get("name"), level: Number(data.get("level")), region: data.get("region"),
  }],
  "profile-get": (data) => ["GET", `/api/players/${escapePart(data.get("id"))}`],
  "level-update": (data) => ["PATCH", `/api/players/${escapePart(data.get("id"))}/level`, { delta: Number(data.get("delta")) }],
  login: (data) => ["POST", `/api/players/${escapePart(data.get("id"))}/login`],
  "score-add": (data) => ["POST", "/api/leaderboard/score", { player_id: data.get("id"), score: Number(data.get("score")) }],
  "leaderboard-top": (data) => ["GET", `/api/leaderboard/top?limit=${escapePart(data.get("limit"))}`],
  "leaderboard-rank": (data) => ["GET", `/api/leaderboard/rank/${escapePart(data.get("id"))}`],
  "achievement-add": (data) => ["POST", `/api/players/${escapePart(data.get("id"))}/achievements`, { name: data.get("name") }],
  "achievement-check": (data) => ["GET", `/api/players/${escapePart(data.get("id"))}/achievements/${escapePart(data.get("name"))}`],
  "achievements-common": (data) => ["GET", `/api/players/${escapePart(data.get("firstId"))}/achievements/common/${escapePart(data.get("secondId"))}`],
  "batch-create": (data) => ["POST", "/api/players/batch", { players: JSON.parse(data.get("players")) }],
};

document.querySelectorAll("form[data-action]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await request(...actions[form.dataset.action](new FormData(form)));
    } catch (error) {
      resultStatus.textContent = "Ошибка формы";
      result.textContent = JSON.stringify({ error: error.message }, null, 2);
    }
  });
});

document.querySelector("#clear-log").addEventListener("click", () => logList.replaceChildren());
