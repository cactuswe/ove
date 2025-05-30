import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.1/firebase-app.js";
import {
  getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword,
  onAuthStateChanged, updateProfile, signOut
} from "https://www.gstatic.com/firebasejs/9.22.1/firebase-auth.js";
import {
  getFirestore, doc, getDoc, setDoc, updateDoc, collection,
  addDoc, getDocs, query, orderBy, where, onSnapshot, serverTimestamp, limit
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
const db   = getFirestore(app);

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

// System-prompt
let chatHistory = [
  { role: "system", content: "Du är Ove, en hjälpsam assistent på svenska." }
];

// Summarize long context
async function summarizeMessages(messages, previousSummary="") {
  let prompt = "Sammanfatta ENDAST viktiga fakta och samtalsämnen (max 30 ord, inga detaljer om känslor eller beteende):\n";
  if (previousSummary) {
    prompt += "Tidigare kontext: " + previousSummary + "\n---\nNya fakta:\n";
  }
  messages.forEach(m => {
    const who = m.role==="assistant" ? "Ove" : "Användare";
    prompt += `${who}: ${m.content}\n`;
  });
  const res = await fetch("/api/anthropic", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ message: prompt })
  });
  const data = await res.json();
  return data.reply.trim();
}

// Add message grouping by time
function shouldGroupMessage(prevMessage, newMessage) {
  if (!prevMessage || prevMessage.role !== newMessage.role) return false;
  const prevTime = new Date(prevMessage.timestamp?.seconds * 1000);
  const newTime = new Date(newMessage.timestamp?.seconds * 1000);
  return (newTime - prevTime) < 120000; // 2 minutes
}

// Update message rendering
function appendMessage(role, text, alias, timestamp) {
  const isNearBottom = chatWindow.scrollHeight - chatWindow.scrollTop - chatWindow.clientHeight < 150;
  const div = document.createElement("div");
  const currentUser = auth.currentUser;
  
  // Determine message type
  if (role === 'user') {
    if (alias === (currentUser?.displayName || currentUser?.email)) {
      div.className = 'message user';
    } else {
      div.className = 'message other-user';
    }
  } else {
    div.className = `message ${role}`;
  }
  
  const meta = document.createElement("div");
  meta.className = "message-meta";
  
  const timeStr = timestamp
    ? new Date(timestamp.seconds * 1000)
        .toLocaleTimeString("sv-SE", {hour:"2-digit", minute:"2-digit"})
    : new Date().toLocaleTimeString("sv-SE", {hour:"2-digit", minute:"2-digit"});
  
  meta.innerHTML = `
    ${alias || 'Unknown'}
    <span class="message-time">${timeStr}</span>
  `;
  
  const content = document.createElement("div");
  content.className = "message-content";
  content.textContent = text;
  
  div.append(meta, content);
  
  // Add message without scrolling
  requestAnimationFrame(() => {
    chatWindow.appendChild(div);
    // Only scroll if we're near bottom
    if (isNearBottom) {
      div.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  });
}

// Add scroll to bottom button when needed
const scrollBtn = document.createElement('button');
scrollBtn.className = 'scroll-btn hidden';
scrollBtn.innerHTML = '↓';
chatWindow.appendChild(scrollBtn);

chatWindow.addEventListener('scroll', () => {
  const shouldShow = chatWindow.scrollTop + chatWindow.clientHeight < chatWindow.scrollHeight - 100;
  scrollBtn.classList.toggle('hidden', !shouldShow);
});

scrollBtn.addEventListener('click', () => scrollToBottom());

// Add smooth scroll function after message
function scrollToBottom(smooth = true) {
  requestAnimationFrame(() => {
    const chatWindow = document.getElementById('chatWindow');
    const lastMessage = chatWindow.lastElementChild;
    if (lastMessage) {
      lastMessage.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'end' });
    }
  });
}

