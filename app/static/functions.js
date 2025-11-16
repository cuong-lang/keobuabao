// static/functions.js (Đã sửa để dùng Socket.IO)

// --- CÁC BIẾN SỐ (Giữ nguyên) ---
let userScore = 0;
let compScore = 0;
const userScore_span = document.getElementById("user-score");
const compScore_span = document.getElementById("comp-score");
const resultMessage = document.getElementById("resultMessage");
const rock_div = document.getElementById("r");
const paper_div = document.getElementById("p");
const scissor_div = document.getElementById("s");
const predictionMessage = document.getElementById("prediction-display");
const restartButton = document.getElementById("restart-button");

// === SỬA LỖI: CHUYỂN SANG LOGIC SOCKET.IO ===

// 1. Kết nối tới Socket.IO (biến 'io' có từ thư viện đã tải trong single.html)
var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

socket.on('connect', () => {
    console.log("Socket.IO connected for Single Player.");
    // Yêu cầu gợi ý AI đầu tiên
    predictionMessage.innerHTML = "🤖 AI Gợi Ý: Đang tải...";
    // Gửi sự kiện mà events.py đang lắng nghe
    socket.emit('ai_game_request', {});
});

socket.on('disconnect', () => {
    // Hiển thị lỗi nếu mất kết nối
    predictionMessage.innerHTML = "Lỗi kết nối AI. Vui lòng F5.";
});

// 2. Lắng nghe sự kiện 'ai_suggestion' từ server (events.py)
socket.on('ai_suggestion', (data) => {
    if (predictionMessage) {
        // Hiển thị gợi ý cho LƯỢT TIẾP THEO
        const suggestionMap = {'rock': 'Kéo', 'paper': 'Búa', 'scissor': 'Bao'};
        const suggestionText = suggestionMap[data.suggestion] || data.suggestion;
        predictionMessage.innerHTML = `🤖 AI Gợi Ý (cho lượt sau): Bạn nên chơi <strong>${suggestionText}</strong>.`;
    }
});

// --- CÁC HÀM CẬP NHẬT GIAO DIỆN (Giữ nguyên) ---

function removeGlows() {
    rock_div.classList.remove('win-glow', 'lose-glow', 'tie-glow');
    paper_div.classList.remove('win-glow', 'lose-glow', 'tie-glow');
    scissor_div.classList.remove('win-glow', 'lose-glow', 'tie-glow');
}

function updateScores(userScore, compScore) {
  userScore_span.innerHTML = userScore;
  compScore_span.innerHTML = compScore;
}

function win(userChoice, compChoice) {
  userScore++;
  resultMessage.innerHTML = `[THẮNG] ${userChoice} của bạn thắng ${compChoice} của Bot!`;
  removeGlows();
  document.getElementById(userChoice === 'rock' ? 'r' : (userChoice === 'paper' ? 'p' : 's')).classList.add('win-glow');
}

function lost(userChoice, compChoice) {
  compScore++;
  resultMessage.innerHTML = `[THUA] ${userChoice} của bạn thua ${compChoice} của Bot.`;
  removeGlows();
  document.getElementById(userChoice === 'rock' ? 'r' : (userChoice === 'paper' ? 'p' : 's')).classList.add('lose-glow');
}

function tie(userChoice) {
  resultMessage.innerHTML = `[HÒA] Cả hai đều ra ${userChoice}.`;
  removeGlows();
  document.getElementById(userChoice === 'rock' ? 'r' : (userChoice === 'paper' ? 'p' : 's')).classList.add('tie-glow');
}

// Hàm này lấy từ file socketio.js của bạn để tính kết quả
function getWinner(p1, p2) {
    if (p1 === p2) return "tie";
    if (
        (p1 === 'rock' && p2 === 'scissor') ||
        (p1 === 'scissor' && p2 === 'paper') ||
        (p1 === 'paper' && p2 === 'rock')
    ) return "player_win";
    return "ai_win";
}


// --- LOGIC GAME CHÍNH (SỬA LẠI, KHÔNG DÙNG FETCH) ---

function game(userChoice) {
  // 1. Bot chọn ngẫu nhiên (Vì tên game là "vs. Bot Ngẫu Nhiên")
  const botChoice = ['rock', 'paper', 'scissor'][Math.floor(Math.random() * 3)];

  // 2. Tính kết quả
  const result = getWinner(userChoice, botChoice);
  const choiceMap = {'rock': 'Kéo', 'paper': 'Búa', 'scissor': 'Bao'};

  // 3. Xử lý kết quả (Thắng/Thua/Hòa)
  if (result === 'player_win') {
    win(choiceMap[userChoice], choiceMap[botChoice]);
  } else if (result === 'ai_win') {
    lost(choiceMap[userChoice], choiceMap[botChoice]);
  } else {
    tie(choiceMap[userChoice]);
  }

  // 4. Cập nhật bảng điểm
  updateScores(userScore, compScore);

  // 5. YÊU CẦU GỢI Ý MỚI TỪ AI cho lượt sau
  if (predictionMessage) {
      predictionMessage.innerHTML = "🤖 AI Gợi Ý: Đang tải...";
      socket.emit('ai_game_request', {}); // Gửi sự kiện 'ai_game_request'
  }
}

// 3. Sửa hàm Chơi Lại để dùng Socket
function restartGame() {
    userScore = 0;
    compScore = 0;
    updateScores(userScore, compScore);
    resultMessage.innerHTML = "Đã chơi lại! Hãy chọn nước đi!";
    if (predictionMessage) {
        predictionMessage.innerHTML = "🤖 AI Gợi Ý: Đang tải...";
        // Yêu cầu gợi ý AI mới
        socket.emit('ai_game_request', {});
    }
    removeGlows();
}


// --- BỘ LẮNG NGHE SỰ KIỆN (Giữ nguyên) ---
function main() {
  rock_div.addEventListener('click', () => game("rock"));
  paper_div.addEventListener('click', () => game("paper"));
  scissor_div.addEventListener('click', () => game("scissor"));

  if (restartButton) {
      restartButton.addEventListener('click', restartGame);
  }
}

main(); // Chạy hàm main để kích hoạt các nút