import eventlet
import random
import html
from flask import session, request
from flask_socketio import emit, join_room, leave_room, disconnect
from .extensions import socketio
from .database import users
from .utils import create_random_string, create_deck

# === CẤU HÌNH TRUNG TÂM ===
rooms = {}  # PvP
baucua_rooms = {}  # Bầu Cua
forbidden_rooms = {}  # Tử Cấm
card_game_rooms = {}  # Game Thẻ
quick_match_queue = []  # Hàng đợi PvP

GAME_MODES_CONFIG = {
    'pvp': {'prefix': 'PVP-', 'dict': rooms},
    'baucua': {'prefix': 'BC-', 'dict': baucua_rooms},
    'forbidden': {'prefix': 'FB-', 'dict': forbidden_rooms}
}
CHOICES = ['rock', 'paper', 'scissor']
BAUCUA_TIMER = 15  # Thêm hằng số thời gian Bầu Cua


# === CÁC HÀM TRỢ GIÚP ===
def get_winner(p1_choice, p2_choice):
    if p1_choice == p2_choice: return "tie"
    if (p1_choice == 'rock' and p2_choice == 'scissor') or \
            (p1_choice == 'scissor' and p2_choice == 'paper') or \
            (p1_choice == 'paper' and p2_choice == 'rock'):
        return "player1_win"
    return "player2_win"


# === HÀM MỚI: Hỗ trợ cho Game Thẻ Bài ===
def get_card_winner(p1_choice, p2_choice):
    # (p1_choice và p2_choice là 'Kéo', 'Búa', 'Bao')
    if p1_choice == p2_choice: return "tie"
    if (p1_choice == 'Búa' and p2_choice == 'Kéo') or \
            (p1_choice == 'Kéo' and p2_choice == 'Bao') or \
            (p1_choice == 'Bao' and p2_choice == 'Búa'):
        return "p1_win"
    return "p2_win"


# === KẾT THÚC HÀM MỚI ===

def get_ai_suggestion(room_id, player_sid): return random.choice(CHOICES)


#
# === SỬA LỖI 2: CONTEXT ===
#

# HÀM MỚI: Chỉ cập nhật DB, an toàn cho tác vụ nền (game loop)
def update_currency_db_only(username, amount):
    if not username: return 0
    # Cập nhật database
    users.update_one({"username": username}, {"$inc": {"currency": amount}}, upsert=True)

    # Lấy giá trị tiền mới từ database
    user_doc = users.find_one({"username": username}, {"currency": 1})
    if user_doc:
        return user_doc.get("currency", 1000)
    return 1000  # Tiền mặc định


# HÀM CŨ (ĐÃ SỬA): Dùng cho các sự kiện (có context), cập nhật cả DB và Session
def update_currency(username, amount):
    if not username: return

    # Gọi hàm DB an toàn để thực hiện cập nhật
    new_currency = update_currency_db_only(username, amount)

    # Cập nhật session (An toàn vì hàm này chỉ được gọi từ event handler)
    try:
        if session.get("username") == username:
            session["currency"] = new_currency
            session.modified = True
    except Exception as e:
        print(f"WARN: Không thể cập nhật session cho {username}: {e}")

    return new_currency


# === KẾT THÚC SỬA LỖI 2 ===
#

def get_players_in_room(room_data):
    if not room_data or 'players' not in room_data: return []
    return [p['username'] for p in room_data['players'].values()]


def find_room(room_id):
    if not room_id: return None, None
    if room_id in rooms: return rooms[room_id], 'pvp'
    if room_id in baucua_rooms: return baucua_rooms[room_id], 'baucua'
    if room_id in forbidden_rooms: return forbidden_rooms[room_id], 'forbidden'

    # === SỬA LOGIC: Thêm game_card_rooms vào tìm kiếm ===
    if room_id in card_game_rooms: return card_game_rooms[room_id], 'cardgame'

    # Kiểm tra nếu người dùng nhập thiếu prefix
    pvp_id = GAME_MODES_CONFIG['pvp']['prefix'] + room_id
    if pvp_id in rooms: return rooms[pvp_id], 'pvp'
    bc_id = GAME_MODES_CONFIG['baucua']['prefix'] + room_id
    if bc_id in baucua_rooms: return baucua_rooms[bc_id], 'baucua'
    fb_id = GAME_MODES_CONFIG['forbidden']['prefix'] + room_id
    if fb_id in forbidden_rooms: return forbidden_rooms[fb_id], 'forbidden'
    return None, None


def find_room_by_sid(sid):
    for room_id, room in rooms.items():
        p1 = room.get('player1')
        p2 = room.get('player2')
        p1_sid = p1['sid'] if p1 else None
        p2_sid = p2['sid'] if p2 else None

        if (p1_sid and p1_sid == sid) or \
                (p2_sid and p2_sid == sid) or \
                (sid in room.get('spectators', [])):
            return room_id, room, 'pvp'

    for room_id, room in baucua_rooms.items():
        if sid in room.get('players', {}): return room_id, room, 'baucua'
    for room_id, room in forbidden_rooms.items():
        if sid in room.get('players', {}): return room_id, room, 'forbidden'

    # === SỬA LOGIC: Thêm tìm kiếm game thẻ bài bằng SID ===
    for room_id, room in card_game_rooms.items():
        for player in room.get('players', []):
            if player.get('sid') == sid:
                return room_id, room, 'cardgame'
    # === KẾT THÚC SỬA LOGIC ===

    return None, None, None


