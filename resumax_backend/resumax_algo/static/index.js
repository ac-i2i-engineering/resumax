DEBUGMODE = false;  
const chatBox = document.getElementById("chat-box");
const sidePanel = document.getElementById("side-panel");
const attachedFile = document.getElementById("file");
const textarea = document.getElementById("chat-input-text")
const sendPromptBtn = document.getElementById("send-btn")
const fileUploadBtn = document.getElementById("file-upload-btn");
const createThreadBtn = document.getElementById("create-thread-btn");
const promptInputForm = document.getElementById("prompt-input-form");
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
createThreadBtn.addEventListener("click", createThread);

// resize the textarea to fit the content
function resizeTextarea() {
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";
}

// sends the prompt to the server and gets the bot response
// add the received bot response to the chat box
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
    /* if the current thread is 0, reload the threads
    to get the newly created thread and set currentThreadId to the new it's id
    */
    if(currentThreadId == 0){
      loadThreads();
    }
    // add the bot response to the chat box
    addBotMessage(response.text)
  })
  .catch((error) => console.error("Error fetching data:", error));
}

// handle the textarea formatting on enter key, shift+enter keys, or submitBtn press
// if the textarea is not empty, send the prompt to the server on enter key press or submitBtn press
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
// adds the threads to the side panel
// set the first thread as the current thread
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
        const deleteThreadBtn = document.createElement("span");
        const icon = document.createElement('i');
        chatTitleElement.classList.add("thread-title");
        chatTitleElement.textContent = thread.title;
        chatTitleElement.addEventListener("click", ()=>{loadConversations(thread.id)});
        deleteThreadBtn.addEventListener("click", ()=>{deleteThread(thread.id)});
        icon.classList.add("bi","bi-trash3-fill");
        deleteThreadBtn.appendChild(icon);
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
          deleteThreadBtn.style.display = "flex";
        }
        chatTitleElement.onmouseout = () =>{
          deleteThreadBtn.style.display = "none";
        }
        chatTitleElement.appendChild(deleteThreadBtn);
        historyRange.appendChild(chatTitleElement);
      });
    })
    .then(()=>loadConversations())
    .catch(error => console.error('Error fetching data:', error));
}
// loads the conversation in the thread with certain ID from the server api
// if no threadId is provided, it loads the currentThreadId(recently created thread)
function loadConversations(threadId=currentThreadId) {
  //change the global variable currentThread to the threadId
  currentThreadId = threadId;
  // if the threadId is 0, don't load the conversations
  if (threadId == 0) return
  //fetch the conversations from the server
  fetch("../api/thread/"+threadId)
    .then((response) => {
      if (!response.ok && !DEBUGMODE) return;
      return response.json()
    })
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

// create a new thread
function createThread() {
  // set the current thread to 0
  currentThreadId = 0;
  chatBox.innerHTML = "";
}

// delete a thread
function deleteThread(threadId) {
  /* temporarily set the currentThreadId to 0 to avoid errors if 
  no other threads to load after deleting the current thread
  */
  currentThreadId = 0;
  // delete the thread from the server and reload the threads
  const requestOptions = {
    method: 'DELETE',
    headers: {
        'X-CSRFToken': csrfToken,
    },
    };
  fetch("../api/thread/"+threadId+"/delete", requestOptions)
  .then((response) => {
    if (!response.ok && !DEBUGMODE) return;
    return response.json()
  })
  .then(() => loadThreads())
  .catch((error) => console.error("Error fetching data:", error));
}
// TODO: add functionalities for the remove file button on the chat box
// TODO: make a user message with a file attachment =>"file-message"