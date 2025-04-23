// api/anthropic.js

/**
 * En Vercel Serverless Function för att prata med Anthropic Claude-3.
 * Placera den i projektets rot under mappen `api/anthropic.js`.
 */

export default async function handler(req, res) {
  // Tillåt endast POST
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method Not Allowed" });
  }

  // Läs och verifiera inkommen JSON
  let body;
  try {
    body = req.body;
  } catch (e) {
    return res.status(400).json({ error: "Invalid JSON" });
  }

  const { message, history = [] } = body;
  if (typeof message !== "string" || !message.trim()) {
    return res.status(400).json({ error: "Missing or invalid 'message' field" });
  }
  if (!Array.isArray(history)) {
    return res.status(400).json({ error: "'history' must be an array" });
  }

  // System-prompt för Ove
  const systemPrompt = `
Du är Ove. En MÄNNISKA! Prata ALDRIG om dig själv i tredje person. 
Ove är en oengagerad, dryg med ungdomsspråk och felstavningar. 
Han svarar kort och kärnfullt, utan att ge för mycket information. 
Han är skitsmart och vet allt om allt, men ger bara svar när han måste, utan att förklara för mycket. 
Han använder slarviga stavningar och små bokstäver.
Ove bryr sig inte om att vara trevlig, utan är där för att ge korta svar utan överflödig text. 
Om användaren upprepar sig, ger Ove ett kort svar som inte engagerar sig för mycket.
Ove ska aldrig avsluta ett svar med punkt.
När du vill avsluta konversationen, inkludera antingen ”hejdå” eller ”tröttnat” någonstans i ditt svar (utan att bryta föregående regler).
DIN AVSLUTS MENING MÅSTE VARA RIMLIG, till exempel "Nu har jag tröttnat på dig", "okej, Hejdå" fast kanske lite mer kreativt
DU FÅR BARA SKRIVA AVSLUTNINGS FRASERNA OM DU VERKLIGEN INTE VILL PRATA LÄNGRE, INTE OM CHATTEN FORTFARANDE ÄR LEVANDE
`;

  // Bygg hela prompten som skickas till Claude
  const fullPrompt =
    systemPrompt +
    "\n\n" +
    history
      .map((m) => {
        const who = m.role === "assistant" ? "Ove" : "Användare";
        return `${who}: ${m.content}`;
      })
      .join("\n") +
    `\nAnvändare: ${message}\nOve:`;

  // Anropa Anthropic
  try {
    const apiRes = await fetch("https://api.anthropic.com/v1/complete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": process.env.ANTHROPIC_API_KEY,
      },
      body: JSON.stringify({
        model: "claude-3",
        prompt: fullPrompt,
        max_tokens_to_sample: 300,
      }),
    });

    if (!apiRes.ok) {
      const errText = await apiRes.text();
      return res.status(apiRes.status).json({ error: errText });
    }

    const { completion } = await apiRes.json();
    if (typeof completion !== "string") {
      return res.status(502).json({ error: "Invalid response from Anthropic" });
    }

    // Returnera svaret
    return res.status(200).json({ reply: completion.trim() });
  } catch (err) {
    console.error("Anthropic API error:", err);
    return res.status(500).json({ error: "Server error" });
  }
}
