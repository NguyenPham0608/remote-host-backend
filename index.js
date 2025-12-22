const express = require('express');
const { Client } = require('ssh2');
const cors = require('cors');

const app = express();
app.use(cors()); // Allows your HTML file to talk to the server
app.use(express.json());

// Deployment Port for Render
const PORT = process.env.PORT || 5000;

app.post('/connect', (req, res) => {
    const { host, username, password } = req.body;
    const conn = new Client();

    conn.on('ready', () => {
        conn.exec('uptime', (err, stream) => {
            if (err) return res.status(500).send(err.message);
            let data = '';
            stream.on('data', (d) => data += d);
            stream.on('close', () => {
                res.json({ message: "Success", output: data });
                conn.end();
            });
        });
    }).on('error', (err) => {
        res.status(500).json({ error: "Connection failed: " + err.message });
    }).connect({
        host,
        port: 22,
        username,
        password,
        readyTimeout: 10000 // 10 second timeout
    });
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));