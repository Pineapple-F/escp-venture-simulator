const STATUS_MODE = "patchtst-backend";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

function parseCsv(text) {
  const lines = text.replace(/^﻿/, "").split(/\r?\n/).filter((line) => line.trim() !== "");
  if (lines.length < 2) return [];
  const headers = lines[0].split(",");
  return lines.slice(1).map((line) => {
    const cells = line.split(",");
    const row = {};
    headers.forEach((header, idx) => {
      row[header] = cells[idx] ?? "";
    });
    return row;
  });
}

async function loadMetrics(env, request) {
  try {
    const url = new URL("/processed/patchtst_metrics.csv", request.url);
    const response = await env.ASSETS.fetch(new Request(url));
    if (!response.ok) return [];
    return parseCsv(await response.text());
  } catch (_error) {
    return [];
  }
}

function extractGeminiText(result) {
  const texts = [];
  const candidates = Array.isArray(result?.candidates) ? result.candidates : [];
  for (const candidate of candidates) {
    const parts = Array.isArray(candidate?.content?.parts) ? candidate.content.parts : [];
    for (const part of parts) {
      if (part && typeof part.text === "string" && part.text) texts.push(part.text);
    }
  }
  return texts.join("\n").trim();
}

const SYSTEM_INSTRUCTION =
  "你是创投与公司金融分析助手。只根据用户提供的当前公司数据回答，使用简洁、专业、易懂的中文。" +
  "必须区分历史事实、模型预测和缺失数据；不得把未披露写成零，不得虚构公司、人员、金额或概率。" +
  "涉及预测时说明概率、时间和金额口径；涉及IPO或并购时明确这是事实还是参考概率。" +
  "答案控制在250字内，不作收益承诺，并在数据不足时直接说明需要补充什么。";

async function askGemini(payload, env) {
  const apiKey = (env.GEMINI_API_KEY || "").trim();
  if (!apiKey) return jsonResponse({ ok: false, error: "服务器尚未配置 GEMINI_API_KEY" }, 503);

  const question = String(payload?.question ?? "").trim();
  if (!question) return jsonResponse({ ok: false, error: "问题不能为空" }, 502);
  if (question.length > 500) return jsonResponse({ ok: false, error: "问题不能超过 500 个字符" }, 502);

  const model = env.GEMINI_MODEL || "gemini-3.6-flash";
  const context = payload?.context && typeof payload.context === "object" && !Array.isArray(payload.context) ? payload.context : {};
  const history = Array.isArray(payload?.history) ? payload.history : [];
  const safeHistory = history
    .slice(-6)
    .filter((item) => item && typeof item === "object" && (item.role === "user" || item.role === "assistant"));
  const contents = safeHistory.map((item) => ({
    role: item.role === "assistant" ? "model" : "user",
    parts: [{ text: String(item.content ?? "").slice(0, 1200) }],
  }));
  contents.push({
    role: "user",
    parts: [{ text: `当前公司数据：\n${JSON.stringify(context)}\n\n用户问题：${question}` }],
  });

  const requestBody = {
    systemInstruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
    contents,
    generationConfig: { maxOutputTokens: 2048 },
  };

  let result;
  try {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,
      {
        method: "POST",
        headers: { "x-goog-api-key": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      },
    );
    if (!response.ok) {
      const detail = (await response.text()).slice(0, 500);
      return jsonResponse({ ok: false, error: `Gemini API 请求失败（HTTP ${response.status}）：${detail}` }, 502);
    }
    result = await response.json();
  } catch (_error) {
    return jsonResponse({ ok: false, error: "无法连接 Gemini API，请检查服务器网络" }, 502);
  }

  const answer = extractGeminiText(result);
  if (!answer) return jsonResponse({ ok: false, error: "Gemini API 未返回可用文本" }, 502);
  return jsonResponse({ ok: true, answer, model, provider: "Gemini" });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/status" && request.method === "GET") {
      return jsonResponse({
        ok: true,
        mode: STATUS_MODE,
        metrics: await loadMetrics(env, request),
        ai: {
          configured: Boolean((env.GEMINI_API_KEY || "").trim()),
          model: env.GEMINI_MODEL || "gemini-3.6-flash",
          provider: "Gemini",
        },
      });
    }

    if (url.pathname === "/api/assistant" && request.method === "POST") {
      const length = Number(request.headers.get("Content-Length") || "0");
      if (length > 64 * 1024) return jsonResponse({ ok: false, error: "请求内容过大" }, 413);
      let payload;
      try {
        payload = await request.json();
      } catch (_error) {
        payload = {};
      }
      return askGemini(payload, env);
    }

    return env.ASSETS.fetch(request);
  },
};
