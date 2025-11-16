// static/baucua.js (HOÀN CHỈNH - ĐÃ GỘP CHAT)
document.addEventListener('DOMContentLoaded', () => {
    console.log("Baucua.js (Bản V3 + Chat) đã tải!");

    let roomid = null;
    let currentTimerInterval = null;
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    // Lấy các thành phần
    const lobbyDiv = document.getElementById('baucua-lobby');
    const gameDiv = document.getElementById('baucua-game-area');
    const lobbyMsg = document.getElementById('lobby-message');
    const createBtn = document.getElementById('baucua-create-btn');
    const baucuaRoomInput = document.getElementById('baucua-room-input');
    const leaveBtn = document.getElementById('baucua-leave-btn');
    const timerDisplay = document.getElementById('baucua-timer-display');
    const baucuaMsg = document.getElementById('baucua-message');
    const playerList = document.getElementById('baucua-player-list');
    const grid = document.getElementById('betting-grid');

    // SỬA LỖI: Đảm bảo các phần tử xúc xắc được lấy đúng cách
    const die1 = document.getElementById('die1');
    const die2 = document.getElementById('die2');
    const dice = [die1, die2];

    const betAmountSpans = {
        'rockrock': document.getElementById('bet-rockrock'),
        'paperpaper': document.getElementById('bet-paperpaper'),
        'scissorscissor': document.getElementById('bet-scissorscissor'),
        'paperrock': document.getElementById('bet-paperrock'),
        'rockscissor': document.getElementById('bet-rockscissor'),
        'paperscissor': document.getElementById('bet-paperscissor')
    };

    // Lấy username và roomid từ script tag trong game_baucua_6.html
    const scriptElement = document.querySelector('script[src*="baucua.js"]').previousElementSibling;
    const username = scriptElement.textContent.match(/const username = `(.*?)`/)[1];
    const currentRoomIdMatch = scriptElement.textContent.match(/const currentRoomId = `(.*?)`/);
    const currentRoomId = currentRoomIdMatch ? currentRoomIdMatch[1] : '';

    // --- 1. LOGIC VÀO PHÒNG / SẢNH ---
    if (currentRoomId && currentRoomId.trim() !== "") {
        console.log(`Phát hiện Room ID từ URL: ${currentRoomId}`);
        roomid = currentRoomId;
        if(lobbyDiv) lobbyDiv.classList.add('hidden');
        if(gameDiv) gameDiv.classList.remove('hidden');
        socket.emit('player_joined_game_page', {
            'room_id': roomid,
            'username': username
        });
    } else {
        if(lobbyDiv) lobbyDiv.classList.remove('hidden');
        if(gameDiv) gameDiv.classList.add('hidden');
    }

    // --- HÀM HỖ TRỢ ---
    function startTimer(displayElement, seconds) {
        if (currentTimerInterval) clearInterval(currentTimerInterval);
        let timer = seconds;
        if(displayElement) displayElement.innerHTML = `⏳ Đặt cược: ${timer}s`;

        currentTimerInterval = setInterval(() => {
            timer--;
            if(displayElement) displayElement.innerHTML = `⏳ Đặt cược: ${timer}s`;
            if (timer <= 0) {
                clearInterval(currentTimerInterval);
                if(displayElement) displayElement.innerHTML = "Hết giờ!";
                // Server sẽ tự động chuyển trạng thái, client không cần gửi gì thêm.
            }
        }, 1000);
    }

    function stopTimer() {
        if (currentTimerInterval) clearInterval(currentTimerInterval);
    }

    function updatePlayerList(playerNames) {
        if (!playerList) return;
        playerList.innerHTML = "";
        if (playerNames) {
            playerNames.forEach(name => {
                const li = document.createElement('li');
                li.textContent = name;
                playerList.appendChild(li);
            });
        }
    }

    function enableBetting(enable) {
        if (!grid) return;
        grid.style.opacity = enable ? '1' : '0.5';
        grid.style.pointerEvents = enable ? 'auto' : 'none';

        // SỬA LỖI: Reset trạng thái xúc xắc về dấu hỏi
        if (enable && die1 && die2) {
             die1.classList.remove('rolled'); die1.innerHTML = '?';
             die2.classList.remove('rolled'); die2.innerHTML = '?';
        }
    }

    // --- 2. LOGIC NÚT BẤM ---
    if (createBtn) {
        createBtn.onclick = () => {
            let customCode = "";
            if (baucuaRoomInput) customCode = baucuaRoomInput.value.trim();
            if (!customCode) {
                customCode = Math.floor(Math.random() * 9000 + 1000).toString();
            }
            createBtn.disabled = true;
            if(lobbyMsg) lobbyMsg.innerHTML = "Đang tạo phòng...";
            socket.emit('create_room', {
                'username': username,
                'game_mode': 'baucua',
                'room_id_custom': customCode
            });
        };
    }

    if (leaveBtn) {
        leaveBtn.onclick = () => {
            // Yêu cầu server xóa phòng (nếu là host) và rời khỏi phòng
            socket.emit('leave_room', {'room_id': roomid});
            window.location.href = "/lobby/";
        };
    }

    document.querySelectorAll('.bet-button').forEach(button => {
        button.onclick = () => {
            // Kiểm tra trạng thái cược trước khi gửi lệnh
            if (currentTimerInterval) {
                const bet_key = button.dataset.bet;
                // Sửa lỗi: Cần đặt cược tối đa 10v/click (ví dụ)
                socket.emit('baucua_bet', {
                    'room_id': roomid,
                    'bet_type': bet_key,
                    'amount': 10
                });
                button.style.transform = "scale(0.95)";
                setTimeout(() => button.style.transform = "", 100);
            } else {
                // Sửa lỗi: Hiển thị thông báo khi hết giờ
                if(baucuaMsg) baucuaMsg.innerHTML = "Hết giờ đặt cược! Đang chờ kết quả.";
            }
        };
    });

    // --- 3. LẮNG NGHE SERVER ---

    socket.on('join_error', (data) => {
        alert(data.error);
        if(createBtn) createBtn.disabled = false;
        if (roomid) window.location.href = "/lobby/";
    });

    socket.on('room_joined', (data) => {
        // SỬA LỖI CHUYỂN HƯỚNG: Chuyển hướng đến URL Bầu Cua chung (đã sửa)
        if (data.game_mode === 'baucua') {
            window.location.href = "/game_baucua/" + data.room_id; // Sửa lỗi cú pháp URL
        }
    });

    socket.on('baucua_state_update', (data) => {
        updatePlayerList(data.players);

        if (data.state === 'betting') {
            // SỬA LỖI: Đảm bảo timer được reset
            if (data.time_left !== undefined) {
                 startTimer(timerDisplay, data.time_left);
            } else {
                 startTimer(timerDisplay, 15); // Dùng hằng số mặc định
            }
            if(baucuaMsg) baucuaMsg.innerHTML = "Mời đặt cược!";
            enableBetting(true);

        } else if (data.state === 'rolling') {
            stopTimer();
            if(timerDisplay) timerDisplay.innerHTML = "🎲 Đang quay...";
            if(baucuaMsg) baucuaMsg.innerHTML = "Chờ kết quả...";
            enableBetting(false);

            // Xóa hết các cược hiển thị (vì vòng đặt cược kết thúc)
            for (const key in betAmountSpans) {
                 if (betAmountSpans[key]) {
                      betAmountSpans[key].innerHTML = '';
                      betAmountSpans[key].style.display = 'none';
                 }
            }
        }
    });

    socket.on('dice_result', (data) => {
        // SỬA LỖI: Cập nhật logic hiển thị kết quả xúc xắc Bầu Cua

        // 1. Dừng timer và cập nhật tiêu đề
        stopTimer();
        if(timerDisplay) timerDisplay.innerHTML = "⭐️ Kết quả! ⭐️";

        // 2. Ánh xạ xúc xắc sang emoji và hiển thị
        const emojiMap = {
            'rock': '✊',
            'paper': '🖐️',
            'scissor': '✌️'
        };
        const die1Emoji = emojiMap[data.die1] || data.die1;
        const die2Emoji = emojiMap[data.die2] || data.die2;

        // Cập nhật giao diện xúc xắc
        if(die1) { die1.innerHTML = die1Emoji; die1.classList.add('rolled'); }
        if(die2) { die2.innerHTML = die2Emoji; die2.classList.add('rolled'); }

        // 3. Gửi thông báo kết quả vào chat
        const winnersList = data.winners.length > 0 ? `Thắng: ${data.winners.join(', ')}` : 'Không có người chơi thắng cược.';
        const diceMsg = `🎲 KẾT QUẢ QUAY: ${die1Emoji} ${die2Emoji}. ${winnersList}`;
        addChatMessage(null, diceMsg, true);

        // SỬA DỨT ĐIỂM: Sử dụng 'diceMsg' (đã được định nghĩa) thay vì 'msg' (bị lỗi ReferenceError)
        if(baucuaMsg) baucuaMsg.innerHTML = diceMsg;

        // Server sẽ gửi lại baucua_state_update sau 5s để bắt đầu vòng mới.
    });

    socket.on('update_bets', (data) => {
        // Cập nhật tổng số tiền đã cược trên giao diện
        for (const [key, span] of Object.entries(betAmountSpans)) {
            if (span) {
                const amount = data.bets[key] || 0;
                span.innerHTML = amount > 0 ? amount + 'v' : '';
                span.style.display = amount > 0 ? 'block' : 'none';
            }
        }
    });

    // === SỬA LỖI LOGIC HIỂN THỊ TIỀN TỆ ===
    socket.on('currency_update', function(data) {
        const currencyDisplay = document.getElementById('user-currency-display');

        // Nếu không có new_currency, đây không phải là bản tin hợp lệ
        if (!data.hasOwnProperty('new_currency')) return;

        // 1. Cập nhật số tiền trên layout (luôn chạy nếu nhận được)
        if (currencyDisplay) {
            currencyDisplay.innerHTML = `<i class="fas fa-coins"></i> ${data.new_currency}v`;
        }

        // 2. Gửi thông báo chat (chỉ xử lý cho người chơi này)
        // Server gửi 'amount' là số tiền đặt cược (âm) hoặc tiền lãi/lỗ ròng (âm/dương)

        if (data.amount < 0) {
            // Phân biệt TRỪ TIỀN CƯỢC và THUA RÒNG
            if (data.winner_username === username) {
                // Đây là lúc đặt cược (winner_username là mình, amount < 0)
                addChatMessage(null, `Bạn đã đặt cược ${-data.amount}v.`, true);
            } else {
                // Đây là lúc thua ròng (winner_username = None, amount < 0)
                addChatMessage(null, `Bạn đã thua ròng ${-data.amount}v.`, true);
            }
        } else if (data.amount > 0) {
            // Đây là lúc thắng ròng (winner_username là mình, amount > 0)
            addChatMessage(null, `Bạn đã thắng ròng ${data.amount}v!`, true);
        }
        // Nếu amount = 0 (hòa vốn), không cần thông báo gì thêm
    });
    // === KẾT THÚC SỬA LỖI ===


    socket.on('baucua_error', (data) => {
        if (baucuaMsg) {
            const oldMsg = baucuaMsg.innerHTML;
            baucuaMsg.innerHTML = `<span style="color: red; animation: shake 0.5s;">${data.error}</span>`;
            setTimeout(() => { if (baucuaMsg.innerHTML.includes(data.error)) baucuaMsg.innerHTML = oldMsg; }, 2000);
        }
    });

    // --- LOGIC CHAT (ĐÃ THÊM VÀO ĐÂY) ---
    const chatBox = document.getElementById('chat-box');
    const chatInput = document.getElementById('chat-input');
    const chatForm = document.getElementById('chat-form');

    function addChatMessage(username, message, isSystem = false) {
        if (chatBox) {
            const p = document.createElement('p');
            p.innerHTML = isSystem ? `<em>${message}</em>` : `<strong>${username}:</strong> ${message}`;
            chatBox.appendChild(p);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    }

    if (chatForm) {
        chatForm.onsubmit = (e) => {
            e.preventDefault();
            const message = chatInput.value;
            if (message.trim() !== "" && roomid) {
                socket.emit('send_message', {'room_id': roomid, 'message': message, 'username': username});
                chatInput.value = "";
            }
        };
    }

    socket.on('receive_message', function(data) {
        addChatMessage(data.username, data.message);
    });

    socket.on('system_message', function(data) {
        addChatMessage(null, data.message, true);
    });
    // --- KẾT THÚC LOGIC CHAT ---

}); // <-- Dấu đóng file (Chỉ có 1 dấu)