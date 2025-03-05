const textarea = document.getElementById("chat-input-text")
const startNewChatBtn = document.getElementById("start-new-chat-btn");
const chatHistoryRangeContainer = document.getElementById("chat-history-range-container");

document.addEventListener("DOMContentLoaded", (event) => {
  //localStorage.clear();
  loadMessages();
  loadAllThreadsInfo();
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
startNewChatBtn.addEventListener("click", function () {
  // Clear the chat box and local storage
  document.getElementById("chat-box").innerHTML = "";
  localStorage.clear();
}
);
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
// function to get all chat histories from the server
function loadAllThreadsInfo() {
  fetch("./static/sampleChatHistoryDb.json")
    .then((response) => response.json())
    .then((data) => {
      // add the chat history to the side panel
      const today = new Date();
      const historyRange = document.querySelector(".thread-container");
      historyRange.innerHTML = "";
      data.forEach((thread) => {
        const threadCreatedAt = new Date(thread.created_at);
        const timeDiff = today.getTime() - threadCreatedAt.getTime();
        const diffDays = Math.ceil(timeDiff / (1000 * 3600 * 24));
        const chatTitleElement = document.createElement("p");
        chatTitleElement.classList.add("chat-title");
        chatTitleElement.textContent = thread.title;
        const deleteThreadBtn = document.createElement("span");
        chatTitleElement.addEventListener("click", ()=>{openChatThread(thread.id)});
        deleteThreadBtn.innerHTML = 
                    `
                      <?xml version="1.0" ?><svg height="24" viewBox="0 0 20 20" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M6 10C6 11.1046 5.10457 12 4 12C2.89543 12 2 11.1046 2 10C2 8.89543 2.89543 8 4 8C5.10457 8 6 8.89543 6 10Z" fill="currentColor"/><path d="M12 10C12 11.1046 11.1046 12 10 12C8.89543 12 8 11.1046 8 10C8 8.89543 8.89543 8 10 8C11.1046 8 12 8.89543 12 10Z" fill="currentColor"/><path d="M16 12C17.1046 12 18 11.1046 18 10C18 8.89543 17.1046 8 16 8C14.8954 8 14 8.89543 14 10C14 11.1046 14.8954 12 16 12Z" fill="currentColor"/></svg></span>
                    `;
        // You can format the date difference as needed
        let timeAgo;
        if (diffDays < 1) {
          timeAgo = "Today";
        } else if (diffDays === 1) {
          timeAgo = "Yesterday";
        } else {
          timeAgo = `${diffDays} days ago`;
        }

        chatTitleElement.innerHTML = thread.title; // Added thread title
        chatTitleElement.onmouseover = () =>{
          deleteThreadBtn.style.display = "block";
        }
        chatTitleElement.onmouseout = () =>{
          deleteThreadBtn.style.display = "none";
        }
        chatTitleElement.appendChild(deleteThreadBtn);
        historyRange.appendChild(chatTitleElement);
      });
    }).catch(error => console.error('Error fetching data:', error));
}
// function to load and display the chat thread
function openChatThread(threadId) {
  console.log(threadId);
  fetch("./static/sampleChatHistoryDb.json")
    .then((response) => response.json())
    .then((data) => {
      const chatBox = document.getElementById("chat-box");
      chatBox.innerHTML = "";
      const thread = data.find((thread) => thread.id === threadId);
      thread.messages.forEach((message) => {
        const userMessage = document.createElement("div");
        userMessage.classList.add("message","user-message");
        userMessage.textContent = message.prompt.text;
        const botMessage = document.createElement("div");
        botMessage.classList.add("message","bot-message");
        botMessage.textContent = message.response;
        chatBox.appendChild(userMessage);
        chatBox.appendChild(botMessage);
      });
      chatBox.scrollTop = chatBox.scrollHeight; // Scroll to the bottom after loading messages
    }).catch(error => console.error('Error fetching data:', error));
}
// TODO: add functionalities for the remove file button on the chat box
