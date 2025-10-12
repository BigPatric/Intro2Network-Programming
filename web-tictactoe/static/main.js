let socket = io();
let mySymbol, room, myTurn, board;

function join() {
    let username = document.getElementById('username').value;
    socket.emit('join', {username});
}

socket.on('waiting', () => {
    document.getElementById('status').innerText = 'Waiting for another player...';
    document.getElementById('login').style.display = 'none';
    document.getElementById('game').style.display = '';
});

socket.on('start', (data) => {
    mySymbol = data.symbol;
    room = data.room;
    myTurn = (data.turn === mySymbol);
    board = data.board;
    document.getElementById('login').style.display = 'none';
    document.getElementById('game').style.display = '';
    updateStatus();
    drawBoard();
});

socket.on('move', (data) => {
    board = data.board;
    myTurn = (data.turn === mySymbol);
    document.getElementById('cell'+data.idx).innerText = data.symbol;
    updateStatus();
});

socket.on('end', (data) => {
    board = data.board;
    drawBoard();
    let msg = '';
    if (data.winner === 'Draw') msg = 'It\'s a draw!';
    else if (data.winner === mySymbol) msg = 'You win!';
    else msg = 'You lose!';
    document.getElementById('status').innerHTML = msg + 
        ' <button onclick="restart()">Play again</button> <button onclick="location.reload()">Back to lobby</button>';
    myTurn = false;
});

function drawBoard() {
    let html = '';
    for(let i=0;i<9;i++) {
        html += `<button id="cell${i}" onclick="move(${i})" style="width:60px;height:60px;font-size:2em;" ${board[i] ? 'disabled' : ''}>${board[i]||''}</button>`;
        if(i%3==2) html += '<br>';
    }
    document.getElementById('board').innerHTML = html;
}

function move(idx) {
    if (!myTurn || board[idx]) return;
    socket.emit('move', {room, idx, symbol: mySymbol});
}

function updateStatus() {
    if (myTurn)
        document.getElementById('status').innerText = 'Your turn (' + mySymbol + ')';
    else
        document.getElementById('status').innerText = 'Opponent\'s turn';
}

function restart() {
    socket.emit('restart', {room, symbol: mySymbol});
}