#
# === SỬA LỖI 1: CRASH KHI XÓA PHÒNG ===
#
def check_and_delete_room(room_id, game_mode):
    """
    Chờ 5 giây, sau đó kiểm tra xem phòng có còn trống không.
    Nếu vẫn trống thì mới xóa.
    """
    print(f"LOG: Bắt đầu 5 giây ân hạn cho phòng {game_mode} {room_id}...")
    eventlet.sleep(5)  # Chờ 5 giây

    room_dict = None
    if game_mode == 'baucua':
        room_dict = baucua_rooms
    elif game_mode == 'forbidden':
        room_dict = forbidden_rooms
    else:
        return  # Không xử lý cho PvP

    if room_id in room_dict:
        room = room_dict[room_id]
        # Kiểm tra lại sau 5 giây
        if not room.get('players'):
            print(f"LOG: Hết 5 giây. Phòng {room_id} vẫn trống. Đang xóa.")

            # SỬA LỖI: Không dùng .kill()
            # Vòng lặp game (baucua_game_loop) sẽ tự kiểm tra 'while room_id in baucua_rooms'
            # và tự thoát ra một cách an toàn khi chúng ta 'del' phòng.
            if room.get('game_loop_task'):
                # Đánh dấu là không cần chạy nữa, nhưng không cần kill
                room['game_loop_task'] = None

            del room_dict[room_id]
            print(f"LOG: Đã xóa phòng {room_id}.")
        else:
            print(f"LOG: Người chơi đã kết nối lại vào {room_id}. Phòng được giữ lại.")
    else:
        print(f"LOG: Phòng {room_id} đã bị xóa (có thể do lỗi khác).")


# === KẾT THÚC SỬA LỖI 1 ===


def baucua_game_loop(room_id):
    print(f"LOG: Bắt đầu vòng lặp Bầu Cua cho phòng {room_id}")

    # Vòng lặp chính phải nằm ở đây để game chạy liên tục
    while room_id in baucua_rooms:
        try:
            # Lấy thông tin phòng ở mỗi vòng lặp
            room = baucua_rooms.get(room_id)
            if not room:  # Phòng đã bị xóa, thoát ngay
                print(f"LOG: Phòng {room_id} không còn, dừng vòng lặp.")
                return

                # 1. GIAI ĐOẠN ĐẶT CƯỢC
            room['state'] = 'betting'
            for t in range(BAUCUA_TIMER, 0, -1):
                socketio.emit('baucua_state_update', {
                    'state': 'betting',
                    'time_left': t,
                    'players': get_players_in_room(room)
                }, to=room_id)
                eventlet.sleep(1)
                # THÊM: Kiểm tra an toàn để thoát vòng lặp nhỏ (quan trọng)
                if room_id not in baucua_rooms:
                    print(f"LOG: Phòng {room_id} bị xóa trong lúc đếm ngược, dừng.")
                    return

            # 2. GIAI ĐOẠN QUAY
            room['state'] = 'rolling'
            socketio.emit('baucua_state_update', {
                'state': 'rolling',
                'players': get_players_in_room(room)
            }, to=room_id)
            eventlet.sleep(2)  # Chờ 2 giây để client hiển thị animation "Đang quay..."

            # 3. TÍNH KẾT QUẢ
            die1 = random.choice(['rock', 'paper', 'scissor'])
            die2 = random.choice(['rock', 'paper', 'scissor'])

            # Đã sửa: Sắp xếp kết quả xúc xắc để khớp với các loại cược không có thứ tự
            dice_results = sorted([die1, die2])

            winning_bets = []

            # Tổ hợp 1: rock-rock (Kéo-Kéo)
            if dice_results == ['rock', 'rock']: winning_bets.append('rockrock')
            # Tổ hợp 2: paper-paper (Búa-Búa)
            if dice_results == ['paper', 'paper']: winning_bets.append('paperpaper')
            # Tổ hợp 3: scissor-scissor (Bao-Bao)
            if dice_results == ['scissor', 'scissor']: winning_bets.append('scissorscissor')

            # Tổ hợp 4: rock-paper (Kéo-Búa)
            if dice_results == ['paper', 'rock']: winning_bets.append('paperrock')
            # Tổ hợp 5: rock-scissor (Kéo-Bao)
            if dice_results == ['rock', 'scissor']: winning_bets.append('rockscissor')
            # Tổ hợp 6: paper-scissor (Búa-Bao)
            if dice_results == ['paper', 'scissor']: winning_bets.append('paperscissor')

            winners = []
            bets = dict(room.get('bets', {}))

            # Lấy danh sách người chơi hiện tại TRƯỚC khi lặp
            # (Phải dùng .items() để tránh lỗi 'dictionary changed size during iteration')
            current_players_copy = dict(room.get('players', {}))

            for user, user_bets in bets.items():
                winnings = 0
                total_bet = sum(user_bets.values())

                # Tính toán tổng tiền thắng
                for bet_type, amount in user_bets.items():
                    multiplier = 0
                    if bet_type in winning_bets:
                        # Mọi cược thắng đều là x3 (dựa trên hình ảnh)
                        multiplier = 3

                    if multiplier > 0:
                        # Tiền thắng cược (bao gồm tiền cược gốc)
                        winnings += amount * multiplier

                net_change_to_add = winnings  # Đây là tiền trả thưởng

                # CẬP NHẬT TÀI KHOẢN
                if net_change_to_add > 0:
                    # === SỬA LỖI 2: Dùng hàm _db_only ===
                    new_currency = update_currency_db_only(user, net_change_to_add)
                else:
                    new_currency = update_currency_db_only(user, 0)  # Lấy số dư mới nhất

                net_profit_or_loss = net_change_to_add - total_bet

                if net_profit_or_loss > 0:
                    winners.append(f"{user} (+{net_profit_or_loss})")

                # Gửi cập nhật tiền tệ (cho cả người thắng và người thua)
                for pid, pdata in current_players_copy.items():
                    if pdata and pdata.get('username') == user:
                        # Gửi cập nhật tiền
                        socketio.emit('currency_update',
                                      {'winner_username': user if net_profit_or_loss > 0 else None,
                                       'amount': net_profit_or_loss,  # Gửi tiền LÃI/LỖ RÒNG
                                       'new_currency': new_currency},
                                      to=pid)
                        break

            # Gửi kết quả xúc xắc (die1 và die2) đến client
            socketio.emit('dice_result', {
                'die1': die1,  # rock/paper/scissor
                'die2': die2,  # rock/paper/scissor
                'winners': winners  # [user (+winnings)]
            }, to=room_id)

            # 4. Bắt đầu vòng mới
            room['bets'] = {}
            socketio.emit('update_bets', {'bets': {}}, to=room_id)

            eventlet.sleep(5)  # Nghỉ 5s xem kết quả, sau đó quay lại vòng đặt cược

        except Exception as e:
            # In lỗi để xác định nguyên nhân treo
            print(f"LỖI NGHIÊM TRỌNG TRONG GAME LOOP ({room_id}): {e}")
            eventlet.sleep(5)
            if room_id not in baucua_rooms:
                print("Phòng không còn, dừng hẳn vòng lặp.")
                return


