const textarea = document.getElementById("chat-input-text")
document.addEventListener("DOMContentLoaded", (event) => {
  //localStorage.clear();
  loadMessages();
});

document.getElementById("file-upload-btn").addEventListener("click", () => {
  document.getElementById("file").click();
});

document.getElementById("file").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) {
    document.getElementById("file-icon-container").style.display = "flex";
    document.getElementById("file-name").textContent = file.name;
    //add space between the textarea and the file icon
    textarea.classList.toggle("mt-2");
  } else {
    document.getElementById("file-icon-container").style.display = "none";
    document.getElementById("file-name").textContent = "";
  }
});

document.getElementById("send-btn").addEventListener("click", function (event) {
  sendMessage();
  uploadFile();
});
textarea.addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
      document.getElementById("send-btn").click();
    }
  });

//   responsiveness for the UI
document.getElementById("open-side-panel-btn").addEventListener("click", sideBarDisplay);
document.getElementById("close-side-panel-btn").addEventListener("click", sideBarDisplay);
document.getElementById("side-panel-backdrop").addEventListener("click", sideBarDisplay);
textarea.addEventListener("input", function () {
  this.style.height = "auto";
  this.style.height = this.scrollHeight + "px";
});

function sendMessage() {
  const chatBox = document.getElementById("chat-box");
  const chatInput = document.getElementById("chat-input-text");
  const message = chatInput.value.trim();

  if (message) {
    const messageElement = document.createElement("div");
    messageElement.classList.add("message", "user-message");
    messageElement.textContent = message;
    chatBox.appendChild(messageElement);
    chatInput.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;
    saveMessage({ type: "text", content: message });
  }
}

function uploadFile() {
  const chatBox = document.getElementById("chat-box");
  //const file = event.target.files[0];
  const fileName = document.getElementById("file-name").textContent;

  if (fileName != "") {
    const fileElement = document.createElement("div");
    fileElement.classList.add("message", "file-message");
    fileElement.textContent = `File uploaded: ${fileName}`;
    chatBox.appendChild(fileElement);
    chatBox.scrollTop = chatBox.scrollHeight;
    saveMessage({ type: "file", content: fileElement.textContent });
    document.getElementById("file-icon-container").style.display = "none";
    document.getElementById("file-name").textContent = "";
  }
}

function saveMessage(message) {
  let messages = JSON.parse(localStorage.getItem("messages")) || [];
  messages.push(message);
  localStorage.setItem("messages", JSON.stringify(messages));
}

function loadMessages() {
  const messages = JSON.parse(localStorage.getItem("messages")) || [];
  const chatBox = document.getElementById("chat-box");
  messages.forEach((message) => {
    const messageElement = document.createElement("div");
    messageElement.classList.add(
      "message",
      message.type === "text" ? "user-message" : "file-message"
    );
    messageElement.textContent = message.content;
    chatBox.appendChild(messageElement);
  });
  chatBox.scrollTop = chatBox.scrollHeight; // Scroll to the bottom after loading messages
}
function sideBarDisplay() {
  document.getElementById("side-panel").classList.toggle("active");
  document.getElementById("side-panel-backdrop").classList.toggle("active");
  document.getElementById("chat-container").classList.toggle("minimized");
  document.getElementById("close-side-panel-btn").classList.toggle("active");
  document.getElementById("open-side-panel-btn").classList.toggle("active");
  document.querySelectorAll(".nav-app-name").forEach((element) => {
    element.classList.toggle("active");
  });
}
// TODO: add functionalities for the remove file button on the chat box
