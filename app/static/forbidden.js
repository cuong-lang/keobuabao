// static/forbidden.js (ĐÃ THÊM CHAT ĐÚNG VỊ TRÍ)
document.addEventListener('DOMContentLoaded', () => {
    console.log("Forbidden.js (Bí mật + Chat) đã tải!");

    let roomid = null;
    let currentTimerInterval = null;
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    // Lấy các thành phần
    const lobbyDiv = document.getElementById('forbidden-lobby');
    const gameDiv = document.getElementById('forbidden-game-area');
    const createBtn = document.getElementById('forbidden-create-btn');
    const roomInput = document.getElementById('forbidden-room-input');
    const leaveBtn = document.getElementById('forbidden-leave-btn');
    const playerList = document.getElementById('forbidden-player-list');
    const statusDisplay = document.getElementById('forbidden-status-display');
    const timerDisplay = document.getElementById('forbidden-timer');
    const resultDisplay = document.getElementById('forbidden-result-display');
    const bannedCardSpan = document.getElementById('banned-card-reveal');
    const gameControls = document.getElementById('game-controls');
    const checkpointControls = document.getElementById('checkpoint-controls');

    // === THÊM NÚT MỚI ===
    const startBtn = document.getElementById('forbidden-start-btn');

    const choiceButtons = {
        'rock': document.getElementById('btn-rock'),
        'paper': document.getElementById('btn-paper'),
        'scissor': document.getElementById('btn-scissor')
    };
    const btnStop = document.getElementById('btn-stop');
    const btnContinue = document.getElementById('btn-continue');

    // --- 1. LOGIC VÀO PHÒNG / SẢNH ---
    if (typeof currentRoomId !== 'undefined' && currentRoomId.trim() !== "") {
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

    // --- 2. LOGIC NÚT BẤM ---
    if (createBtn) {
        createBtn.onclick = () => {
            let customCode = "";
            if (roomInput) customCode = roomInput.value.trim();
            if (!customCode) customCode = Math.floor(Math.random() * 9000 + 1000).toString();
            createBtn.disabled = true;
            socket.emit('create_room', {
                'username': username,
                'game_mode': 'forbidden',
                'room_id_custom': customCode
            });
        };
    }
    if (leaveBtn) {
        leaveBtn.onclick = () => window.location.href = "/game_forbidden/";
    }

    // === THÊM SỰ KIỆN CLICK CHO NÚT BẮT ĐẦU ===
    if (startBtn) {
        startBtn.onclick = () => {
            socket.emit('forbidden_start_game', {'room_id': roomid});
            startBtn.classList.add('hidden'); // Ẩn nút sau khi bấm
        };
    }

    Object.entries(choiceButtons).forEach(([choice, button]) => {
        if (button) {
            button.onclick = () => {
                socket.emit('forbidden_choice', {'room_id': roomid, 'choice': choice});
                enableChoiceButtons(false, null);
                statusDisplay.innerHTML = "Bạn đã chọn. Chờ kết quả...";
            };
        }
    });

    if(btnStop) btnStop.onclick = () => {
        socket.emit('forbidden_stop', {'room_id': roomid});
        checkpointControls.classList.add('hidden');
    };
    if(btnContinue) btnContinue.onclick = () => {
        checkpointControls.classList.add('hidden');
        statusDisplay.innerHTML = "Bạn đã chọn chơi tiếp! Chờ vòng 6...";
    };

    // --- HÀM HỖ TRỢ GIAO DIỆN ---
    function enableChoiceButtons(enable, forbiddenChoice) {
        Object.entries(choiceButtons).forEach(([choice, button]) => {
            if (button) {
                button.disabled = !enable;
                if (enable) {
                    button.style.opacity = '1';
                }
            }
        });
    }

    function updatePlayerList(playersData) {
        if (!playerList) return;
        playerList.innerHTML = "";
        if (playersData) {
            Object.values(playersData).forEach(p => {
                const li = document.createElement('li');
                li.textContent = `${p.username} (Thắng: ${p.wins})`;
                li.className = `status-${p.status}`;
                playerList.appendChild(li);
            });
        }
    }

    // --- 3. LẮNG NGHE SERVER ---
    socket.on('join_error', (data) => {
        alert(data.error);
        if(createBtn) createBtn.disabled = false;
        if (roomid) window.location.href = "/game_forbidden/";
    });

    socket.on('room_joined', (data) => {
        if (data.game_mode === 'forbidden') {
            window.location.href = "/game_forbidden/" + data.room_id;
        }
    });

    socket.on('forbidden_state_update', (data) => {
        if(data.message) statusDisplay.innerHTML = data.message;
        if(data.players_data) updatePlayerList(data.players_data);

        // === THÊM LOGIC HIỂN THỊ NÚT BẮT ĐẦU ===
        if (data.state === 'waiting') {
            if (startBtn) startBtn.classList.remove('hidden');
            if (gameControls) gameControls.classList.add('hidden');
            if (timerDisplay) timerDisplay.innerHTML = "Đang chờ";
        } else {
            if (startBtn) startBtn.classList.add('hidden');
            if (gameControls) gameControls.classList.remove('hidden');
        }
        // === KẾT THÚC LOGIC MỚI ===
    });

    socket.on('forbidden_new_round', (data) => {
        statusDisplay.innerHTML = `Vòng ${data.round} / 10`;
        if(resultDisplay) resultDisplay.classList.add('hidden');
        enableChoiceButtons(true, null);
        if(checkpointControls) checkpointControls.classList.add('hidden');
    });

    socket.on('forbidden_timer', (data) => {
        if(timerDisplay) timerDisplay.innerHTML = `${data.time}s`;
    });

    socket.on('forbidden_round_result', (data) => {
        if(timerDisplay) timerDisplay.innerHTML = "Hết giờ!";
        const forbiddenIcon = {'rock': '✊', 'paper': '✋', 'scissor': '✌️'};
        if(bannedCardSpan) bannedCardSpan.innerHTML = forbiddenIcon[data.banned_card];
        if(resultDisplay) resultDisplay.classList.remove('hidden');

        if (data.losers.length > 0) {
            statusDisplay.innerHTML = `Lá cấm là ${forbiddenIcon[data.banned_card]}. Loại: ${data.losers.join(', ')}`;
        } else {
            statusDisplay.innerHTML = `Lá cấm là ${forbiddenIcon[data.banned_card]}. Tất cả đều sống sót!`;
        }
        updatePlayerList(data.players_data);
        enableChoiceButtons(false, null);
    });

    socket.on('forbidden_checkpoint', (data) => {
        if(checkpointControls) checkpointControls.classList.remove('hidden');
    });

    socket.on('forbidden_game_over', (data) => {
        statusDisplay.innerHTML = data.message;
        if(timerDisplay) timerDisplay.innerHTML = "GAME OVER";
        if(resultDisplay) resultDisplay.classList.add('hidden');
        if(checkpointControls) checkpointControls.classList.add('hidden');
        // Game kết thúc, hiện lại nút Bắt đầu cho ván mới
        if (startBtn) startBtn.classList.remove('hidden');
    });

    socket.on('currency_update', function(data) {
        const currencyDisplay = document.getElementById('user-currency-display');
        if (currencyDisplay && data.winner_username === username) {
            currencyDisplay.innerHTML = `<i class="fas fa-coins"></i> ${data.new_currency}v`;
        }
        if (data.winner_username === username && data.amount > 0) {
            // Sửa lại: Dùng addChatMessage thay vì alert
            addChatMessage(null, `🎉 CHÚC MỪNG! Bạn đã nhận được ${data.amount} xu!`, true);
        }
    });

    //
    // --- LOGIC CHAT (ĐÃ DÁN ĐÚNG VỊ TRÍ) ---
    //
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
        // Ghi đè: Dùng addChatMessage thay vì alert
        addChatMessage(null, data.message, true);
    });
    // --- KẾT THÚC LOGIC CHAT ---

}); // <-- Chỉ có MỘT dấu đóng '});' ở cuối file