def forbidden_game_loop(room_id):
    print(f"LOG: Bắt đầu vòng lặp Tử Cấm cho phòng {room_id}")

    while room_id in forbidden_rooms:
        try:
            room = forbidden_rooms.get(room_id)
            if not room:
                print(f"LOG: Phòng {room_id} không còn, dừng vòng lặp.")
                return

            # 1. KIỂM TRA SỐ NGƯỜI CHƠI
            if not room.get('players'):
                room['state'] = 'waiting'
                socketio.emit('forbidden_state_update', {
                    'state': 'waiting', 'message': 'Đang chờ người chơi...',
                    'players_data': room.get('players', {})
                }, to=room_id)
                eventlet.sleep(5)
                continue

                # 2. BẮT ĐẦU GAME (RESET VÒNG CHƠI)
            room['state'] = 'playing'
            for p in room['players'].values():
                p['status'] = 'playing'
                p['wins'] = 0
                p['choice'] = None

            socketio.emit('forbidden_state_update', {
                'state': 'playing', 'message': 'Game bắt đầu! Sống sót qua 10 vòng.',
                'players_data': room['players']
            }, to=room_id)
            eventlet.sleep(3)

            # 3. CHẠY 10 VÒNG
            game_over = False
            for round_num in range(1, 11):
                if room_id not in forbidden_rooms:
                    print(f"LOG: Phòng {room_id} bị xóa, dừng vòng lặp 10 vòng.")
                    return

                forbidden_choice = random.choice(CHOICES)
                room['current_forbidden'] = forbidden_choice
                room['state'] = f'round_{round_num}'

                socketio.emit('forbidden_new_round', {
                    'round': round_num
                }, to=room_id)

                for t in range(15, 0, -1):
                    socketio.emit('forbidden_timer', {'time': t}, to=room_id)
                    eventlet.sleep(1)
                    if room_id not in forbidden_rooms:
                        print(f"LOG: Phòng {room_id} bị xóa, dừng timer vòng.")
                        return

                # HẾT GIỜ, XỬ LÝ KẾT QUẢ VÒNG
                losers_this_round = []
                survivors = []
                banned_card = room['current_forbidden']

                current_players = dict(room['players'])

                for sid, player in current_players.items():
                    if player['status'] == 'playing':
                        choice = player.get('choice')
                        if choice is None or choice == banned_card:
                            player['status'] = 'out'
                            losers_this_round.append(player['username'])
                        else:
                            player['wins'] += 1
                            survivors.append(player['username'])
                        player['choice'] = None

                socketio.emit('forbidden_round_result', {
                    'losers': losers_this_round,
                    'survivors': survivors,
                    'players_data': room['players'],
                    'banned_card': banned_card
                }, to=room_id)
                eventlet.sleep(5)  # Nghỉ 5s xem kết quả vòng

                if round_num == 5:
                    survivors_at_cp = []
                    for sid, player in current_players.items():
                        if player['status'] == 'playing' and player['wins'] == 5:
                            survivors_at_cp.append(sid)
                            emit('forbidden_checkpoint',
                                 {'message': 'Bạn đã sống sót 5 vòng! Dừng lại (100v) hay chơi tiếp (1000v)?'},
                                 to=sid)

                    # Nếu có người sống sót để ra quyết định, thì PAUSE game
                    if survivors_at_cp:
                        print(f"LOG: {room_id} đang ở Checkpoint Vòng 5. Chờ 15s...")
                        room['state'] = 'checkpoint'

                        # Đếm ngược 15s cho người chơi quyết định
                        for t in range(15, 0, -1):
                            socketio.emit('forbidden_timer', {'time': t}, to=room_id)
                            eventlet.sleep(1)
                            if room_id not in forbidden_rooms:
                                print(f"LOG: Phòng {room_id} bị xóa, dừng timer checkpoint.")
                                return

                        room['state'] = 'playing'  # Reset state
                        socketio.emit('system_message', {'message': 'Hết giờ quyết định. Ai không dừng là chơi tiếp!'},
                                      to=room_id)

                # Kiểm tra nếu hết người chơi (bao gồm cả người vừa 'stopped')
                current_survivors = [p for p in room['players'].values() if p['status'] == 'playing']
                if not current_survivors:
                    socketio.emit('forbidden_game_over',
                                  {'message': 'Tất cả đã bị loại hoặc dừng lại! Chuẩn bị ván mới...'}, to=room_id)
                    game_over = True
                    break  # Thoát vòng lặp for (10 vòng)

            # HẾT 10 VÒNG (Nếu game không bị break sớm)
            if not game_over:
                final_winners = []
                for sid, player in room['players'].items():
                    if player['status'] == 'playing' and player['wins'] == 10:
                        final_winners.append(player['username'])
                        # === SỬA LỖI 2: Dùng hàm _db_only ===
                        new_currency = update_currency_db_only(player['username'], 1000)
                        emit('currency_update',
                             {'winner_username': player['username'], 'amount': 1000, 'new_currency': new_currency},
                             to=sid)

                msg = f'Chúc mừng người chiến thắng 1000v: {", ".join(final_winners)}! Chuẩn bị ván mới...' if final_winners else 'Không ai sống sót 10 vòng. Chuẩn bị ván mới...'
                socketio.emit('forbidden_game_over', {'message': msg}, to=room_id)

            room['state'] = 'waiting'
            print(f"LOG: Game Tử Cấm {room_id} kết thúc. Chờ 5s để reset...")
            eventlet.sleep(5)

        except Exception as e:
            print(f"LỖI NGHIÊM TRỌNG TRONG GAME LOOP TỬ CẤM ({room_id}): {e}")
            room['state'] = 'waiting'
            eventlet.sleep(5)
            if room_id not in forbidden_rooms:
                print("Phòng không còn, dừng hẳn vòng lặp.")
                return


