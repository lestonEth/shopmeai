const socket = io("https://distinct-useful-lark.ngrok-free.app", {
    transports: ["websocket", "polling"],
});

// check if connection is successful alert success or error
socket.on("connect", () => {
  alert("Connected to the server");
});

socket.on("connect_error", () => {
  alert("Failed to connect to the server");
}); 


const chatBox = document.getElementById("chat-box");
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message");
const speechBtn = document.getElementById("speechBtn");
const imageInput = document.getElementById("imageInput");
const notes = document.getElementById("notes");

socket.emit("join_chat", { chat_id: chatId });
// Load initial messages

if (messages.length > 0) {
  chatBox.style.display = "flex";
  messages.forEach((data) => {
    if (data.image) {
      addImageToChatBox(data.sender, data.image);
    } else {
      addMessageToChatBox(data.sender, data.text);
    }
  });
}

function dataURLtoBlob(dataURL) {
  const parts = dataURL.split(",");
  const mime = parts[0].match(/:(.*?);/)[1];
  const bstr = atob(parts[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new Blob([u8arr], { type: mime });
}

form.addEventListener("submit", (e) => {
  e.preventDefault();

  const message = messageInput.value.trim();
  const imageToUpload = tempImageData;

  if (message || imageToUpload) {
    if (imageToUpload) {
      const formData = new FormData();
      formData.append("file", dataURLtoBlob(imageToUpload)); // Convert base64 to Blob
      formData.append("chat_id", chatId); // Include chat_id in the form data

      fetch("/upload", {
        method: "POST",
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.file_url) {
            const previewImg = chatBox.querySelector(
              'img[data-is-preview="true"]'
            );
            if (previewImg) {
              previewImg.src = data.file_url; // Replace preview with real image
              previewImg.dataset.isPreview = "false"; // Mark it as real
            }
            socket.emit("send_image", {
              chat_id: chatId,
              sender: role,
              image: data.file_url,
            });
            tempImageData = null; // Clear temp storage after upload
          }
        })
        .catch((error) => {
          console.error("Error uploading image:", error);
          notes.textContent = "Failed to upload the image.";
        });
    }

    if (message) {
      socket.emit("send_message", { chat_id: chatId, sender: role, message });
    }

    messageInput.value = ""; // Clear input
  }
});

socket.on("receive_message", (data) => {
  if (data.image) {
    addImageToChatBox(data.sender, data.image);
  } else {
    addMessageToChatBox(data.sender, data.text);
  }
});

function addMessageToChatBox(sender, message) {
  const messageElement = document.createElement("div");
  messageElement.style.marginBottom = "10px";
  messageElement.style.display = "flex"; // Use flexbox for alignment
  messageElement.style.flexDirection =
    sender === "user" ? "row-reverse" : "row"; // Reverse order for user messages

  const messageContent = document.createElement("div");
  messageContent.style.maxWidth = "70%"; // Max width of 70% of the container
  messageContent.style.wordWrap = "break-word"; // Ensure long words wrap
  messageContent.style.padding = "10px";
  messageContent.style.borderRadius = "10px";
  messageContent.style.backgroundColor =
    sender === "user" ? "var(--input-bg-color)" : "var(--message-bg-color)"; // Different background color based on sender
  messageContent.style.color = "var(--text-color)"; // Text color

  // Check if the message starts with "[payment_url]"
  if (message.startsWith("[payment_url]")) {
    // Extract the payment details
    const urlMatch = message.match(/url:([^\s]+)/);
    const amountMatch = message.match(/amount:([0-9.]+)/);

    const paymentUrl = urlMatch ? urlMatch[1].split("amount:")[0] : "#";
    const amount = amountMatch ? parseFloat(amountMatch[1]).toFixed(2) : "0.00";

    // Create a card container
    const card = document.createElement("div");
    card.style.border = "1px solid #565869";
    card.style.borderRadius = "10px";
    card.style.padding = "15px";
    card.style.margin = "10px 0";
    card.style.backgroundColor = "#2f2f2f";
    card.style.boxShadow = "0 4px 6px rgba(0, 0, 0, 0.1)";
    card.style.textAlign = "center";

    // Amount
    const amountElement = document.createElement("p");
    amountElement.textContent = `Price: $${amount}`;
    amountElement.style.margin = "10px 0";
    amountElement.style.fontSize = "16px";
    amountElement.style.color = "#ffffff";

    // Payment Button
    const button = document.createElement("a");
    button.href = paymentUrl;
    button.target = "_blank";
    button.textContent = "Pay Now";
    button.style.display = "inline-block";
    button.style.padding = "10px 20px";
    button.style.color = "#fff";
    button.style.backgroundColor = "#225a2e";
    button.style.borderRadius = "5px";
    button.style.textDecoration = "none";
    button.style.marginTop = "10px";
    button.style.cursor = "pointer";
    button.style.fontWeight = "bold";

    // Append elements to the card
    card.appendChild(amountElement);
    card.appendChild(button);

    // Append card to the message content
    messageContent.appendChild(card);
  } else {
    // Add the plain text message
    messageContent.textContent = message;
  }

  // Append message to chat box
  messageElement.appendChild(messageContent);
  chatBox.appendChild(messageElement);
  chatBox.scrollTop = chatBox.scrollHeight;

  // Text-to-speech for admin messages to the user
  if (sender === "admin" && role === "user") {
    // Cancel ongoing speech synthesis
    speechSynthesis.cancel();

    if (!message.startsWith("[payment_url]")) {
      // Create a new utterance for the last message
      const utterance = new SpeechSynthesisUtterance(message);
      utterance.lang = "en-US";
      utterance.rate = 1;
      speechSynthesis.speak(utterance);
    }
  }
}

function addImageToChatBox(sender, imageUrl, isPreview = false) {
  const imageElement = document.createElement("div");
  imageElement.style.marginBottom = "10px";

  const imgStyle =
    "max-width: 100%; min-width: 100%; border-radius: 10px; margin-top: 5px;";
  const img = document.createElement("img");
  img.src = imageUrl;
  img.alt = isPreview ? "" : "Image";
  img.style = `${imgStyle} max-height: 300px;`;
  img.dataset.isPreview = isPreview; // Mark as a preview if applicable

  imageElement.appendChild(img);

  if (sender === "user") {
    imageElement.style.alignSelf = "flex-end";
  } else {
    imageElement.style.alignSelf = "flex-start";
  }

  chatBox.appendChild(imageElement);
  chatBox.scrollTop = chatBox.scrollHeight;

  return img; // Return the image element for replacement later
}

// Speech to Text Feature
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;

  speechBtn.addEventListener("click", () => {
    notes.textContent = "We are listening...";
    speechBtn.style.backgroundColor = "#225a2e";
    recognition.start();
  });

  recognition.addEventListener("result", (event) => {
    const transcript = event.results[0][0].transcript;
    if (transcript.trim() === "") {
      notes.textContent =
        "Your microphone seems not to work. Please check and try again.";
    } else {
      notes.textContent = "Listening finished.";
      socket.emit("send_message", {
        chat_id: chatId,
        sender: role,
        message: transcript,
      });
    }
  });

  recognition.addEventListener("end", () => {
    recognition.stop();
    speechBtn.style.backgroundColor = "";
  });
} else {
  speechBtn.disabled = true;
  speechBtn.title = "Speech recognition not supported in this browser.";
}
imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (file) {
    const formData = new FormData();
    formData.append("file", file);

    fetch("/upload", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.file_url) {
          socket.emit("send_image", {
            chat_id: chatId,
            sender: role,
            image: data.file_url,
          });
          addImageToChatBox(role, data.file_url);
        } else {
          notes.textContent = data.error || "File upload failed.";
        }
      })
      .catch((error) => {
        console.error("Error uploading file:", error);
        notes.textContent = "An error occurred while uploading the file.";
      });
  }
});

