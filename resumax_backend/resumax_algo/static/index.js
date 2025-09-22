const chatBox = document.getElementById("chat-box");
const sidePanel = document.getElementById("side-panel");
const attachedFiles = document.getElementById("file");
const textarea = document.getElementById("chat-input-text")
const sendPromptBtn = document.getElementById("send-btn")
const uploadFileBtn = document.getElementById("upload-file-btn");
const createThreadBtn = document.getElementById("create-thread-btn");
const promptInputForm = document.getElementById("prompt-input-form");
const openSidePanelBtn = document.getElementById("open-side-panel-btn");
const closeSidePanelBtn = document.getElementById("close-side-panel-btn");
const sidePanelBackdrop = document.getElementById("side-panel-backdrop");
const inputFilesPreviewContainer = document.getElementById("input-files-preview-container");
const chatHistoryRangeContainer = document.getElementById("chat-history-range-container");
const MAX_FILENAME_LENGTH = 10;
const CSRFTOKEN = getCookie('csrftoken') || document.querySelector('meta[name="csrf-token"]').getAttribute('content');

// Simple formatting function (alternative to markdown-it)
// function formatText(text) {
//   return text
//     // Convert **bold** to <strong>
//     .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
//     // Convert *italic* to <em>
//     .replace(/\*(.*?)\*/g, '<em>$1</em>')
//     // Convert line breaks to <br>
//     .replace(/\n/g, '<br>')
//     // Convert bullet points (lines starting with * or -)
//     .replace(/^[\*\-]\s+(.*)$/gm, '<li>$1</li>')
//     // Wrap consecutive <li> elements in <ul>
//     .replace(/(<li>.*<\/li>)(\s*<li>.*<\/li>)*/g, '<ul>$&</ul>')
//     // Convert numbered lists (lines starting with 1. 2. etc.)
//     .replace(/^\d+\.\s+(.*)$/gm, '<li>$1</li>')
//     // Convert ## headers to h3
//     .replace(/^##\s+(.*)$/gm, '<h3>$1</h3>')
//     // Convert # headers to h2
//     .replace(/^#\s+(.*)$/gm, '<h2>$1</h2>');
// }

// initialize the thread id as a session value
if (!sessionStorage.getItem("currentThreadId")){
  sessionStorage.setItem("currentThreadId", 0);
}

document.addEventListener("DOMContentLoaded", (event) => {
  loadThreads(focusFirstThread=false);
});

