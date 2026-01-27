const sidebar = document.querySelector('.sidebar');
const chatDrawer = document.querySelector('.chat-drawer');
const toggleSidebarBtn = document.getElementById('toggleSidebar');
const hideSidebarBtn = document.getElementById('hideSidebar');
const toggleChatMenuBtn = document.getElementById('toggleChatMenu');
const hideChatMenuBtn = document.getElementById('hideChatMenu');
const toggleDarkModeBtn = document.getElementById('toggleDarkMode');

if (toggleSidebarBtn && sidebar) {
    toggleSidebarBtn.addEventListener('click', function() {
        sidebar.classList.toggle('show');
    });
}

if (hideSidebarBtn && sidebar) {
    hideSidebarBtn.addEventListener('click', function() {
        sidebar.classList.remove('show');
    });
}

if (toggleChatMenuBtn && chatDrawer) {
    toggleChatMenuBtn.addEventListener('click', function() {
        chatDrawer.classList.toggle('is-open');
    });
}

if (hideChatMenuBtn && chatDrawer) {
    hideChatMenuBtn.addEventListener('click', function() {
        chatDrawer.classList.remove('is-open');
    });
}

if (toggleDarkModeBtn) {
    toggleDarkModeBtn.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const pinnedMessagesList = document.getElementById('pinnedMessagesList');
    const existingPinned = new Set();
    if (pinnedMessagesList) {
        Array.from(pinnedMessagesList.querySelectorAll('[data-message-id]'))
            .map((item) => item.dataset.messageId)
            .forEach((messageId) => existingPinned.add(messageId));
    }
    const conversationId = document.body.dataset.conversationId;

    function removePinnedMessage(messageId) {
        if (!messageId) {
            return;
        }
        existingPinned.delete(messageId);
        if (!pinnedMessagesList) {
            return;
        }
        const item = pinnedMessagesList.querySelector(
            `[data-message-id="${messageId}"]`
        );
        if (item) {
            item.remove();
        }
    }

    function addPinnedMessage(pinned) {
        if (!pinned || !pinned.message_id) {
            return;
        }
        if (existingPinned.has(pinned.message_id)) {
            return;
        }
        existingPinned.add(pinned.message_id);
        if (!pinnedMessagesList) {
            return;
        }
        const pinnedMessageItem = document.createElement('li');
        pinnedMessageItem.classList.add('list-group-item', 'pinned-message-item');
        pinnedMessageItem.dataset.messageId = pinned.message_id;
        pinnedMessageItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${pinned.creator.name}:</strong> ${pinned.text}<br><em>${pinned.created_date}</em>
                </div>
                <button class="pin-message-btn unpin-message-btn" aria-label="Unpin Message">
                    <i class="fas fa-thumbtack"></i>
                </button>
            </div>
        `;
        pinnedMessagesList.appendChild(pinnedMessageItem);
    }

    function unpinMessage(messageId) {
        if (!messageId) {
            return;
        }
        if (!conversationId) {
            removePinnedMessage(messageId);
            return;
        }
        fetch('/unpin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: messageId, conversation_id: conversationId })
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Failed to unpin message');
                }
                return response.json();
            })
            .then(function() {
                removePinnedMessage(messageId);
            })
            .catch(function() {
                removePinnedMessage(messageId);
            });
    }

    if (pinnedMessagesList) {
        pinnedMessagesList.addEventListener('click', function(event) {
            const target = event.target.closest('.unpin-message-btn');
            if (!target) {
                return;
            }
            const item = target.closest('[data-message-id]');
            if (!item) {
                return;
            }
            unpinMessage(item.dataset.messageId);
        });
    }

    // Add event listener to pin buttons
    document.querySelectorAll('.pin-message-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            if (this.classList.contains('unpin-message-btn')) {
                return;
            }
            const messageElement = this.closest('.message');
            if (!messageElement) {
                return;
            }
            const messageId = messageElement.dataset.messageId;
            if (!messageId) {
                return;
            }
            if (existingPinned.has(messageId)) {
                unpinMessage(messageId);
                return;
            }
            const messageTextElement = messageElement.querySelector('.message-text');
            const messageText = messageTextElement ? messageTextElement.textContent.trim() : '';
            const messageCreator = messageElement.querySelector('.member').textContent.trim();
            const messageDate = messageElement.querySelector('.timestamp').textContent.trim();

            if (!conversationId) {
                return;
            }
            fetch('/pin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message_id: messageId, conversation_id: conversationId })
            })
                .then(function(response) {
                    if (!response.ok) {
                        throw new Error('Failed to pin message');
                    }
                    return response.json();
                })
                .then(function(data) {
                    if (data && data.pinned) {
                        addPinnedMessage(data.pinned);
                        return;
                    }
                    addPinnedMessage({
                        message_id: messageId,
                        creator: { name: messageCreator },
                        text: messageText,
                        created_date: messageDate
                    });
                })
                .catch(function() {
                    addPinnedMessage({
                        message_id: messageId,
                        creator: { name: messageCreator },
                        text: messageText,
                        created_date: messageDate
                    });
                });
        });
    });

    const pinnedChatsList = document.getElementById('pinnedChatsList');
    const pinnedChatIds = new Set();
    const pinnedChatsToggle = document.querySelector(
        '.drawer-section-toggle[data-target="pinnedChatsList"]'
    );
    const pinnedChatsCount = pinnedChatsToggle
        ? pinnedChatsToggle.querySelector('.drawer-section-count')
        : null;
    const pinnedChatsEmpty = pinnedChatsList
        ? pinnedChatsList.querySelector('[data-empty-state="pinned"]')
        : null;

    if (pinnedChatsList) {
        Array.from(pinnedChatsList.querySelectorAll('li[data-conversation-id]'))
            .map((item) => item.dataset.conversationId)
            .forEach((conversationId) => pinnedChatIds.add(conversationId));
    }

    function updatePinnedChatsCount() {
        if (pinnedChatsCount) {
            pinnedChatsCount.textContent = String(pinnedChatIds.size);
        }
        if (!pinnedChatsList) {
            return;
        }
        const hasItems = pinnedChatsList.querySelectorAll('li[data-conversation-id]').length > 0;
        if (pinnedChatsEmpty) {
            pinnedChatsEmpty.style.display = hasItems ? 'none' : '';
        } else if (!hasItems) {
            const emptyItem = document.createElement('li');
            emptyItem.classList.add('chat-list-empty');
            emptyItem.dataset.emptyState = 'pinned';
            emptyItem.textContent = 'No pinned chats yet';
            pinnedChatsList.appendChild(emptyItem);
        }
    }

    function updateChatPinButtons(conversationId, isPinned) {
        document
            .querySelectorAll(`.pin-chat-btn[data-conversation-id="${conversationId}"]`)
            .forEach(function(button) {
                button.classList.toggle('is-pinned', isPinned);
                if (!button.classList.contains('unpin-chat-btn')) {
                    button.setAttribute('aria-label', isPinned ? 'Unpin chat' : 'Pin chat');
                }
            });
    }

    function removePinnedChat(conversationId) {
        pinnedChatIds.delete(conversationId);
        if (pinnedChatsList) {
            const item = pinnedChatsList.querySelector(
                `li[data-conversation-id="${conversationId}"]`
            );
            if (item) {
                item.remove();
            }
        }
        updateChatPinButtons(conversationId, false);
        updatePinnedChatsCount();
    }

    function buildPinnedChatItem(conversation) {
        if (!pinnedChatsList || !conversation) {
            return;
        }
        const conversationId = String(conversation.id);
        if (pinnedChatIds.has(conversationId)) {
            return;
        }
        const sourceItem = document.querySelector(
            `.chat-item[data-conversation-id="${conversationId}"]`
        );
        const href = sourceItem ? sourceItem.getAttribute('href') : `/chat/${conversation.dir_name}`;
        const searchText = sourceItem ? sourceItem.getAttribute('data-search') : conversation.display_name;
        const isActive = sourceItem ? sourceItem.classList.contains('is-active') : false;
        const metaLabel = conversation.conv_type === 'dm' ? 'DM' : 'Space';
        const metaText = `${metaLabel} \u00b7 ${conversation.members_count || 0} members`;
        const iconClass = conversation.emoji_id ? 'chat-icon--emoji' : 'chat-icon--initials';

        const item = document.createElement('li');
        item.dataset.conversationId = conversationId;
        item.innerHTML = `
            <div class="chat-item-row">
                <a href="${href}"
                   class="chat-item ${isActive ? 'is-active' : ''}"
                   data-conversation-id="${conversationId}"
                   data-search="${searchText || ''}">
                    <span class="chat-icon ${iconClass}">${conversation.icon_text || ''}</span>
                    <span class="chat-item-text">
                        <span class="chat-name">${conversation.display_name || ''}</span>
                        <span class="chat-meta">${metaText}</span>
                    </span>
                </a>
                <button class="pin-chat-btn unpin-chat-btn is-pinned" aria-label="Unpin chat" data-conversation-id="${conversationId}">
                    <i class="fas fa-thumbtack"></i>
                </button>
            </div>
        `;
        if (pinnedChatsEmpty) {
            pinnedChatsEmpty.style.display = 'none';
        }
        pinnedChatsList.appendChild(item);
        pinnedChatIds.add(conversationId);
        updateChatPinButtons(conversationId, true);
        updatePinnedChatsCount();
    }

    function pinChat(conversationId) {
        fetch('/pin-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conversation_id: conversationId })
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Failed to pin chat');
                }
                return response.json();
            })
            .then(function(data) {
                if (data && data.conversation) {
                    buildPinnedChatItem(data.conversation);
                }
            })
            .catch(function() {
                const fallback = document.querySelector(
                    `.chat-item[data-conversation-id="${conversationId}"]`
                );
                if (!fallback) {
                    return;
                }
                buildPinnedChatItem({
                    id: conversationId,
                    dir_name: fallback.getAttribute('href')?.replace('/chat/', '') || '',
                    display_name: fallback.querySelector('.chat-name')?.textContent || '',
                    conv_type: fallback.querySelector('.chat-meta')?.textContent.includes('DM') ? 'dm' : 'space',
                    icon_text: fallback.querySelector('.chat-icon')?.textContent || '',
                    emoji_id: fallback.querySelector('.chat-icon')?.classList.contains('chat-icon--emoji') ? 'emoji' : '',
                    members_count: 0
                });
            });
    }

    function unpinChat(conversationId) {
        fetch('/unpin-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conversation_id: conversationId })
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Failed to unpin chat');
                }
                return response.json();
            })
            .then(function() {
                removePinnedChat(conversationId);
            })
            .catch(function() {
                removePinnedChat(conversationId);
            });
    }

    document.addEventListener('click', function(event) {
        const button = event.target.closest('.pin-chat-btn');
        if (!button) {
            return;
        }
        const conversationId = button.dataset.conversationId;
        if (!conversationId) {
            return;
        }
        if (pinnedChatIds.has(conversationId)) {
            unpinChat(conversationId);
        } else {
            pinChat(conversationId);
        }
    });

    updatePinnedChatsCount();
});

document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('assignUserModal');
    if (!modal) {
        return;
    }
    const userList = modal.querySelector('#assignUserList');
    const searchInput = modal.querySelector('#assignUserSearch');
    const addUserButton = modal.querySelector('#showAddUserForm');
    const addUserForm = modal.querySelector('#addUserForm');
    const cancelAddUser = modal.querySelector('#cancelAddUser');
    const statusMessage = modal.querySelector('#assignUserStatus');
    const preview = modal.querySelector('#assignUserMessagePreview');
    const closeButton = modal.querySelector('.assign-user-close');
    const backdrop = modal.querySelector('.assign-user-backdrop');
    const membersList = document.querySelector('.member-list');
    const messageList = document.getElementById('messageList');
    const conversationId = document.body.dataset.conversationId;
    const assignableUsers = Array.isArray(window.assignableUsers)
        ? window.assignableUsers.slice()
        : [];

    let activeMessageElement = null;

    function setStatus(text, isError) {
        if (!statusMessage) {
            return;
        }
        statusMessage.textContent = text || '';
        if (isError) {
            statusMessage.style.color = 'var(--accent-strong)';
        } else {
            statusMessage.style.color = '';
        }
    }

    function renderUserList(filterText) {
        if (!userList) {
            return;
        }
        const query = (filterText || '').toLowerCase();
        userList.innerHTML = '';
        const filtered = assignableUsers.filter(function(user) {
            const name = (user.name || '').toLowerCase();
            const email = (user.email || '').toLowerCase();
            return name.includes(query) || email.includes(query);
        });
        if (!filtered.length) {
            const empty = document.createElement('p');
            empty.className = 'assign-user-empty';
            empty.textContent = 'No matching users yet.';
            userList.appendChild(empty);
            return;
        }
        filtered.forEach(function(user) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'assign-user-item';
            button.dataset.userId = user.id;
            const name = document.createElement('strong');
            name.textContent = user.name || 'Unnamed user';
            const meta = document.createElement('span');
            if (user.email) {
                meta.textContent = user.email;
            } else {
                meta.textContent = user.user_type || 'User';
            }
            button.appendChild(name);
            button.appendChild(meta);
            userList.appendChild(button);
        });
    }

    function openModal(messageElement) {
        activeMessageElement = messageElement;
        const messageText = messageElement
            ? messageElement.querySelector('.message-text')?.textContent.trim()
            : '';
        const previewText = messageText ? messageText.slice(0, 160) : '';
        if (preview) {
            preview.textContent = previewText
                ? `“${previewText}${messageText.length > 160 ? '…' : ''}”`
                : 'Select a user to assign this message.';
        }
        setStatus('');
        if (searchInput) {
            searchInput.value = '';
            searchInput.disabled = false;
            searchInput.focus();
        }
        if (userList) {
            userList.style.display = '';
        }
        if (addUserButton) {
            addUserButton.disabled = false;
        }
        if (addUserForm) {
            addUserForm.hidden = true;
            addUserForm.reset();
        }
        renderUserList('');
        if (modal) {
            modal.classList.add('is-visible');
            modal.setAttribute('aria-hidden', 'false');
        }
    }

    function closeModal() {
        activeMessageElement = null;
        setStatus('');
        if (modal) {
            modal.classList.remove('is-visible');
            modal.setAttribute('aria-hidden', 'true');
        }
    }

    function assignMessageToUser(user) {
        if (!activeMessageElement || !conversationId || !user || !user.id) {
            return;
        }
        const messageId = activeMessageElement.dataset.messageId;
        if (!messageId) {
            return;
        }
        setStatus('Assigning message…');
        fetch('/assign-message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message_id: messageId,
                conversation_id: conversationId,
                user_id: user.id
            })
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Failed to assign message');
                }
                return response.json();
            })
            .then(function(data) {
                if (!data || !data.user) {
                    throw new Error('Missing user payload');
                }
                let resolvedColor = '';
                if (membersList && data.user && data.user.name) {
                    const memberItems = Array.from(membersList.querySelectorAll('li'));
                    const match = memberItems.find(function(item) {
                        return item.textContent.trim().startsWith(data.user.name);
                    });
                    if (match && match.style.color) {
                        resolvedColor = match.style.color;
                    }
                }
                if (!resolvedColor && data.member_color) {
                    resolvedColor = data.member_color;
                }
                const memberEl = activeMessageElement.querySelector('.member');
                if (memberEl) {
                    memberEl.textContent = data.user.name;
                }
                if (resolvedColor) {
                    activeMessageElement.style.borderColor = resolvedColor;
                    if (memberEl) {
                        memberEl.style.color = resolvedColor;
                    }
                }
                const assignBtn = activeMessageElement.querySelector('.assign-user-btn');
                if (assignBtn) {
                    assignBtn.remove();
                }
                if (data.member_added && membersList) {
                    const item = document.createElement('li');
                    item.className = 'list-group-item';
                    if (data.member_color) {
                        item.style.color = data.member_color;
                    }
                    const emailSuffix = data.user.email ? ` (${data.user.email})` : '';
                    item.textContent = `${data.user.name}${emailSuffix}`;
                    membersList.appendChild(item);
                }
                setStatus('Message reassigned.');
                closeModal();
            })
            .catch(function() {
                setStatus('Could not assign message. Try again.', true);
            });
    }

    if (messageList) {
        messageList.addEventListener('click', function(event) {
            const trigger = event.target.closest('.assign-user-btn');
            if (!trigger) {
                return;
            }
            const messageElement = trigger.closest('.message');
            if (!messageElement) {
                return;
            }
            openModal(messageElement);
        });
    }

    if (userList) {
        userList.addEventListener('click', function(event) {
            const button = event.target.closest('.assign-user-item');
            if (!button) {
                return;
            }
            const userId = Number(button.dataset.userId);
            const user = assignableUsers.find(function(entry) {
                return entry.id === userId;
            });
            if (user) {
                assignMessageToUser(user);
            }
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            renderUserList(searchInput.value);
        });
    }

    if (addUserButton && addUserForm && searchInput) {
        addUserButton.addEventListener('click', function() {
            addUserForm.hidden = false;
            searchInput.value = '';
            searchInput.disabled = true;
            if (userList) {
                userList.style.display = 'none';
            }
            addUserButton.disabled = true;
            setStatus('');
        });
    }

    if (cancelAddUser && addUserForm && addUserButton && searchInput) {
        cancelAddUser.addEventListener('click', function() {
            addUserForm.hidden = true;
            addUserButton.disabled = false;
            searchInput.disabled = false;
            if (userList) {
                userList.style.display = '';
            }
            addUserForm.reset();
            renderUserList('');
        });
    }

    if (addUserForm) {
        addUserForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const nameInput = addUserForm.querySelector('#assignUserName');
            const emailInput = addUserForm.querySelector('#assignUserEmail');
            const typeInput = addUserForm.querySelector('#assignUserType');
            const name = nameInput ? nameInput.value.trim() : '';
            const email = emailInput ? emailInput.value.trim() : '';
            const userType = typeInput ? typeInput.value : 'Human';
            if (!name) {
                setStatus('Please provide a full name.', true);
                return;
            }
            setStatus('Creating user…');
            fetch('/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    email: email,
                    user_type: userType
                })
            })
                .then(function(response) {
                    if (!response.ok) {
                        throw new Error('Failed to create user');
                    }
                    return response.json();
                })
                .then(function(data) {
                    if (!data || !data.user) {
                        throw new Error('Missing user payload');
                    }
                    assignableUsers.push(data.user);
                    assignableUsers.sort(function(a, b) {
                        return (a.name || '').localeCompare(b.name || '');
                    });
                    if (addUserForm) {
                        addUserForm.hidden = true;
                        addUserForm.reset();
                    }
                    if (addUserButton) {
                        addUserButton.disabled = false;
                    }
                    if (searchInput) {
                        searchInput.disabled = false;
                    }
                    if (userList) {
                        userList.style.display = '';
                    }
                    renderUserList('');
                    assignMessageToUser(data.user);
                })
                .catch(function() {
                    setStatus('Could not create user. Try again.', true);
                });
        });
    }

    if (closeButton) {
        closeButton.addEventListener('click', closeModal);
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeModal);
    }

    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal.classList.contains('is-visible')) {
            closeModal();
        }
    });
});

const scrollToBottomBtn = document.getElementById('scrollToBottom');
if (scrollToBottomBtn) {
    scrollToBottomBtn.addEventListener('click', function() {
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    });

    window.addEventListener('scroll', function() {
        if (window.scrollY > 300) {
            scrollToBottomBtn.style.display = 'flex';
        } else {
            scrollToBottomBtn.style.display = 'none';
        }
    });
}

const searchBar = document.querySelector('.search-bar');
const searchInput = document.getElementById('searchInput');
const messages = document.querySelectorAll('.message');
const chatSearchInput = document.getElementById('chatSearchInput');

function isEditableTarget(target) {
    if (!target) {
        return false;
    }
    const tagName = target.tagName ? target.tagName.toLowerCase() : '';
    return target.isContentEditable || tagName === 'input' || tagName === 'textarea' || tagName === 'select';
}

function filterMessages() {
    if (!searchInput) {
        return;
    }
    var filter = searchInput.value.toLowerCase();
    messages.forEach(function(message) {
        var text = message.textContent.toLowerCase();
        message.style.display = text.includes(filter) ? '' : 'none';
    });
}

if (searchInput) {
    searchInput.addEventListener('input', filterMessages);
}

const toggleSearchBtn = document.getElementById('toggleSearch');
if (toggleSearchBtn && searchBar && searchInput) {
    toggleSearchBtn.addEventListener('click', function() {
        if (!searchBar.classList.contains('is-visible')) {
            searchBar.classList.add('is-visible');
            searchInput.focus();
        } else {
            searchBar.classList.remove('is-visible');
            searchInput.value = '';
            filterMessages();
        }
    });
}

if (chatSearchInput) {
    chatSearchInput.addEventListener('input', function() {
        const filter = chatSearchInput.value.toLowerCase();
        document.querySelectorAll('.chat-item').forEach(function(item) {
            const searchText = item.getAttribute('data-search') || '';
            const match = searchText.includes(filter);
            const listItem = item.closest('li');
            if (listItem) {
                listItem.style.display = match ? '' : 'none';
            }
        });
    });
}

document.addEventListener('keydown', function(event) {
    if (event.key !== 'f' || !(event.ctrlKey || event.metaKey) || isEditableTarget(event.target)) {
        return;
    }
    event.preventDefault();
    if (searchInput && searchBar) {
        searchBar.classList.add('is-visible');
        searchInput.focus();
        searchInput.select();
        return;
    }
    if (chatSearchInput) {
        chatSearchInput.focus();
        chatSearchInput.select();
    }
});

document.querySelectorAll('.drawer-section-toggle').forEach(function(toggle) {
    toggle.addEventListener('click', function() {
        const targetId = toggle.getAttribute('data-target');
        const list = document.getElementById(targetId);
        if (!list) {
            return;
        }
        const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
        toggle.setAttribute('aria-expanded', String(!isExpanded));
        list.style.display = isExpanded ? 'none' : '';
    });
});

const imageLightbox = document.getElementById('imageLightbox');
const lightboxImage = document.getElementById('lightboxImage');
const lightboxClose = document.querySelector('.image-lightbox-close');

function closeLightbox() {
    if (!imageLightbox || !lightboxImage) {
        return;
    }
    imageLightbox.classList.remove('is-visible');
    imageLightbox.setAttribute('aria-hidden', 'true');
    lightboxImage.src = '';
}

if (imageLightbox && lightboxImage) {
    document.addEventListener('click', function(event) {
        const target = event.target;
        if (target && target.tagName === 'IMG' && (target.closest('.attachments') || target.closest('.annotation-box'))) {
            event.preventDefault();
            lightboxImage.src = target.src;
            imageLightbox.classList.add('is-visible');
            imageLightbox.setAttribute('aria-hidden', 'false');
        }
    });
}

if (lightboxClose) {
    lightboxClose.addEventListener('click', closeLightbox);
}

if (imageLightbox) {
    imageLightbox.addEventListener('click', function(event) {
        if (event.target.classList.contains('image-lightbox-backdrop')) {
            closeLightbox();
        }
    });
}