def get_waiting_pvp_rooms():
    """
    Trả về danh sách các phòng PvP đang chờ người chơi 2.
    """
    waiting_rooms = []
    for room_id, room in rooms.items():
        if room.get('player2') is None:
            waiting_rooms.append({
                'room_id': room_id,
                'player1_name': room['player1']['username'] if room['player1'] else "Trống",
                'has_password': bool(room.get('password'))
            })
    return waiting_rooms


#
# === XỬ LÝ KẾT NỐI / NGẮT KẾT NỐI ===


@socketio.on('connect')
def handle_connect():
    pass


@socketio.on('disconnect')
def handle_disconnect(reason=None):
    username = "Guest"
    # SỬA LỖI: Phải lấy session an toàn
    try:
        username = session.get("username", "Guest")
    except Exception:
        pass  # Không có context, bỏ qua

    room_id, room, game_mode = find_room_by_sid(request.sid)
    if not room:
        queue_entry = next((item for item in quick_match_queue if item['sid'] == request.sid), None)
        if queue_entry:
            quick_match_queue.remove(queue_entry)
        return

    if game_mode == 'pvp':
        p1 = room.get('player1')
        p2 = room.get('player2')
        is_p1 = p1 and p1.get('sid') == request.sid
        is_p2 = p2 and p2.get('sid') == request.sid

        # LOGIC: Nếu P1 hoặc P2 thoát, xóa phòng và thông báo cho tất cả (bao gồm người còn lại)
        if is_p1 or is_p2:
            opponent_sid = None

            # 1. Thông báo đóng phòng cho tất cả client trong phòng
            emit('leave', {'message': f"Người chơi {username} đã rời. Phòng đã đóng."}, to=room_id,
                 skip_sid=request.sid)

            # 2. Xóa phòng
            if room_id in rooms: del rooms[room_id]

            # 3. Cập nhật lại danh sách phòng chờ (nếu có)
            socketio.emit('pvp_waiting_rooms', {'rooms': get_waiting_pvp_rooms()})

        else:
            # Spectator rời
            if request.sid in room.get('spectators', []):
                room['spectators'].remove(request.sid)


    elif game_mode == 'baucua' or game_mode == 'forbidden':
        if request.sid in room['players']:
            # Lấy username từ data trong phòng, không dùng session
            player_username = room['players'][request.sid].get('username', 'Guest')
            print(f"LOG: {player_username} ({game_mode} Player) đã rời phòng {room_id}.")
            del room['players'][request.sid]

            # Nếu phòng trống
            if not room['players']:
                # KHÔNG XÓA NGAY!
                # Bắt đầu chạy ngầm hàm chờ 5 giây
                socketio.start_background_task(check_and_delete_room, room_id, game_mode)
            else:
                # Cập nhật danh sách người chơi cho những người còn lại
                if game_mode == 'baucua':
                    emit('baucua_state_update', {'state': room.get('state'), 'players': get_players_in_room(room)},
                         to=room_id)
                else:
                    # Gửi tin nhắn hệ thống thay vì 'player_left' (không tồn tại)
                    emit('system_message', {'message': f'{player_username} đã rời.'}, to=room_id)
                    emit('forbidden_state_update', {
                        'state': room.get('state', 'waiting'),
                        'players_data': room['players']
                    }, to=room_id)

    # === SỬA LOGIC: Thêm xử lý ngắt kết nối cho Game Thẻ Bài ===
    elif game_mode == 'cardgame':
        player = next((p for p in room['players'] if p['sid'] == request.sid), None)
        if player:
            room['players'].remove(player)
            player_name = player.get('name', 'Một người chơi')
            print(f"LOG: {player_name} (Card Game) đã rời phòng {room_id}.")

            # Báo cho người còn lại
            if room['players']:  # Nếu còn 1 người
                opponent_sid = room['players'][0]['sid']
                opponent_name = room['players'][0]['name']
                emit('opponentLeft', {'msg': f"'{player_name}' đã rời phòng."}, to=opponent_sid)

                # Reset deck và score cho người còn lại
                new_deck = create_deck()
                room['players'][0]['deck'] = new_deck
                room['players'][0]['choice'] = None
                room['score'] = {opponent_name: 0}  # Reset score

                emit('updateDeck', {
                    'selfName': opponent_name,
                    'opponentName': '...',
                    'deck': new_deck,
                    'roomId': room_id
                }, to=opponent_sid)

            # Nếu phòng trống, xóa phòng
            if not room['players']:
                if room_id in card_game_rooms:
                    del card_game_rooms[room_id]
                    print(f"LOG: Đã xóa phòng Card Game {room_id} (trống).")
    # === KẾT THÚC SỬA LOGIC ===


# === LOGIC TẠO / VÀO PHÒNG ===

