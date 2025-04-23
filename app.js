/* ---------- Firebase-SDK ---------- */
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.1/firebase-app.js";
import {
  getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword,
  onAuthStateChanged, updateProfile, signOut
} from "https://www.gstatic.com/firebasejs/9.22.1/firebase-auth.js";
import {
  getFirestore, doc, setDoc, getDocs, updateDoc, collection,
  addDoc, query, orderBy, where, onSnapshot, serverTimestamp
} from "https://www.gstatic.com/firebasejs/9.22.1/firebase-firestore.js";

/* ---------- Init Firebase ---------- */
const firebaseConfig = {
  apiKey:            "AIzaSyBRMtuyLiyRfWwq1p3e_dSE83Z7sBYJM3I",
  authDomain:        "ove-ai.firebaseapp.com",
  projectId:         "ove-ai",
  storageBucket:     "ove-ai.firebasestorage.app",
  messagingSenderId: "200723689801",
  appId:             "1:200723689801:web:5dbedb16f582048081ea98",
  measurementId:     "G-PEZM6B3N58"
};
const app  = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db   = getFirestore(app);

/* ---------- DOM-refs ---------- */
const $ = (id)=>document.getElementById(id);
const tabs            = document.querySelectorAll(".tab");
const tabContents     = document.querySelectorAll(".tab-content");
const authUI          = $("authUI");
const chatUI          = $("chatUI");
const loginForm       = $("loginForm");
const registerForm    = $("registerForm");
const loginId         = $("loginId");
const loginPw         = $("loginPassword");
const btnLogin        = $("btnLogin");
const regDn           = $("regDisplayName");
const regEm           = $("regEmail");
const regPw           = $("regPassword");
const btnRegister     = $("btnRegister");
const btnLogout       = $("btnLogout");
const userNameEl      = $("userName");
const chatWindow      = $("chatWindow");
const messageIn       = $("messageInput");
const sendBtn         = $("sendBtn");
const ovePeek         = $("ovePeek");
const typingIndicator = $("typingIndicator");

let chatUnsub, presenceUnsub, presenceRef;
let isOveActive = false;

/* ---------- Kontext-state ---------- */
let chatHistory = [];
let chatSummary = "";

/* ---------- Summerings-funktion ---------- */
async function summarizeMessages(messages, previousSummary=""){
  let prompt = "Sammanfatta följande konversation på max 60 ord:\n";
  if(previousSummary) prompt += "Tidigare sammanfattning:\n"+previousSummary+"\n---\n";
  messages.forEach(m=>{
    const who = m.role==="assistant"?"Ove":"Användare";
    prompt += `${who}: ${m.content}\n`;
  });
  const r = await fetch("/api/anthropic",{
    method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({message:prompt})
  });
  const d = await r.json();
  return d.reply.trim();
}

/* ---------- UI-helpers ---------- */
function appendMessage(role,text){
  const div=document.createElement("div");
  div.className="message "+role;
  div.textContent=text;
  chatWindow.append(div);
  chatWindow.scrollTop=chatWindow.scrollHeight;
}
function addTypingBubble(){
  const b=document.createElement("div");
  b.className="message assistant typing";
  for(let i=0;i<3;i++){
    const dot=document.createElement("span");
    dot.className="dot"; b.append(dot);
  }
  chatWindow.append(b);
  chatWindow.scrollTop=chatWindow.scrollHeight;
  return b;
}

/* ---------- Tabs ---------- */
tabs.forEach(tab=>{
  tab.addEventListener("click",()=>{
    tabs.forEach(t=>t.classList.remove("active"));
    tabContents.forEach(c=>c.classList.remove("active"));
    tab.classList.add("active");
    $(tab.dataset.tab).classList.add("active");
  });
});

/* ---------- Stoppa default-submit ---------- */
loginForm.addEventListener("submit",e=>{e.preventDefault();btnLogin.click();});
registerForm.addEventListener("submit",e=>{e.preventDefault();btnRegister.click();});

/* ==================== AUTH ==================== */
btnRegister.addEventListener("click",async()=>{
  try{
    const cred=await createUserWithEmailAndPassword(auth,regEm.value,regPw.value);
    await updateProfile(cred.user,{displayName:regDn.value});
    await setDoc(doc(db,"users",cred.user.uid),{displayName:regDn.value,email:cred.user.email});
  }catch(e){alert("Registreringsfel: "+e.message);}
});

