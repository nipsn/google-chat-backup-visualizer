document.getElementById('toggleSidebar').addEventListener('click', function() {
    document.querySelector('.sidebar').classList.toggle('show');
});

document.getElementById('hideSidebar').addEventListener('click', function() {
    document.querySelector('.sidebar').classList.remove('show');
});

document.getElementById('toggleDarkMode').addEventListener('click', function() {
    document.body.classList.toggle('dark-mode');
});

document.addEventListener('DOMContentLoaded', function() {
    const pinnedMessagesList = document.getElementById('pinnedMessagesList');
    const pinnedMessages = JSON.parse(localStorage.getItem('pinnedMessages')) || [];

    // Load pinned messages from local storage
    pinnedMessages.forEach(function(message) {
        const pinnedMessageItem = document.createElement('li');
        pinnedMessageItem.classList.add('list-group-item');
        pinnedMessageItem.innerHTML = `<strong>${message.creator}:</strong> ${message.text}<br><em>${message.date}</em>`;
        pinnedMessagesList.appendChild(pinnedMessageItem);
    });

    // Add event listener to pin buttons
    document.querySelectorAll('.pin-message-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const messageElement = this.closest('.message');
            const messageText = messageElement.querySelector('.member').nextSibling.textContent.trim();
            const messageCreator = messageElement.querySelector('.member').textContent.trim();
            const messageDate = messageElement.querySelector('em').textContent.trim();

            const pinnedMessage = {
                creator: messageCreator,
                text: messageText,
                date: messageDate
            };

            // Store pinned message in local storage
            pinnedMessages.push(pinnedMessage);
            localStorage.setItem('pinnedMessages', JSON.stringify(pinnedMessages));

            // Add pinned message to the sidebar
            const pinnedMessageItem = document.createElement('li');
            pinnedMessageItem.classList.add('list-group-item');
            pinnedMessageItem.innerHTML = `<strong>${messageCreator}:</strong> ${messageText}<br><em>${messageDate}</em>`;
            pinnedMessagesList.appendChild(pinnedMessageItem);
        });
    });
});

document.getElementById('scrollToBottom').addEventListener('click', function() {
    window.scrollTo(0, document.body.scrollHeight);
});

window.addEventListener('scroll', function() {
    var scrollToBottomBtn = document.getElementById('scrollToBottom');
    if (window.scrollY > 300) {
        scrollToBottomBtn.style.display = 'flex';
    } else {
        scrollToBottomBtn.style.display = 'none';
    }
});

document.getElementById('toggleSearch').addEventListener('click', function() {
    var searchBar = document.querySelector('.search-bar');
    var searchInput = document.getElementById('searchInput');
    var messages = document.querySelectorAll('.message');
    if (searchBar.style.display === 'none' || searchBar.style.display === '') {
        searchBar.style.display = 'block';
        searchInput.addEventListener('input', function() {
            var filter = this.value.toLowerCase();
            messages.forEach(function(message) {
                var text = message.textContent.toLowerCase();
                if (text.includes(filter)) {
                    message.style.display = '';
                } else {
                    message.style.display = 'none';
                }
            });
        });
    } else {
        searchBar.style.display = 'none';
        searchInput.value = '';
        messages.forEach(function(message) {
            message.style.display = '';
        });
    }
});