@socketio.on('create_room')
def handle_create_room(data):
    username = session.get('username')
    if not username:
        emit('join_error', {'error': 'Bạn cần đăng nhập.'}, to=request.sid)
        return
    room_id_custom = data.get('room_id_custom')
    game_mode = data.get('game_mode', 'pvp')
    password = data.get('password')
    if not room_id_custom or room_id_custom.strip() == "":
        emit('join_error', {'error': 'Vui lòng tự nhập mã phòng!'}, to=request.sid)
        return
    if game_mode not in GAME_MODES_CONFIG:
        emit('join_error', {'error': 'Game mode không hợp lệ.'}, to=request.sid)
        return

    mode_config = GAME_MODES_CONFIG[game_mode]
    room_dict = mode_config['dict']
    room_id = mode_config['prefix'] + room_id_custom.strip().upper()

    if room_id in room_dict:
        emit('join_error', {'error': f'Phòng "{room_id_custom.strip().upper()}" đã tồn tại!'}, to=request.sid)
        return

    join_room(room_id)

    if game_mode == 'pvp':
        player_data = {'sid': None, 'username': username}
        room_dict[room_id] = {
            'player1': player_data, 'player2': None,
            'spectators': [], 'password': password,
            'score': {username: 0}
        }
        # Chuyển hướng client bằng event `room_joined`
        emit('room_joined', {'room_id': room_id, 'game_mode': 'pvp'}, to=request.sid)
        # Cập nhật lại danh sách phòng chờ
        socketio.emit('pvp_waiting_rooms', {'rooms': get_waiting_pvp_rooms()})

    elif game_mode == 'baucua':
        room_dict[room_id] = {
            'players': {},  # Để trống để tránh lỗi disconnect
            'state': 'waiting',
            'game_loop_task': None,
            'bets': {}
        }
        # Khởi động game loop
        if room_dict[room_id]['game_loop_task'] is None:
            room_dict[room_id]['game_loop_task'] = socketio.start_background_task(baucua_game_loop, room_id)

        # Gửi sự kiện để client chuyển trang
        emit('room_joined', {'room_id': room_id, 'game_mode': 'baucua'})

    elif game_mode == 'forbidden':
        if session.get('currency', 0) < 10:
            emit('join_error', {'error': 'Không đủ tiền cược (10v).'}, to=request.sid)
            return

        # Hàm này an toàn, nó đang ở trong 1 event handler
        new_currency = update_currency(username, -10)

        if 'username' in session:
            # Gửi số tiền mới về, không cần gửi số tiền trừ
            emit('currency_update', {'winner_username': username, 'new_currency': new_currency, 'amount': -10})

        room_dict[room_id] = {
            'players': {},  # Để trống để an toàn
            'state': 'waiting',
            'game_loop_task': None,
            'choices': {},
            'round': 0
        }
        if room_dict[room_id]['game_loop_task'] is None:
            room_dict[room_id]['game_loop_task'] = socketio.start_background_task(forbidden_game_loop, room_id)
        emit('room_joined', {'room_id': room_id, 'game_mode': 'forbidden'})


@socketio.on('join_room')
def handle_join_game(data):
    # Hàm này dùng để Join Game từ Lobby (qua danh sách phòng)
    username = session.get('username')
    if not username: return
    room_id = data.get('room_id', '').upper()
    password = data.get('password')  # Lấy mật khẩu từ data
    room, game_mode = find_room(room_id)
    if not room:
        emit('join_error', {'error': 'Phòng không tồn tại.'}, to=request.sid)
        emit('pvp_waiting_rooms', {'rooms': get_waiting_pvp_rooms()}, to=request.sid)
        return

    if game_mode == 'pvp':
        # Kiểm tra mật khẩu (áp dụng cho cả Join và Spectate)
        if room.get('password') and room.get('password') != password:
            emit('join_error', {'error': 'Sai mật khẩu.'}, to=request.sid)
            emit('pvp_waiting_rooms', {'rooms': get_waiting_pvp_rooms()}, to=request.sid)
            return

        # Chuyển hướng. Logic gán player2 sẽ được xử lý trong handle_player_joined_page
        real_room_id = next((k for k, v in rooms.items() if v == room), room_id)
        emit('room_joined', {'room_id': real_room_id, 'game_mode': 'pvp'}, to=request.sid)


@socketio.on('player_joined_game_page')
def handle_player_joined_page(data):
    """ Check-in chính thức khi đã ở trang Game (Cho cả 3 game) """
    room_id = data.get('room_id')
    username = data.get('username')
    sid = request.sid
    room, game_mode = find_room(room_id)

    if not room:
        emit('join_error', {'error': f'Phòng "{room_id}" không tồn tại.'}, to=sid)
        return

    join_room(room_id, sid=sid)

    # --- XỬ LÝ CHO PVP ---
    if game_mode == 'pvp':
        player1 = room.get('player1')
        player2 = room.get('player2')
        is_player = False

        # 1. Logic Rejoin (P1 hoặc P2)
        if player1 and player1['username'] == username:
            player1['sid'] = sid
            is_player = True
        elif player2 and player2['username'] == username:
            player2['sid'] = sid
            is_player = True

        # 2. Logic Player 2 Join Lần Đầu (SỬA LỖI GÁN P2)
        # Nếu phòng có P1 và P2 là None, gán P2
        elif player1 and player2 is None and player1['username'] != username:
            room['player2'] = {'sid': sid, 'username': username}
            room['score'][username] = 0
            is_player = True

        # 3. Logic Spectator
        if not is_player:
            if 'spectators' not in room: room['spectators'] = []
            if sid not in room['spectators']: room['spectators'].append(sid)

        player1_name = player1['username'] if player1 else "Player 1"
        player2_name = room['player2']['username'] if room.get('player2') else "Đang chờ..."
        is_full = room.get('player2') is not None
        message = "Trận đấu đang diễn ra!" if is_full else "Đang chờ người chơi 2..."

        # Gửi Spectator Update cho TẤT CẢ client trong phòng
        socketio.emit('spectator_update', {
            'room_id': room_id,
            'user1': player1_name,
            'user2': player2_name,
            'message': message,
            'score1': room['score'].get(player1_name, 0),
            'score2': room['score'].get(player2_name, 0)
        }, to=room_id)

        # Gửi thông báo hệ thống và cập nhật danh sách phòng nếu phòng vừa đầy
        if is_full:
            # Gửi thông báo khởi động chỉ một lần khi P2 kết nối lần đầu
            # Kiểm tra P2 vừa join thành công (SID được gán mới)
            if is_player and room['player1'].get('sid') and room['player2'].get('sid') and sid == room['player2'].get(
                    'sid'):
                emit('system_message',
                     {'message': f"Trận đấu đã đủ người chơi: {player1_name} vs {player2_name}. Bắt đầu chơi!"},
                     to=room_id)
                # Cập nhật danh sách phòng (sau khi phòng đầy, nó sẽ biến mất)
                socketio.emit('pvp_waiting_rooms', {'rooms': get_waiting_pvp_rooms()})

        # --- XỬ LÝ CHO CÁC GAME KHÁC (Giữ nguyên) ---
    elif game_mode == 'baucua':
        if 'players' not in room: room['players'] = {}
        room['players'][sid] = {'sid': sid, 'username': username}
        print(f"LOG: {username} đã check-in vào phòng Bầu Cua {room_id}")

        # Cập nhật lại trạng thái cho người vừa vào
        emit('baucua_state_update', {
            'state': room.get('state', 'betting'),
            'time_left': 15,  # Gửi thời gian mặc định, client sẽ tự cập nhật
            'players': get_players_in_room(room)
        }, to=sid)  # Chỉ gửi cho người vừa vào

        # Gửi cập nhật danh sách người chơi cho cả phòng
        socketio.emit('baucua_state_update', {
            'players': get_players_in_room(room)
        }, to=room_id, skip_sid=sid)


    elif game_mode == 'forbidden':
        if 'players' not in room: room['players'] = {}

        player_status = 'spectating'
        if room.get('state', 'waiting') == 'waiting':
            player_status = 'playing'

        room['players'][sid] = {'sid': sid, 'username': username, 'status': player_status, 'wins': 0, 'choice': None}
        print(f"LOG: {username} đã check-in vào phòng Tử Cấm {room_id} (Trạng thái: {player_status})")

        emit('forbidden_state_update', {
            'state': room.get('state', 'waiting'),
            'message': 'Đã tham gia phòng.',
            'players_data': room['players']
        }, to=sid)

        socketio.emit('forbidden_state_update', {
            'state': room.get('state', 'waiting'),
            'message': f'{username} đã tham gia.',
            'players_data': room['players']
        }, to=room_id, skip_sid=sid)


