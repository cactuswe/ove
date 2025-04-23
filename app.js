import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.1/firebase-app.js";
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  onAuthStateChanged,
  updateProfile,
  signOut
} from "https://www.gstatic.com/firebasejs/9.22.1/firebase-auth.js";
import {
  getFirestore,
  doc,
  setDoc,
  getDocs,
  updateDoc,
  collection,
  addDoc,
  query,
  orderBy,
  where,
  onSnapshot,
  serverTimestamp
} from "https://www.gstatic.com/firebasejs/9.22.1/firebase-firestore.js";

// --- Initiera Firebase ---
const firebaseConfig = {
  apiKey: "AIzaSyBRMtuyLiyRfWwq1p3e_dSE83Z7sBYJM3I",
  authDomain: "ove-ai.firebaseapp.com",
  projectId: "ove-ai",
  storageBucket: "ove-ai.firebasestorage.app",
  messagingSenderId: "200723689801",
  appId: "1:200723689801:web:5dbedb16f582048081ea98",
  measurementId: "G-PEZM6B3N58"
};
const app  = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db   = getFirestore(app);

// --- Referenser & state ---
const tabs            = document.querySelectorAll(".tab");
const tabContents     = document.querySelectorAll(".tab-content");
const authUI          = document.getElementById("authUI");
const chatUI          = document.getElementById("chatUI");
const loginForm       = document.getElementById("loginForm");
const registerForm    = document.getElementById("registerForm");
const loginId         = document.getElementById("loginId");
const loginPw         = document.getElementById("loginPassword");
const btnLogin        = document.getElementById("btnLogin");
const regDn           = document.getElementById("regDisplayName");
const regEm           = document.getElementById("regEmail");
const regPw           = document.getElementById("regPassword");
const btnRegister     = document.getElementById("btnRegister");
const btnLogout       = document.getElementById("btnLogout");
const userNameEl      = document.getElementById("userName");
const chatWindow      = document.getElementById("chatWindow");
const messageIn       = document.getElementById("messageInput");
const sendBtn         = document.getElementById("sendBtn");
const ovePeek         = document.getElementById("ovePeek");
const statusBarEl     = document.getElementById("statusBar");

let chatUnsub, presenceUnsub, presenceRef;
let isOveActive = false;

// För att hålla konversationen
let chatHistory = [];
let chatSummary = "";

/**
 * Sammanfattar meddelanden för att hålla prompten kort.
 */
async function summarizeMessages(messages, previousSummary = "") {
  let prompt = "Sammanfatta följande konversation på max 60 ord:\n";
  if (previousSummary) {
    prompt += "Tidigare sammanfattning:\n" + previousSummary + "\n---\n";
  }
  messages.forEach(m => {
    const who = m.role === "assistant" ? "Ove" : "Användare";
    prompt += `${who}: ${m.content}\n`;
  });
  const res = await fetch("/api/anthropic", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: prompt })
  });
  const data = await res.json();
  return data.reply.trim();
}

/**
 * Lägger in ett meddelande i chat-fönstret.
 */
function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = "message " + role;
  div.textContent = text;
  chatWindow.append(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ======== TAB-switch ========
tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    tabContents.forEach(c => c.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.tab).classList.add("active");
  });
});

// ======== Form-submit kopplar till knappar ========
loginForm.addEventListener("submit", e => {
  e.preventDefault();
  btnLogin.click();
});
registerForm.addEventListener("submit", e => {
  e.preventDefault();
  btnRegister.click();
});

// ======== Auth: Registrera ========
btnRegister.addEventListener("click", async () => {
  try {
    const cred = await createUserWithEmailAndPassword(auth, regEm.value, regPw.value);
    await updateProfile(cred.user, { displayName: regDn.value });
    await setDoc(doc(db, "users", cred.user.uid), {
      displayName: regDn.value,
      email: cred.user.email
    });
  } catch (e) {
    alert("Registreringsfel: " + e.message);
  }
});

// ======== Auth: Logga in ========
btnLogin.addEventListener("click", async () => {
  try {
    let email = loginId.value.trim();
    // Om användaren anger visningsnamn istället för e-post
    if (email && !/@/.test(email)) {
      const q    = query(collection(db, "users"), where("displayName", "==", email));
      const snap = await getDocs(q);
      if (!snap.docs.length) throw new Error("Ingen användare med det visningsnamnet");
      email = snap.docs[0].data().email;
    }
    await signInWithEmailAndPassword(auth, email, loginPw.value);
  } catch (e) {
    alert("Login-fel: " + e.message);
  }
});

