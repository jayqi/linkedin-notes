let message;
let port = null;

function appendMessage(text) {
    // document.getElementById('response').innerHTML += '<p>' + text + '</p>';
}

function updateUiState() {
    if (port) {
        // document.getElementById('connect-button').style.display = 'none';
        // document.getElementById('input-text').style.display = 'block';
        // document.getElementById('send-message-button').style.display = 'block';
    } else {
        // document.getElementById('connect-button').style.display = 'block';
        // document.getElementById('input-text').style.display = 'none';
        // document.getElementById('send-message-button').style.display = 'none';
    }
}

function onNativeMessage(message) {
    appendMessage('Received message: <b>' + JSON.stringify(message) + '</b>');
    if (message.mode == 'read') {
        if (message.payload.text !== null) {
            console.log("Successfully retrieved note from database.");
            document.getElementById('notes-field').value = message.payload.text;
        } else {
            console.log("Note is blank.");
            document.getElementById('notes-field').placeholder = 'Enter a note here.';
        }
        document.getElementById('notes-field').removeAttribute('disabled');
        document.getElementById('save-notes-button').setAttribute('disabled', '');
        document.getElementById('reset-notes-button').setAttribute('disabled', '');
    } else if (message.mode == 'write') {
        if (message.payload.success) {
            console.log("Successfully saved note to database.");
            document.getElementById('notes-status').innerText = 'Changes saved.';
            document.getElementById('save-notes-button').setAttribute('disabled', '');
            document.getElementById('reset-notes-button').setAttribute('disabled', '');
        } else {
            console.log("Failed to save note to database.");
            document.getElementById('notes-status').innerText = 'Changes failed to save.';
        }
    } else {
        console.log("Invalid message mode.");
    }
}

function onNotesFieldChange() {
    document.getElementById('notes-status').innerText = 'You have unsaved changes.';
    document.getElementById('save-notes-button').removeAttribute('disabled');
    document.getElementById('reset-notes-button').removeAttribute('disabled');
}

function onDisconnected() {
    appendMessage('Failed to connect: ' + chrome.runtime.lastError.message);
    port = null;
    updateUiState();
}

function connect() {
    const hostName = 'com.jayqi.linkedin_notes';
    appendMessage('Connecting to native messaging host <b>' + hostName + '</b>');
    port = chrome.runtime.connectNative(hostName);
    port.onMessage.addListener(onNativeMessage);
    port.onDisconnect.addListener(onDisconnected);
    updateUiState();
}

async function getActiveTabUrl() {
    const queryOptions = { active: true, currentWindow: true };
    const [tab] = await chrome.tabs.query(queryOptions);
    return new URL(tab.url);
}

function extractProfile(pathname) {
    const regex = /^\/in\/[^\/]+\//;
    const match = pathname.match(regex);
    return match ? match[0] : null;
}

function queryDatabase(profile) {
    message = { profile: profile, mode: 'read' };
    port.postMessage(message);
    appendMessage('Sent message: <b>' + JSON.stringify(message) + '</b>');
}

function saveToDatabase(profile) {
    message = { profile: profile, text: document.getElementById('notes-field').value, mode: 'write' };
    port.postMessage(message);
    appendMessage('Sent message: <b>' + JSON.stringify(message) + '</b>');
}

function discardChanges(profile) {
    queryDatabase(profile);
    document.getElementById('notes-status').innerText = '\u00A0';
}

document.addEventListener('DOMContentLoaded', async function () {
    console.log("Running DOMContentLoaded hook");
    const url = await getActiveTabUrl();
    console.log(url);
    if (url.hostname === 'www.linkedin.com' && url.pathname.startsWith('/in/')) {
        console.log("URL is LinkedIn profile.");
        const profile = extractProfile(url.pathname);
        console.log("Profile: ", profile);
        document.getElementById('not-linkedin-container').style.display = 'none';
        connect();
        document.getElementById('is-linkedin-container').style.display = 'block';

        // Query database storage for note for this profile
        queryDatabase(profile);

        document.getElementById('save-notes-button').addEventListener('click', function() {saveToDatabase(profile)});
        document.getElementById('reset-notes-button').addEventListener('click', function() {discardChanges(profile)});
        document.getElementById('notes-field').addEventListener('input', onNotesFieldChange);

        updateUiState();
    }
});