@socketio.on('quick_match')
def handle_quick_match(data):
    username = session.get('username')
    if not username: return
    if any(item['username'] == username for item in quick_match_queue): return

    if not quick_match_queue:
        quick_match_queue.append({'sid': request.sid, 'username': username})
        emit('system_message', {'message': 'Đang tìm trận...'}, to=request.sid)
    else:
        opponent = quick_match_queue.pop(0)
        room_id = "PVP-" + create_random_string(3).upper()

        p1_data = {'sid': None, 'username': opponent['username'], 'choice': None}
        p2_data = {'sid': None, 'username': username, 'choice': None}

        rooms[room_id] = {
            'player1': p1_data, 'player2': p2_data,
            'spectators': [], 'password': None,
            'score': {p1_data['username']: 0, p2_data['username']: 0}
        }

        # Chuyển hướng client bằng event `room_joined`
        emit('room_joined', {'room_id': room_id, 'game_mode': 'pvp'}, to=request.sid)
        try:
            emit('room_joined', {'room_id': room_id, 'game_mode': 'pvp'}, to=opponent['sid'])
        except:
            pass
        # THÊM: Cập nhật danh sách phòng (nó sẽ không hiển thị vì đã đủ người)
        socketio.emit('pvp_waiting_rooms', {'rooms': get_waiting_pvp_rooms()})


@socketio.on('player_choice')
def handle_player_choice(data):
    # ... (Giữ nguyên code PvP Choice đã sửa ở lần trước) ...
    print("\n>>> [DEBUG] Bắt đầu xử lý Player Choice")
    room_id = data.get('room_id')
    choice = data.get('choice')
    room = rooms.get(room_id)
    if not room:
        print(f"-> LỖI: Không tìm thấy phòng {room_id}")
        return
    username = session.get('username')
    player_key = None
    p1 = room.get('player1')
    p2 = room.get('player2')
    if p1 and p1['username'] == username:
        player_key = 'player1'
    elif p2 and p2['username'] == username:
        player_key = 'player2'
    if not player_key:
        print("-> LỖI: Người chơi không khớp với P1 hoặc P2.")
        return

    room[player_key]['choice'] = choice
    p1_choice = room['player1'].get('choice') if room.get('player1') else None
    p2_choice = room['player2'].get('choice') if room.get('player2') else None

    if p1_choice and p2_choice:
        print(">>> CẢ HAI ĐÃ CHỌN -> TÍNH KẾT QUẢ!")
        result = get_winner(p1_choice, p2_choice)
        winner = None
        msg = ""

        # Dùng tên người chơi để tính toán và lưu điểm
        p1_name = room['player1']['username']
        p2_name = room['player2']['username']

        if result == 'tie':
            msg = f"HÒA! Cả hai cùng ra {p1_choice}"
            # Gửi AI suggestion cho cả 2 người chơi
            if p1.get('sid'): emit('ai_suggestion', {'suggestion': get_ai_suggestion(room_id, p1['sid'])}, to=p1['sid'])
            if p2.get('sid'): emit('ai_suggestion', {'suggestion': get_ai_suggestion(room_id, p2['sid'])}, to=p2['sid'])
        elif result == 'player1_win':
            winner = p1_name
            msg = f"{winner} thắng! ({p1_choice} vs {p2_choice})"
            room['score'][winner] += 1
            # Gửi AI suggestion cho người chơi 1
            if p1.get('sid'): emit('ai_suggestion', {'suggestion': get_ai_suggestion(room_id, p1['sid'])}, to=p1['sid'])
        else:  # player2_win
            winner = p2_name
            msg = f"{winner} thắng! ({p2_choice} vs {p1_choice})"
            room['score'][winner] += 1
            # Gửi AI suggestion cho người chơi 2
            if p2.get('sid'): emit('ai_suggestion', {'suggestion': get_ai_suggestion(room_id, p2['sid'])}, to=p2['sid'])

        # Cập nhật tiền tệ, stats và thông báo
        if winner:
            # Hàm này an toàn, nó đang ở trong 1 event handler
            nc = update_currency(winner, 10)

            users.update_one({"username": p1_name}, {"$inc": {"played": 1}})
            users.update_one({"username": p2_name}, {"$inc": {"played": 1}})
            users.update_one({"username": winner}, {"$inc": {"wins": 1}})

            # Gửi tín hiệu cập nhật tiền cho TẤT CẢ client trong phòng (để người thắng biết)
            emit('currency_update', {'winner_username': winner, 'new_currency': nc, 'amount': 10}, to=room_id)

        emit('round_result', {
            'message': msg,
            'score1': room['score'][p1_name],
            'score2': room['score'][p2_name]
        }, to=room_id)

        room['player1']['choice'] = None
        room['player2']['choice'] = None
    else:
        print("-> Mới chỉ có 1 người chọn. Đang gửi thông báo chờ...")
        opponent_key = 'player2' if player_key == 'player1' else 'player1'
        opponent = room.get(opponent_key)

        # Gửi thông báo chờ cho người chơi còn lại (P1/P2)
        if opponent and opponent.get('sid'):
            emit('wait', {'person_waiting': username}, to=opponent['sid'])

        # Gửi thông báo chờ cho người chọn xong (để họ thấy thông báo)
        emit('system_message', {'message': f"Bạn đã chọn {choice}. Đang chờ đối thủ..."}, to=request.sid)

    print(">>> [DEBUG] Kết thúc xử lý.\n")