// Add typing bubble function
function addTypingBubble() {
  const div = document.createElement("div");
  div.className = "message assistant";
  
  const bubble = document.createElement("div");
  bubble.className = "typing-indicator";
  
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement("span");
    bubble.appendChild(dot);
  }
  
  div.appendChild(bubble);
  chatWindow.appendChild(div);
  scrollToBottom();
  return div;
}

// Tab-switch
tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t=>t.classList.remove("active"));
    tabContents.forEach(c=>c.classList.remove("active"));
    tab.classList.add("active");
    $(tab.dataset.tab).classList.add("active");
  });
});
loginForm.addEventListener("submit", e=>{e.preventDefault(); btnLogin.click();});
registerForm.addEventListener("submit", e=>{e.preventDefault(); btnRegister.click();});

// Registrera
btnRegister.addEventListener("click", async()=>{
  try {
    const cred = await createUserWithEmailAndPassword(auth, regEm.value, regPw.value);
    await updateProfile(cred.user, { displayName: regDn.value });
    await setDoc(doc(db,"users", cred.user.uid), {
      displayName: regDn.value,
      email: cred.user.email
    });
  } catch(e) {
    alert("Registreringsfel: " + e.message);
  }
});
// Logga in
btnLogin.addEventListener("click", async()=>{
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
  } catch(e) {
    alert("Login-fel: " + e.message);
  }
});
btnLogout.addEventListener("click", ()=>signOut(auth));

// Auth-state + närvaro + meddelanden
onAuthStateChanged(auth, user => {
  if (user) {
    presenceRef = doc(db,"presence","ove");
    presenceUnsub?.();
    presenceUnsub = onSnapshot(presenceRef, snap => {
      const d = snap.exists() ? snap.data() : {};
      ovePeek?.classList.toggle("active", !!d.active);
      if (typingIndicator) {
        typingIndicator.classList.toggle("hidden", !d.typing);
      }
    });

    authUI.classList.add("hidden");
    chatUI.classList.remove("hidden");
    userNameEl.textContent = user.displayName || user.email;
    messageIn.focus();

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
    chatUnsub?.();
    presenceUnsub?.();
    chatUI.classList.add("hidden");
    authUI.classList.remove("hidden");
  }
});