btnLogin.addEventListener("click",async()=>{
  try{
    let email=loginId.value.trim();
    if(email && !/@/.test(email)){
      const snap=await getDocs(query(collection(db,"users"),where("displayName","==",email)));
      if(snap.empty) throw new Error("Ingen användare med det visningsnamnet");
      email=snap.docs[0].data().email;
    }
    await signInWithEmailAndPassword(auth,email,loginPw.value);
  }catch(e){alert("Login-fel: "+e.message);}
});

btnLogout.addEventListener("click",()=>signOut(auth));

/* ================= CHAT & PRESENCE ============ */
onAuthStateChanged(auth,user=>{
  if(user){
    /* Närvaro */
    presenceRef=doc(db,"presence","ove");
    presenceUnsub?.();
    presenceUnsub=onSnapshot(presenceRef,snap=>{
      const d=snap.exists()?snap.data():{};
      isOveActive=!!d.active;
      ovePeek.classList.toggle("active",d.active);
      typingIndicator.classList.toggle("hidden",!d.typing);
    });

    /* UI */
    authUI.classList.add("hidden");
    chatUI.classList.remove("hidden");
    userNameEl.textContent=user.displayName||user.email;
    messageIn.focus();

    /* Meddelanden */
    chatUnsub?.();
    chatUnsub=onSnapshot(query(collection(db,"messages"),orderBy("timestamp")),snap=>{
      chatWindow.innerHTML="";
      snap.forEach(d=>appendMessage(d.data().role,d.data().content));
    });

  }else{
    chatUnsub?.();presenceUnsub?.();
    chatUI.classList.add("hidden");
    authUI.classList.remove("hidden");
  }
});

/* ================= SKICKA ===================== */
sendBtn.addEventListener("click",sendMessage);
messageIn.addEventListener("keydown",e=>{
  if(e.key==="Enter" && !e.shiftKey){e.preventDefault();sendMessage();}
});

async function sendMessage(){
  const text=messageIn.value.trim();
  if(!text) return;

  const mentioned=text.toLowerCase().includes("ove");
  if(mentioned && presenceRef){
    await setDoc(presenceRef,{active:true,typing:false,timestamp:serverTimestamp()});
    isOveActive=true;
  }

  messageIn.value="";messageIn.focus();
  const user=auth.currentUser;
  if(!user) return alert("Du måste vara inloggad!");

  /* Historik */
  chatHistory.push({role:"user",content:text});
  if(chatHistory.length>8){
    const toSum=chatHistory.slice(0,chatHistory.length-4);
    chatSummary=await summarizeMessages(toSum,chatSummary);
    chatHistory=chatHistory.slice(chatHistory.length-4);
  }

  /* Prompt */
  let prompt="";
  if(chatSummary) prompt+="Tidigare sammanfattning:\n"+chatSummary+"\n---\n";
  prompt+="Senaste meddelanden:\n";
  chatHistory.forEach(m=>{
    const who=m.role==="assistant"?"Ove":"Användare";
    prompt+=`${who}: ${m.content}\n`;
  });
  prompt+="Ovan är kontexten. Svara nu på: "+text;

  /* Spara user-msg */
  await addDoc(collection(db,"messages"),{role:"user",content:text,timestamp:serverTimestamp()});

  /* Ring Ove om aktiv */
  const askOve=mentioned||isOveActive;
  if(askOve && presenceRef){
    const typingBubble=addTypingBubble();
    await updateDoc(presenceRef,{typing:true,timestamp:serverTimestamp()});

    const r=await fetch("/api/anthropic",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:prompt})});
    const d=await r.json();
    const reply=d.reply.trim();

    typingBubble.remove();
    appendMessage("assistant",reply);
    await addDoc(collection(db,"messages"),{role:"assistant",content:reply,timestamp:serverTimestamp()});

    chatHistory.push({role:"assistant",content:reply});
    await updateDoc(presenceRef,{typing:false,timestamp:serverTimestamp()});

    const bye=reply.toLowerCase();
    if(bye.includes("hejdå")||bye.includes("tröttnat")){
      await setDoc(presenceRef,{active:false,typing:false,timestamp:serverTimestamp()});
    }
  }
}
