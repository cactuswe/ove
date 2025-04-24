import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.1/firebase-app.js";
import {
  getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword,
  onAuthStateChanged, updateProfile, signOut
} from "https://www.gstatic.com/firebasejs/9.22.1/firebase-auth.js";
import {
  getFirestore, doc, setDoc, updateDoc, collection,
  addDoc, query, orderBy, where, onSnapshot, serverTimestamp
} from "https://www.gstatic.com/firebasejs/9.22.1/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyBRMtuyLiyRfWwq1p3e_dSE83Z7sBYJM3I",
  authDomain: "ove-ai.firebaseapp.com",
  projectId: "ove-ai",
  storageBucket: "ove-ai.firebasestorage.app",
  messagingSenderId: "200723689801",
  appId: "1:200723689801:web:5dbedb16f582048081ea98",
  measurementId: "G-PEZM6B3N58"
};
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// DOM-refs
const $ = id => document.getElementById(id);
const tabs = document.querySelectorAll(".tab");
const tabContents = document.querySelectorAll(".tab-content");
const authUI = $("authUI"), chatUI = $("chatUI");
const loginForm = $("loginForm"), registerForm = $("registerForm");
const loginId = $("loginId"), loginPw = $("loginPassword");
const btnLogin = $("btnLogin"), btnRegister = $("btnRegister");
const regDn = $("regDisplayName"), regEm = $("regEmail"), regPw = $("regPassword");
const btnLogout = $("btnLogout"), userNameEl = $("userName");
const chatWindow = $("chatWindow"), messageIn = $("messageInput");
const sendBtn = $("sendBtn"), ovePeek = $("ovePeek");
const typingIndicator = $("typingIndicator");

let chatUnsub, presenceUnsub, presenceRef;
let chatSummary = "";

// Inledande system-prompt för kontext
let chatHistory = [
  { role: "system", content: "Du är Ove, en hjälpsam assistent som svarar på svenska." }
];

// Summeringsfunktion (oförändrad)
async function summarizeMessages(messages, previousSummary="") {
  let prompt = "Sammanfatta följande konversation på max 60 ord:\n";
  if (previousSummary) prompt += "Tidigare sammanfattning:\n"+previousSummary+"\n---\n";
  messages.forEach(m => {
    const who = m.role==="assistant" ? "Ove" : "Användare";
    prompt += `${who}: ${m.content}\n`;
  });
  const r = await fetch("/api/anthropic", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ message: prompt })
  });
  const d = await r.json();
  return d.reply.trim();
}

// Rendera meddelande med alias + tid
function appendMessage(role, text, alias, timestamp) {
  const div = document.createElement("div");
  div.className = `message ${role}`;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  const timeStr = timestamp
    ? new Date(timestamp.seconds * 1000)
        .toLocaleTimeString("sv-SE",{hour:"2-digit",minute:"2-digit"})
    : "";
  meta.textContent = alias ? `${alias} • ${timeStr}` : timeStr;

  const content = document.createElement("div");
  content.className = "message-content";
  content.textContent = text;

  div.append(meta, content);
  chatWindow.append(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// “Skriv”-bubbla
function addTypingBubble() {
  const b = document.createElement("div");
  b.className = "message assistant typing";
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement("span");
    dot.className = "dot";
    b.append(dot);
  }
  chatWindow.append(b);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return b;
}

// Växla mellan login/register-tabb
tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t=>t.classList.remove("active"));
    tabContents.forEach(c=>c.classList.remove("active"));
    tab.classList.add("active");
    $(tab.dataset.tab).classList.add("active");
  });
});

// Stoppa form-submit
loginForm.addEventListener("submit", e => { e.preventDefault(); btnLogin.click(); });
registerForm.addEventListener("submit", e => { e.preventDefault(); btnRegister.click(); });

// Registrering
btnRegister.addEventListener("click", async () => {
  try {
    const cred = await createUserWithEmailAndPassword(auth, regEm.value, regPw.value);
    await updateProfile(cred.user, { displayName: regDn.value });
    await setDoc(doc(db,"users",cred.user.uid), {
      displayName: regDn.value,
      email: cred.user.email
    });
  } catch (e) {
    alert("Registreringsfel: " + e.message);
  }
});

