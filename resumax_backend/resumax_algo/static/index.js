const chatBox = document.getElementById("chat-box");
const sidePanel = document.getElementById("side-panel");
const attachedFile = document.getElementById("file");
const textarea = document.getElementById("chat-input-text")
const sendPromptBtn = document.getElementById("send-btn")
const fileUploadBtn = document.getElementById("file-upload-btn");
const promptInputForm = document.getElementById("prompt-input-form");
const startNewThreadBtn = document.getElementById("start-new-chat-btn");
const openSidePanelBtn = document.getElementById("open-side-panel-btn");
const closeSidePanelBtn = document.getElementById("close-side-panel-btn");
const sidePanelBackdrop = document.getElementById("side-panel-backdrop");
const chatHistoryRangeContainer = document.getElementById("chat-history-range-container");
const csrfToken = getCookie('csrftoken') || document.querySelector('meta[name="csrf-token"]').getAttribute('content');
// initialize the thread id
let currentThreadId = 0;

document.addEventListener("DOMContentLoaded", (event) => {
  loadThreads();
});

fileUploadBtn.addEventListener("click", () => {attachedFile.click()});
attachedFile.addEventListener("change", handleOnChangeFile);
sendPromptBtn.addEventListener("click", handleOnSubmitPrompt);
textarea.addEventListener("keypress", handleTextareaFormatting);
openSidePanelBtn.addEventListener("click", handleSideBarToggleEffect);
closeSidePanelBtn.addEventListener("click", handleSideBarToggleEffect);
sidePanelBackdrop.addEventListener("click", handleSideBarToggleEffect);
textarea.addEventListener("input", resizeTextarea);
startNewThreadBtn.addEventListener("click", () => {console.log("start new thread")});

function resizeTextarea() {
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";
}
function sendPrompt(promptData) {
  // add the user message to the chat box
  addUserMessage(promptData.get("prompt-text"));
  // send the prompt to the server  
  const requestOptions = {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrfToken,
    },
    body:promptData,
    };
  fetch("../api/thread/"+currentThreadId, requestOptions)
  .then((response) => response.json())
  .then((response) => {
    // add the bot response to the chat box
    addBotMessage(response.text)
  })
  .catch((error) => console.error("Error fetching data:", error));
}

function handleTextareaFormatting(event){
  inputText = textarea.value.trim();
  if (event.key === "Enter" && !event.shiftKey && inputText) {
    event.preventDefault()
    handleOnSubmitPrompt()
  }
}

function handleOnSubmitPrompt(event) {
  if (event) {
    event.preventDefault();
  }
  // get the prompt data from the form
  const promptData = new FormData(promptInputForm);
  // reset the form to its initial state
  promptInputForm.reset()
  textarea.style.height = "auto";
  handleOnChangeFile();
  // send the prompt to the server
  sendPrompt(promptData);
}
function handleOnChangeFile() {    
  const file = attachedFile.files[0];
    if (file) {
      document.getElementById("file-icon-container").style.display = "flex";
      document.getElementById("file-name").textContent = file.name;
      //add space between the textarea and the file icon
      textarea.classList.toggle("mt-2");
    } else {
      document.getElementById("file-icon-container").style.display = "none";
      document.getElementById("file-name").textContent = "";
      textarea.classList.remove("mt-2");
    }
}

function handleSideBarToggleEffect() {
  document.getElementById("chat-container").classList.toggle("minimized");
  sidePanel.classList.toggle("active");
  sidePanelBackdrop.classList.toggle("active");
  closeSidePanelBtn.classList.toggle("active");
  openSidePanelBtn.classList.toggle("active");
  document.querySelectorAll(".nav-app-name").forEach((element) => {
    element.classList.toggle("active");
  });
}
// loads threads from the server api
function loadThreads() {
  isMostRecent = true;
  // fetch the threads from the server
  fetch("../api/threads")
    .then((response) => response.json())
    .then((data) => {
      // add the chat history to the side panel
      const today = new Date();
      const historyRange = document.querySelector(".thread-container");
      historyRange.innerHTML = "";
      data.threads.forEach((thread) => {
        if(isMostRecent){
          // set the first thread as the current thread
          currentThreadId = thread.id;
          isMostRecent = false;
        }
        const threadCreatedAt = new Date(thread.created_at);
        const timeDiff = today.getTime() - threadCreatedAt.getTime();
        const diffDays = Math.ceil(timeDiff / (1000 * 3600 * 24));
        const chatTitleElement = document.createElement("p");
        chatTitleElement.classList.add("chat-title");
        chatTitleElement.textContent = thread.title;
        const deleteThreadBtn = document.createElement("span");
        chatTitleElement.addEventListener("click", ()=>{loadConversations(thread.id)});
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
    })
    .then(()=>{
      // load the conversation of the current thread
      loadConversations(currentThreadId);
    })
    .catch(error => console.error('Error fetching data:', error));
}
// loads the conversation in the thread with certain ID from the server api
function loadConversations(threadId) {
  //change the global variable currentThread to the threadId
  currentThreadId = threadId;
  //fetch the conversations from the server
  fetch("../api/thread/"+threadId)
    .then((response) => response.json())
    .then((response) => {
      chatBox.innerHTML = "";
      response.conversations.forEach((message) => {
        addUserMessage(message.prompt);
        addBotMessage(message.response);
      });
    }).catch(error => console.error('Error fetching data:', error));
}

// gets the cookie with the certain name
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.startsWith(name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              break;
          }
      }
  }
  return cookieValue;
}

// add a user message in the chat box
function addUserMessage(message, attachedFile=null) {
  const messageElement = document.createElement("div");
  messageElement.classList.add("message", "user-message");
  messageElement.textContent = message;
  chatBox.appendChild(messageElement);
  chatBox.scrollTop = chatBox.scrollHeight;
}
// add a bot message in the chat box
function addBotMessage(message) {
  const messageElement = document.createElement("div");
  messageElement.classList.add("message", "bot-message");
  messageElement.textContent = message;
  chatBox.appendChild(messageElement);
  chatBox.scrollTop = chatBox.scrollHeight;
}
// TODO: add functionalities for the remove file button on the chat box
// TODO: make a user message with a file attachment =>"file-message"