@socketio.on('send_message')
def handle_send_message(data):
    room_id = data.get('room_id')
    room, _ = find_room(room_id)
    if room:
        emit('receive_message',
             {'username': html.escape(data.get('username', 'Guest')), 'message': html.escape(data.get('message', ''))},
             to=room_id)


# === SỰ KIỆN MỚI: LẤY DANH SÁCH PHÒNG CHỜ PVP (Cho Lobby) ===
@socketio.on('get_waiting_pvp_rooms')
def handle_get_waiting_pvp_rooms():
    """
    Xử lý yêu cầu gửi danh sách các phòng PvP đang chờ (1 người chơi).
    """
    rooms_data = get_waiting_pvp_rooms()
    emit('pvp_waiting_rooms', {'rooms': rooms_data}, to=request.sid)


@socketio.on('forbidden_mode_choice')
def handle_forbidden_choice(data): pass


@socketio.on('baucua_bet')
def handle_baucua_bet(data):
    room_id = data.get('room_id')
    bet_type = data.get('bet_type')
    amount = int(data.get('amount', 10))
    username = session.get('username')

    room = baucua_rooms.get(room_id)
    if not room or room.get('state') != 'betting':
        emit('baucua_error', {'error': 'Hết giờ cược!'}, to=request.sid)
        return

    if 'bets' not in room: room['bets'] = {}
    if username not in room['bets']: room['bets'][username] = {}

    current_bets = sum(room['bets'][username].values())

    MAX_BET_PER_USER = 100

    if current_bets + amount > MAX_BET_PER_USER:
        emit('baucua_error', {'error': f'Tổng cược tối đa là {MAX_BET_PER_USER}v. Bạn đã cược {current_bets}v.'},
             to=request.sid)
        return

    current_money = session.get('currency', 0)

    if current_money < amount:
        emit('baucua_error', {'error': 'Không đủ tiền!'}, to=request.sid)
        return

    # Trừ tiền VÀ lấy số dư mới (Hàm này an toàn, đang ở event handler)
    new_currency = update_currency(username, -amount)

    # Gửi tín hiệu cập nhật tiền NGAY LẬP TỨC
    emit('currency_update', {'winner_username': username, 'amount': -amount, 'new_currency': new_currency},
         to=request.sid)

    # LƯU CƯỢC (cộng dồn)
    room['bets'][username][bet_type] = room['bets'][username].get(bet_type, 0) + amount

    # Tính tổng cược của cả phòng cho ô đó để hiển thị
    aggregated = {}
    for u in room['bets']:
        for k, v in room['bets'][u].items():
            aggregated[k] = aggregated.get(k, 0) + v

    # Gửi cập nhật để các client thấy tổng tiền cược đã được cộng dồn
    socketio.emit('update_bets', {'bets': aggregated}, to=room_id)


@socketio.on('forbidden_choice')
def handle_forbidden_choice(data):
    room_id = data.get('room_id')
    choice = data.get('choice')
    sid = request.sid

    room = forbidden_rooms.get(room_id)
    if not room or sid not in room['players']:
        return

    player = room['players'][sid]
    if player['status'] == 'playing' and player['choice'] is None:
        player['choice'] = choice
        emit('system_message', {'message': f"Bạn đã chọn: {choice}"}, to=sid)


@socketio.on('forbidden_stop')
def handle_forbidden_stop(data):
    room_id = data.get('room_id')
    sid = request.sid

    room = forbidden_rooms.get(room_id)
    if not room or sid not in room['players']:
        return

    player = room['players'][sid]
    # Chỉ cho dừng ở checkpoint (sau vòng 5)
    if player['status'] == 'playing' and player['wins'] == 5:
        player['status'] = 'stopped'  # Dừng lại

        # Hàm này an toàn, đang ở event handler
        new_currency = update_currency(player['username'], 100)

        emit('currency_update', {'winner_username': player['username'], 'amount': 100, 'new_currency': new_currency},
             to=sid)
        emit('system_message', {'message': 'Bạn đã dừng lại và nhận 100v. Bạn sẽ là khán giả đến hết game.'}, to=sid)

        # Báo cho những người khác
        socketio.emit('player_left_round', {'username': player['username']}, to=room_id, skip_sid=sid)


# === SỬA LOGIC: Điền logic cho các hàm game thẻ bài ===
@socketio.on('createRoom')
def handle_card_create(data):
    name = data.get('name')
    room_id = data.get('room_id_custom')  # Khớp với JS
    if not name or not room_id:
        emit('opponentLeft', {'msg': 'Lỗi: Thiếu tên hoặc mã phòng.'})
        return

    if room_id in card_game_rooms:
        emit('opponentLeft', {'msg': f'Lỗi: Phòng {room_id} đã tồn tại.'})
        return

    # create_deck() được import từ utils
    deck1 = create_deck()

    card_game_rooms[room_id] = {
        'players': [
            {'sid': request.sid, 'name': name, 'deck': deck1, 'choice': None}
        ],
        'spectators': [],
        'score': {name: 0}
    }
    join_room(room_id)
    print(f"LOG: {name} đã tạo phòng Card Game {room_id}")
    emit('room_created', {'roomId': room_id})
    # Gửi bộ bài đầu tiên cho người tạo phòng
    emit('updateDeck', {'selfName': name, 'opponentName': '...', 'deck': deck1, 'roomId': room_id})


