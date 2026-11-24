// Adresse de l'AI Query Service.
const API_URL = "http://localhost:5003/api/ai/query";

const form = document.getElementById("ask-form");
const input = document.getElementById("question");
const button = document.getElementById("send");
const statusBox = document.getElementById("status");
const answerBox = document.getElementById("answer");

async function askQuestion(question) {
  // 1. Attente : message + bouton désactivé
  button.disabled = true;
  statusBox.className = "";
  statusBox.textContent = "Thinking... this can take a few seconds.";
  answerBox.hidden = true;

  try {
    // 2. Envoi de la question
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question }),
    });
    const data = await response.json();

    if (response.ok) {
      // 3. Réponse : textContent et non innerHTML (pas d'injection HTML)
      statusBox.textContent = "";
      answerBox.textContent = data.answer;
      answerBox.hidden = false;
    } else {
      // 4. Le service a répondu par une erreur (400, 503...)
      statusBox.className = "error";
      statusBox.textContent = data.error;
    }
  } catch (error) {
    // 5. Le service ne répond pas du tout (éteint, mauvaise adresse...)
    statusBox.className = "error";
    statusBox.textContent = "The assistant cannot be reached. Please try again later.";
  }

  button.disabled = false;
}

form.addEventListener("submit", function (event) {
  event.preventDefault(); // ne pas recharger la page
  const question = input.value.trim();
  if (question) {
    askQuestion(question);
  }
});

// Un clic sur un exemple remplit le champ et envoie la question.
document.querySelectorAll("#examples button").forEach(function (example) {
  example.addEventListener("click", function () {
    input.value = example.textContent;
    askQuestion(example.textContent);
  });
});