uploadFileBtn.addEventListener("click", () => {attachedFiles.click()});
attachedFiles.addEventListener("change", handleOnChangeFile);
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
  const currentThreadId = sessionStorage.getItem("currentThreadId");
  // add the user message to the chat box
  addUserMessage(promptData.get("prompt-text"), promptData.getAll("prompt-file").map(file => file.name));
  // send the prompt to the server  
  const requestOptions = {
    method: 'POST',
    headers: {
        'X-CSRFToken': CSRFTOKEN,
    },
    body:promptData,
    };
  fetch("../api/threads/"+currentThreadId+"/", requestOptions)
  .then((response) => {
    if (!response.ok) {
      return response.json().then(err => {
        console.error("Server error:", err);
        throw new Error(`HTTP ${response.status}: ${JSON.stringify(err)}`);
      });
    }
    return response.json();
  })
  .then((response) => {
    /* if the current thread is 0, reload the threads
    to get the newly created thread and set currentThreadId to the new it's id
    */
    if(currentThreadId == 0){
      loadThreads();
    }
    // add the bot response to the chat box
    addBotMessage(response.response);
  })
  .catch((error) => {
    console.error("Error fetching data:", error);
    // Show error message to user
    addBotMessage("Sorry, there was an error processing your request. Please try again.");
  });
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
  
  // Debug: log what we're sending
  console.log("Prompt text:", promptData.get("prompt-text"));
  console.log("Form data entries:", [...promptData.entries()]);
  
  // Validate that we have text
  const promptText = promptData.get("prompt-text");
  if (!promptText || !promptText.trim()) {
    console.error("No prompt text provided");
    addBotMessage("Please enter a message before sending.");
    return;
  }
  
  // reset the form to its initial state
  promptInputForm.reset()
  textarea.style.height = "auto";
  handleOnChangeFile();
  // send the prompt to the server
  sendPrompt(promptData);
}
function handleOnChangeFile() {  
  inputFilesPreviewContainer.innerHTML = "";  
  const files = Array.from(attachedFiles.files)
    if (files.length > 0) {
      inputFilesPreviewContainer.style.display = "flex";
      files.forEach((file, index) => {
        addInputFieldFilePreview(index);
      });
      //add space between the textarea and the file icon
      textarea.classList.toggle("mt-2");
      return;
    }
    inputFilesPreviewContainer.style.display = "none";
    textarea.classList.remove("mt-2");
}
function addInputFieldFilePreview(index) {
  const fileIconContainer = document.createElement("div");
  const fileIcon = document.createElement("i");
  const fileName = document.createElement("span");
  const removeFileBtn = document.createElement("i");
  fileIconContainer.classList.add("file-icon-container");
  
  // Determine file type icon based on file extension
  const file = attachedFiles.files[index];
  const fileExtension = file.name.split('.').pop().toLowerCase();
  const iconClass = getFileTypeIcon(fileExtension);
  
  fileIcon.classList.add("bi", iconClass, "file-type-preview-icon");
  fileName.classList.add("file-name");
  removeFileBtn.classList.add("bi", "bi-x", "remove-file-btn");
  fileName.textContent = formatPreviewFileName(attachedFiles.files[index].name);
  fileIconContainer.appendChild(fileIcon);
  fileIconContainer.appendChild(fileName);
  fileIconContainer.appendChild(removeFileBtn);
  removeFileBtn.onclick = () => {deleteInputFile(index)};
  inputFilesPreviewContainer.appendChild(fileIconContainer);
}

function addConversationFilePreview(name) {
  const fileIconContainer = document.createElement("div");
  const fileIcon = document.createElement("i");
  const fileName = document.createElement("span");
  fileIconContainer.classList.add("file-icon-container");
  
  // Determine file type icon based on file extension
  const fileExtension = name.split('.').pop().toLowerCase();
  const iconClass = getFileTypeIcon(fileExtension);
  
  fileIcon.classList.add("bi", iconClass, "file-type-preview-icon");
  fileName.classList.add("file-name");
  fileName.textContent = formatPreviewFileName(name);
  fileIconContainer.appendChild(fileIcon);
  fileIconContainer.appendChild(fileName);
  return fileIconContainer;
}

function getFileTypeIcon(fileExtension) {
  // Return appropriate Bootstrap icon class based on file extension
  switch (fileExtension) {
    case 'pdf':
      return 'bi-file-earmark-pdf';
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'webp':
    case 'heic':
    case 'heif':
      return 'bi-file-earmark-image';
    case 'txt':
    case 'md':
      return 'bi-file-earmark-text';
    case 'html':
    case 'xml':
      return 'bi-file-earmark-code';
    default:
      return 'bi-file-earmark';
  }
}

function deleteInputFile(index) {
  const files = Array.from(attachedFiles.files);
  const dataTransfer = new DataTransfer();
  files.splice(index, 1);
  files.forEach(file => dataTransfer.items.add(file));
  attachedFiles.files = dataTransfer.files;
  handleOnChangeFile();
}

function handleSideBarToggleEffect() {
  document.getElementById("main-container").classList.toggle("minimized");
  sidePanel.classList.toggle("active");
  sidePanelBackdrop.classList.toggle("active");
  closeSidePanelBtn.classList.toggle("active");
  openSidePanelBtn.classList.toggle("active");
  document.querySelectorAll(".nav-app-name").forEach((element) => {
    element.classList.toggle("active");
  });
}