@socketio.on('joinRoom')
def handle_card_join(data):
    name = data.get('name')
    room_id = data.get('roomId')
    if not name or not room_id:
        emit('opponentLeft', {'msg': 'Lỗi: Thiếu tên hoặc mã phòng.'})
        return

    room = card_game_rooms.get(room_id)
    if not room:
        emit('opponentLeft', {'msg': f'Lỗi: Phòng {room_id} không tồn tại.'})
        return

    if len(room['players']) >= 2:
        emit('opponentLeft', {'msg': f'Lỗi: Phòng {room_id} đã đầy.'})
        return

    deck2 = create_deck()
    player2_data = {'sid': request.sid, 'name': name, 'deck': deck2, 'choice': None}
    room['players'].append(player2_data)
    room['score'][name] = 0

    join_room(room_id)
    print(f"LOG: {name} đã tham gia phòng Card Game {room_id}")

    player1_data = room['players'][0]

    # Báo cho P2 (người vừa join)
    emit('updateDeck', {
        'selfName': name,  # Tên của P2
        'opponentName': player1_data['name'],  # Tên của P1
        'deck': deck2,
        'roomId': room_id
    }, to=request.sid)

    # Cập nhật cho P1 (người đã ở trong phòng)
    emit('updateDeck', {
        'selfName': player1_data['name'],  # Tên của P1
        'opponentName': name,  # Tên của P2
        'deck': player1_data['deck'],  # Bộ bài của P1
        'roomId': room_id
    }, to=player1_data['sid'])


@socketio.on('playCard')
def handle_card_play(data):
    room_id = data.get('roomId')
    card = data.get('card')  # 'Kéo', 'Búa', 'Bao'
    room = card_game_rooms.get(room_id)

    if not room or len(room['players']) < 2:
        return  # Phòng chưa sẵn sàng

    player = next((p for p in room['players'] if p['sid'] == request.sid), None)
    if not player:
        return  # Không phải người chơi

    if card not in player['deck']:
        emit('opponentLeft', {'msg': 'Lỗi: Bạn không có thẻ này!'})
        return

    if player['choice']:
        emit('opponentLeft', {'msg': 'Bạn đã chọn rồi, chờ đối thủ.'})
        return

    player['choice'] = card

    # Kiểm tra xem đối thủ đã chọn chưa
    p1 = room['players'][0]
    p2 = room['players'][1]

    if p1['choice'] and p2['choice']:
        # Cả hai đã chọn, xử lý kết quả
        result_text = ""
        winner = get_card_winner(p1['choice'], p2['choice'])  # Dùng hàm helper

        if winner == 'tie':
            result_text = f"HÒA! Cả hai cùng ra {p1['choice']}."
        elif winner == 'p1_win':
            result_text = f"THẮNG! {p1['name']} ({p1['choice']}) thắng {p2['name']} ({p2['choice']})."
            room['score'][p1['name']] += 1
        else:  # p2_win
            result_text = f"THẮNG! {p2['name']} ({p2['choice']}) thắng {p1['name']} ({p1['choice']})."
            room['score'][p2['name']] += 1

        # Xóa thẻ đã dùng
        try:
            p1['deck'].remove(p1['choice'])
            p2['deck'].remove(p2['choice'])
        except ValueError:
            print(f"LỖI: Không thể xóa thẻ {p1['choice']} hoặc {p2['choice']} khỏi bộ bài.")

        # Gửi kết quả cho P1
        socketio.emit('roundResult', {
            'p1Card': {'name': p1['name'], 'card': p1['choice']},
            'p2Card': {'name': p2['name'], 'card': p2['choice']},
            'resultText': result_text,
            'score': room['score'],
            'deck': p1['deck']  # Gửi bộ bài mới của P1
        }, to=p1['sid'])

        # Gửi kết quả cho P2
        socketio.emit('roundResult', {
            'p1Card': {'name': p1['name'], 'card': p1['choice']},
            'p2Card': {'name': p2['name'], 'card': p2['choice']},
            'resultText': result_text,
            'score': room['score'],
            'deck': p2['deck']  # Gửi bộ bài mới của P2
        }, to=p2['sid'])

        # Reset choice
        p1['choice'] = None
        p2['choice'] = None

        # Kiểm tra game over (hết bài)
        if not p1['deck']:
            p1_score = room['score'][p1['name']]
            p2_score = room['score'][p2['name']]
            final_msg = "TRẬN ĐẤU KẾT THÚC!\n"

            if p1_score > p2_score:
                final_msg += f"{p1['name']} thắng chung cuộc {p1_score}-{p2_score}!"
                update_currency(p1['name'], 20)  # Thưởng 20v
                update_currency(p2['name'], -10)  # Phạt 10v
            elif p2_score > p1_score:
                final_msg += f"{p2['name']} thắng chung cuộc {p2_score}-{p1_score}!"
                update_currency(p2['name'], 20)  # Thưởng 20v
                update_currency(p1['name'], -10)  # Phạt 10v
            else:
                final_msg += f"HÒA CHUNG CUỘC {p1_score}-{p2_score}!"

            socketio.emit('opponentLeft', {'msg': final_msg}, to=room_id)

            # Reset phòng
            p1['deck'] = create_deck()
            p2['deck'] = create_deck()
            room['score'][p1['name']] = 0
            room['score'][p2['name']] = 0

            # Gửi lại deck mới
            socketio.emit('updateDeck',
                          {'selfName': p1['name'], 'opponentName': p2['name'], 'deck': p1['deck'], 'roomId': room_id},
                          to=p1['sid'])
            socketio.emit('updateDeck',
                          {'selfName': p2['name'], 'opponentName': p1['name'], 'deck': p2['deck'], 'roomId': room_id},
                          to=p2['sid'])


# === KẾT THÚC SỬA LOGIC ===


# === LOGIC MỚI: XỬ LÝ CHƠI ĐƠN (Gợi ý AI) ===
@socketio.on('ai_game_request')
def handle_ai_game_request(data):
    """
    Xử lý request từ trang chơi đơn (single player) để lấy gợi ý.
    """
    # Simulate AI processing time
    eventlet.sleep(0.5)

    # Random suggestion logic
    suggestion = random.choice(['rock', 'paper', 'scissor'])

    emit('ai_suggestion', {'suggestion': suggestion}, to=request.sid)

# === KẾT THÚC LOGIC MỚI ===