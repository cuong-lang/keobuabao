let socket = io();
let selfName='', opponentName='', roomId='', deck=[], selectedCard=null;

socket.on('room_created', d=>{
    roomId=d.roomId;
    document.getElementById('info').innerText='Phòng: '+roomId;
});

socket.on('updateDeck', d=>{
    selfName=d.selfName; opponentName=d.opponentName; deck=d.deck;
    renderDeck(); renderPlayerInfo();
});

socket.on('roundResult', d=>{
    deck = d.deck;   // nhận deck riêng cho người chơi
    renderDeck();
    showRoundResult(d);
    updateScore(d.score);
});

function createRoom(){
    let n=document.getElementById('name').value.trim();
    if(!n){alert('Nhập tên!');return;}
    socket.emit('createRoom',{name:n});
}
function joinRoom(){
    let n=document.getElementById('name').value.trim();
    let r=document.getElementById('roomId').value.trim();
    if(!n||!r){alert('Nhập tên & phòng!');return;}
    socket.emit('joinRoom',{name:n,roomId:r});
}

function playCard(c){
    selectedCard=c;
    document.querySelectorAll('#deck img').forEach(i=>i.classList.remove('selected'));
    let imgs=document.querySelectorAll(`#deck img[title="${c}"]`);
    if(imgs[0]) imgs[0].classList.add('selected');
    socket.emit('playCard',{roomId:roomId, card:selectedCard});
}

function renderDeck(){
    let html='';
    deck.forEach(c=>{
        let img='';
        if(c=='Kéo') img='static/images/keo.png';
        if(c=='Búa') img='static/images/bua.png';
        if(c=='Bao') img='static/images/bao.png';
        html+=`
        <div class="card">
            <img src="${img}" title="${c}" onclick="playCard('${c}')">
            <span>${c}</span>
        </div>`;
    });
    document.getElementById('deck').innerHTML=html;
}

function renderPlayerInfo(){
    document.getElementById('players').innerHTML=
    `<div class="player-names">
        <div><b>${selfName}</b>: <span id="score-self">0</span></div>
        <div><b>${opponentName}</b>: <span id="score-opponent">0</span></div>
    </div>`;
}

function updateScore(s){
    document.getElementById('score-self').innerText=s[socket.id]||0;
    let opp=Object.keys(s).find(x=>x!=socket.id);
    document.getElementById('score-opponent').innerText=s[opp]||0;
}

function showRoundResult(d){
    let r=document.getElementById('result');
    r.innerText=`${d.p1Card.name} chọn ${d.p1Card.card} | ${d.p2Card.name} chọn ${d.p2Card.card}\n${d.resultText}`;
}
