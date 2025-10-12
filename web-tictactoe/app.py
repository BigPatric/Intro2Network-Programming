from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random, json, os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

waiting_player = None
games = {}
online_users = {}  # username -> sid

USERS_FILE = 'users.json'

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('register')
def on_register(data):
    users = load_users()
    username = data['username']
    password = data['password']
    if username in users:
        emit('register_result', {'success': False, 'msg': '帳號已存在'})
    else:
        users[username] = password
        save_users(users)
        emit('register_result', {'success': True})

@socketio.on('login')
def on_login(data):
    users = load_users()
    username = data['username']
    password = data['password']
    if username not in users or users[username] != password:
        emit('login_result', {'success': False, 'msg': '帳號或密碼錯誤'})
    else:
        online_users[username] = request.sid
        emit('login_result', {'success': True})
        emit('player_list', {'players': list(online_users.keys())}, broadcast=True)

@socketio.on('get_players')
def on_get_players():
    emit('player_list', {'players': list(online_users.keys())})

@socketio.on('invite')
def on_invite(data):
    to_user = data['to']
    from_user = data['from']
    to_sid = online_users.get(to_user)
    if to_sid:
        emit('invited', {'from': from_user}, room=to_sid)

@socketio.on('accept_invite')
def on_accept_invite(data):
    from_user = data['from']
    to_user = data['to']
    from_sid = online_users.get(from_user)
    to_sid = online_users.get(to_user)
    if from_sid and to_sid:
        # 建立遊戲房間
        room = f'room_{random.randint(1000,9999)}'
        join_room(room, sid=from_sid)
        join_room(room, sid=to_sid)
        board = ['']*9
        # from_user 是邀請者，給 X，to_user 是被邀請者，給 O
        emit('invite_accepted', {'symbol': 'X', 'room': room, 'turn': 'X', 'board': board}, room=from_sid)
        emit('invite_accepted', {'symbol': 'O', 'room': room, 'turn': 'X', 'board': board}, room=to_sid)
        games[room] = {'board': board, 'turn': 'X'}
    # 可選：清除 lobby_msg

@socketio.on('decline_invite')
def on_decline_invite(data):
    from_user = data['from']
    to_user = data['to']
    from_sid = online_users.get(from_user)
    if from_sid:
        emit('invite_declined', {'to': to_user}, room=from_sid)

@socketio.on('move')
def on_move(data):
    room = data['room']
    idx = data['idx']
    symbol = data['symbol']
    game = games.get(room)
    if not game:
        return
    board = game['board']
    if board[idx] == '' and game['turn'] == symbol:
        board[idx] = symbol
        winner = check_winner(board)
        game['turn'] = 'O' if symbol == 'X' else 'X'
        emit('move', {'idx': idx, 'symbol': symbol, 'turn': game['turn'], 'board': board}, room=room)
        if winner:
            emit('end', {'winner': winner, 'board': board}, room=room)
            del games[room]

def check_winner(board):
    wins = [
        [0,1,2],[3,4,5],[6,7,8],
        [0,3,6],[1,4,7],[2,5,8],
        [0,4,8],[2,4,6]
    ]
    for line in wins:
        a, b, c = line
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(cell for cell in board):
        return 'Draw'
    return None

@socketio.on('restart')
def on_restart(data):
    room = data['room']
    if room not in games:
        games[room] = {'board': ['']*9, 'turn': 'X'}
    else:
        games[room]['board'] = ['']*9
        games[room]['turn'] = 'X'
    emit('start', {'symbol': data['symbol'], 'room': room, 'turn': 'X', 'board': ['']*9}, room=request.sid)

@socketio.on('disconnect')
def on_disconnect():
    # 移除離線玩家
    for user, sid in list(online_users.items()):
        if sid == request.sid:
            del online_users[user]
            break
    emit('player_list', {'players': list(online_users.keys())}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)