// Skicka-meddelande
sendBtn.addEventListener("click", sendMessage);
messageIn.addEventListener("keydown", e=>{
  if (e.key==="Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Add input handling improvements
messageIn.addEventListener('input', (e) => {
  autoResize(e.target);
  e.target.style.borderColor = e.target.value.trim() ? 'var(--primary-color)' : 'var(--border-color)';
});

// Add send button disable state
function updateSendButton() {
  const text = messageIn.value.trim();
  sendBtn.disabled = !text;
  sendBtn.style.opacity = text ? '1' : '0.5';
}

messageIn.addEventListener('input', updateSendButton);
updateSendButton();

// Enhanced input handling
messageIn.addEventListener('input', (e) => {
  const el = e.target;
  autoResize(el);
  
  // Update send button state
  const text = el.value.trim();
  sendBtn.disabled = !text;
  sendBtn.style.opacity = text ? '1' : '0.5';
  
  // Dynamic border color
  el.style.borderColor = text ? '#94a3b8' : '#e2e8f0';
});

// Improve autoResize function
function autoResize(el) {
  el.style.height = 'auto';
  const newHeight = Math.min(el.scrollHeight, 120);
  el.style.height = newHeight + 'px';
  
  // Adjust footer padding based on input height
  const footer = el.closest('footer');
  footer.style.paddingBottom = newHeight > 50 ? '0.5rem' : '0.75rem';
}

// Add paste handling for better UX
messageIn.addEventListener('paste', (e) => {
  e.preventDefault();
  const text = e.clipboardData.getData('text/plain');
  document.execCommand('insertText', false, text);
});

// Add composition handling for IME input
messageIn.addEventListener('compositionend', (e) => {
  autoResize(e.target);
  updateSendButton();
});

// Add keyboard handling
let keyboardHeight = 0;
let isKeyboardVisible = false;

// Add after DOM refs
const footerEl = document.querySelector('footer');
const chatUIEl = document.getElementById('chatUI');

// Add iOS keyboard handlers
if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
  window.visualViewport.addEventListener('resize', handleViewportResize);
  window.visualViewport.addEventListener('scroll', handleViewportResize);
}

function handleViewportResize() {
  const viewport = window.visualViewport;
  if (!viewport) return;

  // Check if keyboard is visible
  isKeyboardVisible = window.screen.height - viewport.height > 100;
  keyboardHeight = window.screen.height - viewport.height;

  // Adjust UI
  chatUIEl.style.height = `${viewport.height}px`;
  if (isKeyboardVisible) {
    footerEl.style.position = 'absolute';
    footerEl.style.bottom = `${keyboardHeight}px`;
    scrollToBottom();
  } else {
    footerEl.style.position = '';
    footerEl.style.bottom = '';
  }
}

messageIn.addEventListener('focus', () => {
  if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
    setTimeout(scrollToBottom, 100);
  }
});

async function sendMessage() {
  const text = messageIn.value.trim();
  if (!text) return;
  const user = auth.currentUser;
  if (!user) return alert("Du måste vara inloggad!");
  
  try {
    const oveDoc = await getDoc(presenceRef);
    const oveState = oveDoc.data() || {};
    const mentioned = /(^|\s)ove\b/i.test(text);
    const isActiveUser = oveState.activeUser === user.uid;
    
    // Activate Ove if mentioned or already active with this user
    const isOveActive = mentioned || (oveState.active && isActiveUser);

    messageIn.value = "";
    autoResize(messageIn);
    updateSendButton();

    // Save user message
    await addDoc(collection(db,"messages"), {
      role: "user",
      alias: user.displayName || user.email,
      content: text,
      timestamp: serverTimestamp(),
      userId: user.uid // Add userId to track message owner
    });

    // Update Ove's active state when mentioned
    if (mentioned) {
      await updateOvePresence(true, true, user.uid);
    } else if (!oveState.active) {
      // If not mentioned and not active, do nothing
      return;
    }

    // Respond if Ove was mentioned or is active with this user
    if (isOveActive) {
      const typingBubble = addTypingBubble();
      
      // Fetch fewer messages for more focused context
      const recentMsgs = await getDocs(
        query(collection(db, "messages"), 
        orderBy("timestamp", "desc"), 
        limit(5))  // Reduced from 8 to 5
      );
      
      const messages = [];
      recentMsgs.forEach(doc => {
        const msg = doc.data();
        messages.unshift({
          role: msg.role,
          content: msg.content
        });
      });

      // Only update summary if there's significant new content
      if (messages.length > 3 && !chatSummary) {
        chatSummary = await summarizeMessages(messages);
      } else if (messages.length > 5) {
        // Update summary less frequently
        chatSummary = await summarizeMessages(messages.slice(-3), chatSummary);
      }

      try {
        const res = await fetch("/api/anthropic", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({ 
            message: text,
            history: messages,
            summary: chatSummary
          })
        });
        
        typingBubble.remove();
        const data = await res.json();
        const reply = data.reply.trim();

        await addDoc(collection(db,"messages"), {
          role: "assistant",
          alias: "Ove",
          content: reply,
          timestamp: serverTimestamp()
        });

        // Update state based on response
        if (/hejdå|tröttnat/i.test(reply)) {
          await updateOvePresence(false, false, null);
        } else {
          await updateDoc(presenceRef, { typing: false });
        }
      } catch (err) {
        typingBubble.remove();
        console.error("Error:", err);
        appendMessage("assistant", "Oj, något gick fel!", "System");
      }
    }
  } catch (err) {
    console.error("Failed to handle message:", err);
    alert("Något gick fel när meddelandet skulle skickas");
  }
}

// Update presence tracking to include active user
async function updateOvePresence(isActive, typing, activeUser = null) {
  await setDoc(presenceRef, {
    active: isActive,
    typing: typing,
    activeUser: activeUser, // Track who Ove is talking to
    timestamp: serverTimestamp()
  });
}