let tempImageData = null; // Temporarily store image data
messageInput.addEventListener("paste", (event) => {
  const items = event.clipboardData.items;

  // Prevent adding multiple previews
  if (chatBox.querySelector('img[data-is-preview="true"]')) {
    notes.textContent =
      "Image preview already exists. Please send or remove it.";
    event.preventDefault();
    return;
  }

  for (let i = 0; i < items.length; i++) {
    const item = items[i];

    // Check if the item is an image
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      const reader = new FileReader();

      reader.onload = function (event) {
        tempImageData = event.target.result; // Store image as base64 in temp
        addImageToChatBox(role, tempImageData, true); // Add as preview
      };

      reader.readAsDataURL(file);

      // Prevent default paste behavior
      event.preventDefault();
      break; // Stop processing other clipboard items
    }
  }
});

// Save scroll position before page reload
window.addEventListener("beforeunload", () => {
  const chatBox = document.getElementById("chat-box");
  if (chatBox.scrollTop + chatBox.clientHeight >= chatBox.scrollHeight) {
    sessionStorage.setItem("scrollToBottom", "true");
  } else {
    sessionStorage.setItem("scrollToBottom", "false");
  }
});

// Scroll to the bottom on page load if needed
window.addEventListener("load", () => {
  const chatBox = document.getElementById("chat-box");
  const shouldScrollToBottom =
    sessionStorage.getItem("scrollToBottom") === "true";

  if (shouldScrollToBottom) {
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Clear the flag after scrolling
  sessionStorage.removeItem("scrollToBottom");
});
