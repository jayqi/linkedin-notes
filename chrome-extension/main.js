const hostName = 'com.jayqi.linkedin_notes_storage';
let port = null;
let profile = null;

async function onNativeMessage(message) {
    if (message.mode == 'read') {
        document.getElementById('notes-field').placeholder = 'Enter a note here.';
        if (message.payload.text) {
            console.log("Successfully retrieved note from database.");
            document.getElementById('notes-field').value = message.payload.text;
        } else {
            console.log("Note is blank.");
        }
        document.getElementById('save-notes-button').setAttribute('disabled', '');
        document.getElementById('reset-notes-button').setAttribute('disabled', '');
        // Check cache for unsaved changes
        const cached_text = await readCache();
        if (cached_text) {
            document.getElementById('notes-field').value = cached_text;
            document.getElementById('notes-status').innerText = 'You have unsaved changes.';
            document.getElementById('save-notes-button').removeAttribute('disabled');
            document.getElementById('reset-notes-button').removeAttribute('disabled');
        }
        document.getElementById('notes-field').removeAttribute('disabled');
    } else if (message.mode == 'write') {
        if (message.payload.success) {
            console.log("Successfully saved note to database.");
            document.getElementById('notes-status').innerText = 'Changes saved.';
            document.getElementById('save-notes-button').setAttribute('disabled', '');
            document.getElementById('reset-notes-button').setAttribute('disabled', '');
            await removeCache();
        } else {
            console.log("Failed to save note to database.");
            document.getElementById('notes-status').innerText = 'Changes failed to save.';
        }
    } else {
        console.log("Invalid message mode.");
    }
}

function onDisconnected() {
    port = null;
}

async function getActiveTabUrl() {
    const queryOptions = { active: true, currentWindow: true };
    const [tab] = await chrome.tabs.query(queryOptions);
    return new URL(tab.url);
}

function setProfile(pathname) {
    const regex = /^\/in\/[^\/]+\//;
    const match = pathname.match(regex);
    profile = match ? match[0] : null;
}

function queryDatabase() {
    message = { profile: profile, mode: 'read' };
    port.postMessage(message);
}

function saveToDatabase() {
    message = { profile: profile, text: document.getElementById('notes-field').value, mode: 'write' };
    port.postMessage(message);
}

async function writeCache(text) {
    console.log("Writing cache: ", profile);
    await chrome.storage.local.set({[profile]: text});
    console.log("Cache written.")
}

async function readCache() {
    console.log("Reading from cache: ", profile)
    const result = await chrome.storage.local.get([profile]);
    console.log("Cache read: ", result);
    if (profile in result) {
        return result[profile];
    } else {
        return null;
    }
}

async function removeCache() {
    console.log("Removing cache for: ", profile);
    await chrome.storage.local.remove([profile]);
    console.log("Cache removed.");
}

async function onNotesFieldChange() {
    document.getElementById('notes-status').innerText = 'You have unsaved changes.';
    document.getElementById('save-notes-button').removeAttribute('disabled');
    document.getElementById('reset-notes-button').removeAttribute('disabled');
    await writeCache(document.getElementById('notes-field').value);
}

async function discardChanges() {
    // Query database to reset notes
    queryDatabase();
    document.getElementById('notes-status').innerText = 'Changes discarded.';
    await removeCache();
}

document.addEventListener('DOMContentLoaded', async function () {
    console.log("Running DOMContentLoaded hook");

    const url = await getActiveTabUrl();
    console.log(url);
    if (url.hostname === 'www.linkedin.com' && url.pathname.startsWith('/in/')) {
        console.log("Active tab is a LinkedIn profile.");
        setProfile(url.pathname);
        console.log("Profile: ", profile);

        document.getElementById('not-linkedin-container').style.display = 'none';
        document.getElementById('is-linkedin-container').style.display = 'block';

        // Connect to native messaging host
        port = chrome.runtime.connectNative(hostName);
        port.onMessage.addListener(onNativeMessage);
        port.onDisconnect.addListener(onDisconnected);

        // Query database storage for notes for this profile
        queryDatabase(profile);

        // Register event listeners
        document.getElementById('save-notes-button').addEventListener('click', saveToDatabase);
        document.getElementById('reset-notes-button').addEventListener('click', discardChanges);
        document.getElementById('notes-field').addEventListener('input', onNotesFieldChange);
    }
});