function handleOnFocusThread(threadId) {
  const currentFocused = chatHistoryRangeContainer.querySelector(".active");
  if(currentFocused) currentFocused.classList.remove("active");
  if(threadId != "0") document.getElementById(`thread-${threadId}`).classList.add("active");
  // hide the side panel if it's active and the device is small
  if (window.innerWidth < 768 && sidePanel.classList.contains("active")) {
    handleSideBarToggleEffect();
  }
}
// loads threads from the server api
// adds the threads to the side panel
// set the first thread as the current thread
function loadThreads(focusFirstThread=true) {

// fetch the threads from the server
fetch("../api/threads")
  .then((response) => response.json())
  .then((data) => {
    // add the chat history to the side panel
    const dateRanges = [
      { days: 1, title: "Today",threads:[]},
      { days: 2, title: "Yesterday",threads:[]},
      { days: 7, title: "This week",threads:[]},
      { days: 30, title: "This month",threads:[]},
      { days: 365, title: "This year",threads:[]},
      { days: 730, title: "Older",threads:[]},
    ]
    // store the threads count in the session storage
    sessionStorage.setItem("threadsCount", data.threads.length);
    // categorize the threads based on when they were created
    const today = new Date();
    const boundaries = dateRanges.map(range => today - range.days * 86400000);
    dateRanges.forEach((dateRange, index) => {
      const upperBound = boundaries[index];
      const lowerBound = boundaries[index - 1] || 0;
      dateRange.threads = data.threads.filter(thread => {
        const threadTime = new Date(thread.created_at).getTime();
        return threadTime >= upperBound && (index === 0 || threadTime < lowerBound);
      });
    });
    // add the threads to the side panel
    chatHistoryRangeContainer.innerHTML = "";
    dateRanges.forEach((dateRange) => {
      if (dateRange.threads.length > 0) {
        const dateRangeElement = document.createElement("div");
        const dateRangeTitle = document.createElement("h3");
        dateRangeElement.classList.add("history-range");
        dateRangeTitle.classList.add("history-range-title");
        dateRangeTitle.textContent = dateRange.title;
        dateRangeElement.appendChild(dateRangeTitle);
        chatHistoryRangeContainer.appendChild(dateRangeElement);
        dateRange.threads.forEach((thread) => {
          const chatTitleElement = document.createElement("p");
          const deleteThreadBtn = document.createElement("span");
          const icon = document.createElement('i');
          chatTitleElement.classList.add("thread-title");
          chatTitleElement.setAttribute("id", `thread-${thread.id}`);
          chatTitleElement.textContent = thread.title;
          chatTitleElement.addEventListener("click", ()=>{loadConversations(thread.id)});
          deleteThreadBtn.addEventListener("click", ()=>{deleteThread(thread.id)});
          icon.classList.add("bi","bi-trash3-fill");
          deleteThreadBtn.appendChild(icon);
          chatTitleElement.innerHTML = thread.title; // Added thread title
          chatTitleElement.onmouseover = () =>{
            deleteThreadBtn.style.display = "flex";
          }
          chatTitleElement.onmouseout = () =>{
            deleteThreadBtn.style.display = "none";
          }
          chatTitleElement.appendChild(deleteThreadBtn);
          dateRangeElement.appendChild(chatTitleElement);
          if (focusFirstThread) {
            // set the first thread as the current thread
            sessionStorage.setItem("currentThreadId",thread.id);
            handleOnFocusThread(thread.id);
            focusFirstThread = false;
          }
      });
      }
    });
  })
  .then(() =>loadConversations())
  .catch(error => console.error('Error fetching data:', error));
}
// loads the conversation in the thread with certain ID from the server api
// if no threadId is provided, it loads the currentThreadId(recently created thread)
function loadConversations(threadId) {
  //change the global variable currentThread to the threadId
  if(threadId){
    sessionStorage.setItem("currentThreadId", threadId)}
    else{
      threadId = sessionStorage.getItem("currentThreadId");
    }
  handleOnFocusThread(threadId)
  // if the threadId is 0, don't load the conversations
  if (threadId == 0){
    chatBox.innerHTML = "";
    promptInputForm.classList.add("new-chat");
    return;
  }
  //fetch the conversations from the server
  fetch("../api/threads/"+threadId+"/")
    .then((response) => {
      if (!response.ok) {
        throw new Error("couldn't  thread " + response.statusText);
      }
      return response.json();
    })
    .then((response) => {
      chatBox.innerHTML = "";
      response.conversations.forEach((message) => {
        addUserMessage(message.prompt, message.attachedFiles);
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
function addUserMessage(message, attachedFiles=null) {
  const messageElement = document.createElement("div");
  const textBox = document.createElement("div");
  messageElement.classList.add("message", "user-message");
  // remove the new-chat class from the promptInputForm
  promptInputForm.classList.remove("new-chat");
  //if the are attached files, add them to the message
if(attachedFiles != null && attachedFiles.length > 0 && attachedFiles[0] != ''){
    const filesPreviewContainer = document.createElement("div");
    filesPreviewContainer.classList.add("files-preview-container");
    attachedFiles.forEach((fileName) => {
      fileName = formatPreviewFileName(fileName);
      filesPreviewContainer.appendChild(addConversationFilePreview(fileName));
    });
    messageElement.appendChild(filesPreviewContainer);
  }
  textBox.classList.add("text-box");
  textBox.textContent = message;
  messageElement.appendChild(textBox);
  chatBox.appendChild(messageElement);
  chatBox.scrollTop = chatBox.scrollHeight;
}
// add a bot message in the chat box
function addBotMessage(message) {
  const messageElement = document.createElement("div");
  messageElement.classList.add("message", "bot-message");
  // Use simple formatting instead of markdown-it
  // messageElement.innerHTML = formatText(message);
  
  // Or use the markdown-it version (current implementation)
  const md = window.markdownit({
    html: false,        // Disable HTML tags in source for security
    xhtmlOut: false,    // Use '>' for single tags (<br>)
    breaks: true,       // Convert '\n' in paragraphs into <br>
    linkify: true,      // Autoconvert URL-like text to links
    typographer: true   // Enable some language-neutral replacement + quotes beautification
  });
  
  // Convert markdown to HTML and set as innerHTML
  messageElement.innerHTML = md.render(message);
  chatBox.appendChild(messageElement);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// create a new thread
function createThread() {
  // set the current thread to 0
  sessionStorage.setItem("currentThreadId", 0);
  chatBox.innerHTML = "";
  promptInputForm.classList.add("new-chat");
  handleOnFocusThread(0);
}

// delete a thread
function deleteThread(threadId) {
  // delete the thread from the server and reload the threads
  const requestOptions = {
    method: 'DELETE',
    headers: {
        'X-CSRFToken': CSRFTOKEN,
    },
    };
  fetch("../api/threads/"+threadId+"/delete/", requestOptions)
  .then((response) => {
    if (!response.ok) {
      throw new Error('Failed to delete thread: ' + response.statusText);
    }
    if (threadId == sessionStorage.getItem("currentThreadId")) {
      if(sessionStorage.getItem("threadsCount") <= 1){
        sessionStorage.setItem("currentThreadId", 0);
        chatBox.innerHTML = "";
        promptInputForm.classList.add("new-chat")
      }
      loadThreads()
     }
  })
  .catch((error) => console.error("Error fetching data:", error));
}

function formatPreviewFileName(fileName) {
  if (fileName.length <= MAX_FILENAME_LENGTH) return fileName;
  const [name, ext] = fileName.split(".");
  return `${name.substring(0, MAX_FILENAME_LENGTH)}...${ext ? '.' + ext : ''}`;
}
// TODO: look for pretty UI/UX