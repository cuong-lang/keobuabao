// static/socketio.js
document.addEventListener('DOMContentLoaded', () => {

    // --- BIẾN TOÀN CỤC ---
    let roomid;
    let am_spectator = false;
    let selectedRoomId = null;

    const pathParts = window.location.pathname.split('/');
    if (pathParts[1] === 'game' && pathParts[2]) {
        roomid = pathParts[2];
    }

    // THÊM: Kiểm tra nếu đang ở trang chơi đơn
    const isSinglePlayerPage = window.location.pathname.endsWith('/single_player_page');

    // Hàm cho chế độ chơi đơn
    const CHOICES = ['rock', 'paper', 'scissor'];

    // Định nghĩa hàm randomChoice cho JavaScript
    function randomChoice(arr) {
        return arr[Math.floor(Math.random() * arr.length)];
    }

    function getWinner(p1, p2) {
        if (p1 === p2) return "HÒA";
        if (
            (p1 === 'rock' && p2 === 'scissor') ||
            (p1 === 'scissor' && p2 === 'paper') ||
            (p1 === 'paper' && p2 === 'rock')
        ) return "THẮNG";
        return "THUA";
    }

    // --- KHỞI TẠO SOCKET ---
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);


    // --- LOGIC CHO TRANG LOBBY ---
    const createRoomForm = document.getElementById('create-room-form');
    const quickMatchBtn = document.getElementById('quick_match_btn');

    // BIẾN CHO THIẾT KẾ DANH SÁCH PHÒNG MỚI
    const pvpWaitingRoomsUl = document.getElementById('pvp-waiting-rooms');
    const joinRoomFormNew = document.getElementById('join-room-form-new');
    const selectedRoomIdInput = document.getElementById('selected-room-id');
    const joinPasswordInputNew = document.getElementById('join_password_new');
    const joinRoomBtnNew = document.getElementById('join_room_btn_new');
    const spectateRoomBtnNew = document.getElementById('spectate_room_btn_new');

    const createPasswordInput = document.getElementById('create_password');
    const createRoomIdCustomInput = document.getElementById('create_room_id_custom');

    // YÊU CẦU SERVER GỬI DANH SÁCH PHÒNG KHI VÀO LOBBY
    if (pvpWaitingRoomsUl) {
        socket.emit('get_waiting_pvp_rooms');
    }

    if (createRoomForm) {
        createRoomForm.onsubmit = (e) => {
            e.preventDefault();
            const customCode = createRoomIdCustomInput.value;
            if (!customCode || customCode.trim() === "") {
                alert("Vui lòng tự nhập mã phòng!");
                return;
            }
            createRoomForm.disabled = true;
            socket.emit('create_room', {
                "username": username,
                "password": createPasswordInput.value,
                "game_mode": "pvp",
                "room_id_custom": customCode
            });
        };
    }

    if (quickMatchBtn) {
        quickMatchBtn.onclick = () => {
            if (typeof username !== 'undefined' && username) {
                socket.emit('quick_match', {"username": username});
            } else {
                alert("Lỗi: Không tìm thấy tên người dùng. Đang chuyển về Lobby...");
            }
        };
    }

    // --- LOGIC THAM GIA / XEM PHÒNG (Từ danh sách) ---

    // Xử lý khi người dùng chọn một phòng từ danh sách
    function handleRoomSelection(roomID, player1Name, hasPassword) {
        selectedRoomId = roomID;
        selectedRoomIdInput.value = roomID;

        // Ẩn/Hiện ô mật khẩu dựa trên việc phòng có mật khẩu hay không
        if (hasPassword) {
            joinPasswordInputNew.classList.remove('hidden');
            joinPasswordInputNew.placeholder = "Nhập Mật khẩu phòng";
        } else {
            joinPasswordInputNew.classList.add('hidden');
            joinPasswordInputNew.value = ""; // Xóa mật khẩu cũ
        }

        // Bật các nút Join/Spectate
        joinRoomBtnNew.disabled = false;
        spectateRoomBtnNew.disabled = false;

        // Đảm bảo chỉ 1 phòng được highlight
        document.querySelectorAll('#pvp-waiting-rooms li').forEach(li => {
            li.classList.remove('active');
            li.classList.remove('list-group-item-info');
        });
        document.getElementById(`li-${roomID}`).classList.add('active');
        document.getElementById(`li-${roomID}`).classList.add('list-group-item-info');
    }


    if (joinRoomFormNew) {
        joinRoomFormNew.onsubmit = (e) => {
            e.preventDefault();
            if (selectedRoomId) {
                socket.emit('join_room', {
                    "username": username,
                    'room_id': selectedRoomId,
                    "password": joinPasswordInputNew.value // Dùng mật khẩu từ form mới
                });
            } else {
                 alert("Vui lòng chọn phòng trước!");
            }
        };
    }

    if (spectateRoomBtnNew) {
        spectateRoomBtnNew.onclick = (e) => {
            e.preventDefault();
            if (selectedRoomId) {
                // Spectate sử dụng logic join_room, server sẽ quyết định là player hay spectator
                socket.emit('join_room', {
                    'room_id': selectedRoomId,
                    "password": joinPasswordInputNew.value
                });
            } else {
                 alert("Vui lòng chọn phòng trước!");
            }
        };
    }

    // --- LOGIC CHO TRANG GAME ---
    const messageDiv = document.getElementById('message');
    const gameStatusH2 = document.getElementById('game-status');
    const predictionMessage = document.getElementById('prediction-display');
    const player1NameH4 = document.getElementById('player1_name_display');
    const player2NameH4 = document.getElementById('player2_name_display');
    const player1ScoreSpan = document.getElementById('player1_score');
    const player2ScoreSpan = document.getElementById('player2_score');
    const leaveRoomBtn = document.getElementById('leave_room_btn');
    const rockBtn = document.getElementById('rock');
    const paperBtn = document.getElementById('paper');
    const scissorBtn = document.getElementById('scissor');
    const gameControlsDiv = document.getElementById('game-controls');

    // Nếu đang ở trang game, tự động tham gia (hoặc rejoin)
    if (roomid && typeof username !== 'undefined' && username) {
        console.log(`Đang ở trang game, gửi check-in cho phòng ${roomid}`);
        socket.emit('player_joined_game_page', {
            'room_id': roomid,
            'username': username
        });
    } else if (roomid) {
        console.log("Đang ở trang game nhưng không tìm thấy username!");
        alert("Lỗi: Không tìm thấy tên người dùng. Đang chuyển về Lobby...");
        window.location.href = '/lobby/';
    }

    // THÊM: Logic cho trang chơi đơn (nếu có)
    if (isSinglePlayerPage) {
        // Gửi yêu cầu lấy gợi ý AI ngay khi load trang
        socket.emit('ai_game_request', {});
    }

    // --- HÀM XỬ LÝ CHỌN KÉO BÚA BAO (ĐÃ SỬA) ---
    function makeChoice(choice) {
        if (am_spectator) {
            alert("Bạn là người xem, không thể chơi!");
            return;
        }

        // --- LOGIC CHƠI ĐƠN (Single Player) ---
        if (isSinglePlayerPage) {

            const botChoice = randomChoice(CHOICES);
            const result = getWinner(choice, botChoice);

            // TODO: Cập nhật score hiển thị ở đây

            if (messageDiv) messageDiv.innerHTML = `Bot chọn **${botChoice}**. Kết quả: **${result}**!`;

            // Vô hiệu hóa nút tạm thời
            if (rockBtn) rockBtn.disabled = true;
            if (paperBtn) paperBtn.disabled = true;
            if (scissorBtn) scissorBtn.disabled = true;

            // Yêu cầu AI gợi ý cho lượt sau
            socket.emit('ai_game_request', {});

            // Cho phép chọn lại sau 1s
            setTimeout(() => {
                if (rockBtn) rockBtn.disabled = false;
                if (paperBtn) paperBtn.disabled = false;
                if (scissorBtn) scissorBtn.disabled = false;
            }, 1000);
            return;
        }
        // --- KẾT THÚC LOGIC CHƠI ĐƠN ---

        console.log(`Gửi lựa chọn: ${choice} lên phòng ${roomid}`);
        socket.emit('player_choice', {
            'choice': choice, 'room_id': roomid
        });

        // Vô hiệu hóa các nút để tránh bấm nhiều lần
        if (rockBtn) rockBtn.disabled = true;
        if (paperBtn) paperBtn.disabled = true;
        if (scissorBtn) scissorBtn.disabled = true;

        // Cập nhật thông báo tạm thời cho người chơi vừa chọn
        if (messageDiv) messageDiv.innerHTML = `Bạn đã chọn ${choice}. Đang chờ đối thủ...`;
    }

    if (rockBtn) rockBtn.onclick = () => makeChoice('rock');
    if (paperBtn) paperBtn.onclick = () => makeChoice('paper');
    if (scissorBtn) scissorBtn.onclick = () => makeChoice('scissor');

    if (leaveRoomBtn) leaveRoomBtn.onclick = () => {
        socket.emit('leave_room', {'room_id': roomid});
        window.location.href = '/lobby/';
    };

    // --- LOGIC CHAT ---
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
            if (message.trim() !== "") {
                if (!roomid) { roomid = 'lobby_chat'; }
                socket.emit('send_message', {'room_id': roomid, 'message': message, 'username': username});
                chatInput.value = "";
            }
        };
    }

    // --- LẮNG NGHE SỰ KIỆN TỪ SERVER ---

    // === SỰ KIỆN NHẬN DANH SÁCH PHÒNG CHỜ ===
    socket.on('pvp_waiting_rooms', data => {
        if (pvpWaitingRoomsUl) {
            pvpWaitingRoomsUl.innerHTML = ''; // Xóa thông báo 'Đang tải...'

            // Vô hiệu hóa nút mặc định nếu không có phòng
            joinRoomBtnNew.disabled = true;
            spectateRoomBtnNew.disabled = true;
            joinPasswordInputNew.classList.add('hidden');
            selectedRoomId = null;

            if (data.rooms && data.rooms.length > 0) {
                data.rooms.forEach(room => {
                    const li = document.createElement('li');
                    li.className = 'list-group-item d-flex justify-content-between align-items-center bg-dark text-white-75';
                    li.id = `li-${room.room_id}`;
                    li.style.cursor = 'pointer'; // Thêm con trỏ để nhấn
                    li.innerHTML = `
                        <div style="flex-grow: 1;">
                            <strong>${room.room_id}</strong> - <small>Người tạo: ${room.player1_name}</small>
                        </div>
                        <span class="badge badge-primary badge-pill" style="font-size: 0.9em;">
                            ${room.has_password ? '<i class="fas fa-lock" style="color: #ff9900;"></i> Có Mật khẩu' : 'Mở'}
                        </span>
                    `;
                    li.onclick = () => handleRoomSelection(room.room_id, room.player1_name, room.has_password);
                    pvpWaitingRoomsUl.appendChild(li);
                });
            } else {
                 const li = document.createElement('li');
                 li.className = 'list-group-item d-flex justify-content-between align-items-center bg-dark text-white-50';
                 li.innerHTML = 'Không có phòng nào đang chờ...';
                 pvpWaitingRoomsUl.appendChild(li);
            }
        }
    });

    // Xử lý chuyển hướng cho tất cả các game
    socket.on('room_joined', (data) => {
        if (data.game_mode === 'pvp') {
            window.location.href = "/game/" + data.room_id;

        // === SỬA LỖI CHUYỂN HƯỚNG BAUCUA ===
        // Phải chuyển hướng đến phòng cụ thể, không phải sảnh chung
        } else if (data.game_mode === 'baucua') {
            window.location.href = "/game_baucua/" + data.room_id;
        // === KẾT THÚC SỬA LỖI ===

        } else if (data.game_mode === 'forbidden') {
            window.location.href = "/game_forbidden/";
        }
    });

    socket.on('join_error', data => {
        alert(data['error']);
        // Gửi yêu cầu cập nhật lại danh sách phòng sau khi có lỗi (chỉ nếu đang ở lobby)
        if (pvpWaitingRoomsUl) {
            socket.emit('get_waiting_pvp_rooms');
            if (createRoomForm) createRoomForm.disabled = false;
        } else if (roomid) {
            console.error('Check-in thất bại, chuyển về sảnh:', data.error);
            window.location.href = '/lobby/';
        }
    });


    // === CÁC SỰ KIỆN CHỈ CHẠY Ở TRANG GAME ===

    socket.on('spectator_update', data => {
        if (player1NameH4) player1NameH4.innerHTML = data.user1;
        if (player2NameH4) player2NameH4.innerHTML = data.user2 ? data.user2 : "...";
        if (gameStatusH2) gameStatusH2.innerHTML = data.message;
        if (player1ScoreSpan) player1ScoreSpan.innerHTML = data.score1;
        if (player2ScoreSpan) player2ScoreSpan.innerHTML = data.score2;

        const isPlayer1 = username === data.user1;
        const isPlayer2 = username === data.user2;
        const isFull = data.user2 && data.user2 !== "..." && data.user2 !== "Đang chờ...";

        // 1. Kiểm tra Spectator
        if (!isPlayer1 && !isPlayer2) {
            am_spectator = true;
            if(gameControlsDiv) gameControlsDiv.style.display = 'none'; // Ẩn nút nếu là người xem
        } else {
            am_spectator = false;
            // 2. Kích hoạt nút nếu là Player VÀ phòng đã đầy
            if(gameControlsDiv) {
                if (isFull) {
                    gameControlsDiv.style.display = 'block';
                } else {
                    // Ẩn nút nếu là P1 đang chờ P2
                    gameControlsDiv.style.display = 'none';
                    if (messageDiv) messageDiv.innerHTML = "Đang chờ đối thủ...";
                }
            }
        }
    });

    socket.on('wait', data =>{
        // Thông báo chờ chỉ gửi cho người chưa chọn
        if (messageDiv) messageDiv.innerHTML = `Đối thủ ${data.person_waiting} đã chọn. Vui lòng chọn của bạn.`;

        // Mở khóa nút cho người chưa chọn
        if (rockBtn) rockBtn.disabled = false;
        if (paperBtn) paperBtn.disabled = false;
        if (scissorBtn) scissorBtn.disabled = false;
    });

    socket.on('leave', data => {
        addChatMessage(null, data['message'], true);
        alert(data['message']);
        window.location.href = '/lobby/';
    });

    // --- SỬA LẠI HIỂN THỊ KẾT QUẢ RÕ RÀNG HƠN ---
    socket.on('round_result', data => {
        // Hiển thị thông báo kết quả to và rõ
        if (messageDiv) {
            messageDiv.innerHTML = `<h3 style="color: #ffcc00; text-transform: uppercase;">${data.message}</h3>`;
        }

        if (player1ScoreSpan) player1ScoreSpan.innerHTML = data.score1;
        if (player2ScoreSpan) player2ScoreSpan.innerHTML = data.score2;

        // Mở khóa nút để chơi ván tiếp theo
        if (rockBtn) rockBtn.disabled = false;
        if (paperBtn) paperBtn.disabled = false;
        if (scissorBtn) scissorBtn.disabled = false;
    });

    // === XÓA BỎ SỰ KIỆN 'dice_result' TRÙNG LẶP ===
    // Sự kiện này đã được xử lý chính xác trong `baucua.js`.
    // Việc để nó ở đây (trong `socketio.js`) sẽ gây lỗi khi ở sảnh hoặc phòng PvP.

    socket.on('ai_suggestion', data => {
        if (predictionMessage) {
            predictionMessage.innerHTML = `🤖 AI Gợi Ý (cho lượt sau): Bạn nên chơi <strong>${data.suggestion}</strong>.`;
        }
    });

    socket.on('receive_message', function(data) {
        addChatMessage(data.username, data.message);
    });

    socket.on('system_message', function(data) {
        // Lọc thông báo system_message trước khi hiển thị trong chat box
        if (!data.message.includes("Bạn đã chọn")) {
            addChatMessage(null, data.message, true);
        }

        // Kích hoạt nút chơi khi đủ người
        if (gameStatusH2 && data.message.includes("Bắt đầu chơi!") && !am_spectator) {
             gameStatusH2.innerHTML = "Trận đấu đang diễn ra!";
             if(gameControlsDiv) gameControlsDiv.style.display = 'block';
        }
        // Hiển thị thông báo đang chờ sau khi chọn (chỉ trong messageDiv)
        if (data.message.includes("Bạn đã chọn")) {
             if (messageDiv) messageDiv.innerHTML = data.message;
        }
    });

    // --- SỬA LẠI THÔNG BÁO TIỀN THƯỞNG "ĐÀNG HOÀNG" ---
    socket.on('currency_update', function(data) {
        const currencyDisplay = document.getElementById('user-currency-display');

        // Kiểm tra xem mình có phải là người thắng không
        if (data.winner_username === username) {
            // 1. Cập nhật số tiền trên góc màn hình
            if (currencyDisplay) {
                currencyDisplay.innerHTML = `<i class="fas fa-coins"></i> ${data.new_currency}v`;
                // Tạo hiệu ứng nhấp nháy màu vàng cho tiền
                currencyDisplay.style.color = "yellow";
                setTimeout(() => { currencyDisplay.style.color = ""; }, 2000);
            }

            // 2. BẬT THÔNG BÁO CHÚC MỪNG (Popup)
            if (data.amount > 0) {
                 alert(`🎉 CHÚC MỪNG CHIẾN THẮNG! 🎉\n\n+${data.amount} Xu đã được cộng vào tài khoản.`);
            } else if (data.amount < 0) {
                 // Dùng cho Bầu Cua/Tử Cấm
                 addChatMessage(null, `Bạn đã đặt cược ${-data.amount}v.`, true);
            }
        }
    });

});