// ======== Auth: Logga ut ========
btnLogout.addEventListener("click", () => signOut(auth));

// ======== När auth-state ändras ========
onAuthStateChanged(auth, user => {
  if (user) {
    // Sätt upp närvaro för Ove
    presenceRef = doc(db, "presence", "ove");
    if (presenceUnsub) presenceUnsub();
    presenceUnsub = onSnapshot(presenceRef, snap => {
      const d = snap.exists() ? snap.data() : {};
      isOveActive = !!d.active;
      // Väck Ove (peek-cirkel)
      ovePeek.classList.toggle("hidden", !d.active);
      // Visa/dölj skrivindikatorn
      statusBarEl.classList.toggle("hidden", !d.typing);
    });

    // Visa chat
    authUI.classList.add("hidden");
    chatUI.classList.remove("hidden");
    userNameEl.textContent = user.displayName || user.email;
    messageIn.focus();

    // Lyssna på alla meddelanden
    if (chatUnsub) chatUnsub();
    chatUnsub = onSnapshot(
      query(collection(db, "messages"), orderBy("timestamp")),
      snap => {
        chatWindow.innerHTML = "";
        snap.forEach(d => appendMessage(d.data().role, d.data().content));
      }
    );

  } else {
    // Rensa lyssnare och visa auth-UI
    if (chatUnsub)     chatUnsub();
    if (presenceUnsub) presenceUnsub();
    chatUI.classList.add("hidden");
    authUI.classList.remove("hidden");
  }
});

// ======== Skicka meddelande ========
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

  // Väck Ove om han nämns
  if (presenceRef && text.toLowerCase().includes("ove")) {
    await setDoc(presenceRef, {
      active:    true,
      typing:    false,
      timestamp: serverTimestamp()
    });
  }

  // Töm inputfältet
  messageIn.value = "";
  messageIn.focus();

  const user = auth.currentUser;
  if (!user) return alert("Du måste vara inloggad!");

  // Lägg till i lokal historik
  chatHistory.push({ role: "user", content: text });

  // Om historiken blir för lång, summera de äldsta
  if (chatHistory.length > 8) {
    const toSummarize = chatHistory.slice(0, chatHistory.length - 4);
    chatSummary = await summarizeMessages(toSummarize, chatSummary);
    chatHistory = chatHistory.slice(chatHistory.length - 4);
  }

  // Bygg prompt med sammanfattning + färsk kontext
  let prompt = "";
  if (chatSummary) {
    prompt += "Tidigare sammanfattning:\n" + chatSummary + "\n---\n";
  }
  prompt += "Senaste meddelanden:\n";
  chatHistory.forEach(m => {
    const who = m.role === "assistant" ? "Ove" : "Användare";
    prompt += `${who}: ${m.content}\n`;
  });
  prompt += "Ovan är kontexten. Svara nu på: " + text;

  // Spara användarens meddelande i Firestore
  await addDoc(collection(db, "messages"), {
    role:      "user",
    content:   text,
    timestamp: serverTimestamp()
  });

  // Om Ove är online: visa skrivindikator, anropa API, spara svar
  if (isOveActive && presenceRef) {
    await updateDoc(presenceRef, { typing: true, timestamp: serverTimestamp() });

    const res  = await fetch("/api/anthropic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: prompt })
    });
    const data = await res.json();
    const reply = data.reply.trim();

    await addDoc(collection(db, "messages"), {
      role:      "assistant",
      content:   reply,
      timestamp: serverTimestamp()
    });

    // Lägg till Oves svar i lokal historik
    chatHistory.push({ role: "assistant", content: reply });

    // Dölj skrivindikator
    await updateDoc(presenceRef, { typing: false, timestamp: serverTimestamp() });

    // Om Ove avslutar konversationen, sätt offline
    if (reply.toLowerCase().includes("hejdå") || reply.toLowerCase().includes("tröttnat")) {
      await setDoc(presenceRef, {
        active:    false,
        typing:    false,
        timestamp: serverTimestamp()
      });
    }
  }
}
