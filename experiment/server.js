/**
 * WebRTC signaling server.
 * Relays offer/answer/ICE-candidate messages between two peers in a room.
 * The SECOND peer to join a room is told to be the "initiator".
 */
const WebSocket = require("ws");
const PORT = process.env.PORT || 8080;

const wss = new WebSocket.Server({ port: PORT });
const rooms = {}; // roomId -> [clients]

wss.on("connection", (ws) => {
  let room = null;

  ws.on("message", (data) => {
    let msg;
    try { msg = JSON.parse(data); } catch { return; }

    if (msg.type === "join") {
      room = msg.room;
      rooms[room] = rooms[room] || [];

      if (rooms[room].length >= 2) {
        ws.send(JSON.stringify({ type: "full" }));
        return;
      }

      rooms[room].push(ws);
      const initiator = rooms[room].length === 2; // 2nd joiner starts the offer
      ws.send(JSON.stringify({ type: "joined", initiator }));
      console.log(`Peer joined "${room}" (${rooms[room].length}/2)`);
      return;
    }

    // Relay signaling messages to the other peer in the room
    if (room && rooms[room]) {
      rooms[room].forEach((client) => {
        if (client !== ws && client.readyState === WebSocket.OPEN) {
          client.send(JSON.stringify(msg));
        }
      });
    }
  });

  ws.on("close", () => {
    if (room && rooms[room]) {
      rooms[room] = rooms[room].filter((c) => c !== ws);
      if (rooms[room].length === 0) delete rooms[room];
      else rooms[room].forEach((c) => {
        if (c.readyState === WebSocket.OPEN) c.send(JSON.stringify({ type: "peer-left" }));
      });
      console.log(`Peer left "${room}"`);
    }
  });
});

console.log(`Signaling server running on ws://localhost:${PORT}`);