// Login
btnLogin.addEventListener("click", async () => {
  try {
    let email = loginId.value.trim();
    if (email && !/@/.test(email)) {
      const snap = await getDocs(
        query(collection(db,"users"), where("displayName","==",email))
      );
      if (snap.empty) throw new Error("Ingen användare med det visningsnamnet");
      email = snap.docs[0].data().email;
    }
    await signInWithEmailAndPassword(auth, email, loginPw.value);
  } catch (e) {
    alert("Login-fel: " + e.message);
  }
});
btnLogout.addEventListener("click", () => signOut(auth));

// Auth + närvaro + meddelandesub
onAuthStateChanged(auth, user => {
  if (user) {
    // Närvaro
    presenceRef = doc(db,"presence","ove");
    presenceUnsub?.();
    presenceUnsub = onSnapshot(presenceRef, snap => {
      const d = snap.exists() ? snap.data() : {};
      ovePeek.classList.toggle("active", !!d.active);
      typingIndicator.classList.toggle("hidden", !d.typing);
    });

    // Visa chatten
    authUI.classList.add("hidden");
    chatUI.classList.remove("hidden");
    userNameEl.textContent = user.displayName || user.email;
    messageIn.focus();

    // Hämta meddelanden
    chatUnsub?.();
    chatUnsub = onSnapshot(
      query(collection(db,"messages"), orderBy("timestamp")),
      snap => {
        chatWindow.innerHTML = "";
        snap.forEach(d => {
          const m = d.data();
          appendMessage(m.role, m.content, m.alias, m.timestamp);
        });
      }
    );
  } else {
    chatUnsub?.(); presenceUnsub?.();
    chatUI.classList.add("hidden");
    authUI.classList.remove("hidden");
  }
});

// Skicka-meddelande
sendBtn.addEventListener("click", sendMessage);
messageIn.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

async function sendMessage() {
  const text = messageIn.value.trim();
  if (!text) return;
  // Förbättrad nämning
  const mentioned = /(^|\s)ove\b/i.test(text);

  const user = auth.currentUser;
  if (!user) return alert("Du måste vara inloggad!");

  // Aktivera Ove om nämnd
  if (mentioned && presenceRef) {
    await setDoc(presenceRef, {
      active: true,
      typing: false,
      timestamp: serverTimestamp()
    });
  }

  messageIn.value = "";
  messageIn.focus();

  // Lägg in i historik
  chatHistory.push({ role: "user", content: text });
  if (chatHistory.length > 8) {
    // Summa äldre
    const toSum = chatHistory.slice(1, chatHistory.length - 4);
    chatSummary = await summarizeMessages(toSum, chatSummary);
    chatHistory = [chatHistory[0], ...chatHistory.slice(chatHistory.length - 4)];
  }

  // Bygg prompt
  let prompt = "";
  if (chatSummary) prompt += "Tidigare sammanfattning:\n" + chatSummary + "\n---\n";
  prompt += "Senaste meddelanden:\n";
  chatHistory.forEach(m => {
    const who = m.role === "assistant" ? "Ove" : "Användare";
    prompt += `${who}: ${m.content}\n`;
  });
  prompt += `\nOvan är kontexten. Svara nu på: ${text}`;

  // Spara användarmeddelande
  await addDoc(collection(db,"messages"), {
    role:    "user",
    alias:   user.displayName || user.email,
    content: text,
    timestamp: serverTimestamp()
  });

  // Fråga Ove
  if ((mentioned || true) && presenceRef) {
    const typingBubble = addTypingBubble();
    await updateDoc(presenceRef, { typing: true, timestamp: serverTimestamp() });

    const res = await fetch("/api/anthropic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: prompt })
    });
    const d = await res.json();

    typingBubble.remove();
    const reply = d.reply.trim();

    // Visa svar direkt
    appendMessage("assistant", reply, "Ove", { seconds: Date.now()/1000 });

    // Spara Oves svar
    await addDoc(collection(db,"messages"), {
      role:    "assistant",
      alias:   "Ove",
      content: reply,
      timestamp: serverTimestamp()
    });
    await updateDoc(presenceRef, { typing: false, timestamp: serverTimestamp() });

    // Avsluta när Ove säger hejdå
    if (/hejdå|tröttnat/i.test(reply)) {
      await setDoc(presenceRef, { active: false, typing: false, timestamp: serverTimestamp() });
    }
  }
}
