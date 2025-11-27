# Snowflake Ascent: An Interactive Snowflake Learning Platform

**Snowflake Ascent** este o aplicație web interactivă, expert-level, concepută pentru a servi drept **knowledge base complet** pentru oricine dorește să stăpânească **Snowflake Data Cloud**.  
Platforma funcționează ca un **glosar dinamic**, un **AI tutor personal** și un **code reference practic**, toate într-un singur loc.  

---

## 🚀 Key Features

- **Curated Knowledge Base**  
  Termeni organizați în categorii logice:  
  - Core Architecture  
  - Data Governance  
  - Snowpark  
  - Snowflake Cortex  
  - Cost Management  

- **Multi-Layered Explanations**  
  Fiecare termen include:  
  - **Explain Like I’m Five (ELI5)** → explicație intuitivă  
  - **Definiție formală** → acuratețe tehnică  
  - **Breakdowns, exemple & pitfalls** → detaliu aprofundat  

- **AI-Powered Insights (Gemini Integration)**  
  - *Generate Analogies*: analogii noi, pe loc  
  - *Deconstruct Concepts*: structurare logică a termenilor  
  - *Interactive AI Tutor*: chat contextual pentru explorare mai profundă  
  - *AI Code Explainer*: explicație linie cu linie pentru SQL/Python în Snowflake  

- **Visual Diagrams**  
  Diagramme personalizate (ex: Virtual Warehouses, Time Travel, Cortex Search).  

- **Dynamic Quizzes**  
  Testează-ți cunoștințele cu quiz-uri interactive cu feedback instant.  
  Poți genera și întrebări noi cu AI-ul.  

---

## 🛠 Tech Stack

- **Frontend**: React (Hooks + functional components)  
- **Styling**: Tailwind CSS  
- **Animations**: Framer Motion  
- **Icons**: Lucide React  
- **AI Integration**: Google Gemini API  

---

## ⚡ Getting Started

### 🔑 Step 1: Get Your Free Gemini API Key
1. Mergi la **[Google AI Studio](https://aistudio.google.com/)**  
2. Loghează-te cu Google  
3. Click pe **Create API key**  
4. Copiază cheia generată  

> ⚠️ **Important**  
> - **Nu** împărtăși cheia ta cu nimeni  
> - **Nu** o pune în public pe GitHub  
> - Fiecare user trebuie să-și genereze propria cheie  

---

### 📦 Step 2: Download and Unzip the Project
Dacă ai primit proiectul ca arhivă `.zip`, dezarhivează-l într-un folder local.  

---

### 💻 Step 3: Install Prerequisites
Ai nevoie de **Node.js**.  
Dacă nu îl ai, descarcă-l de pe [nodejs.org](https://nodejs.org) (LTS version recomandat).  

---

### 🔐 Step 4: Add Your API Key
1. În folderul proiectului, creează/editează fișierul **`.env`**  
2. Adaugă linia:  
   ```bash
   VITE_GEMINI_API_KEY="YOUR_API_KEY_HERE"
   ```  
3. Salvează și închide fișierul.  

---

### ▶️ Step 5: Install Dependencies & Run the App
În terminal, rulează:  
```bash
npm install
npm run dev
```  

Accesează aplicația la:  
👉 [http://localhost:5173](http://localhost:5173)  

---

## 🧩 How to Extend the Content
Aplicația este **ușor extensibilă**.  
Pentru a adăuga un nou termen în glosar:  
1. Deschide `src/App.jsx`  
2. Adaugă un nou obiect în array-ul `CURATED_TERMS_SNOWFLAKE`  
3. Respectă structura definită pentru `Term`  

---

## 📜 License
This project is licensed under the **MIT License**.  
Vezi fișierul **LICENSE** pentru detalii.  
