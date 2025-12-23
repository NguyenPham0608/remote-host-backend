const express = require('express');
const { Client } = require('ssh2');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 5000;

app.post('/connect', (req, res) => {
    const { host, username, password, command } = req.body; // Added command
    const conn = new Client();

    conn.on('ready', () => {
        // We execute whatever command the user typed in the UI
        conn.exec(command || 'ls -la', (err, stream) => {
            if (err) return res.status(500).json({ error: err.message });

            let data = '';
            let stderr = '';
            stream.on('data', (d) => { data += d; });
            stream.on('stderr', (d) => { stderr += d; }); // Catch errors like "File not found"
            stream.on('close', () => {
                res.json({
                    output: data || stderr || "Command executed (no output)."
                });
                conn.end();
            });
        });
    }).on('error', (err) => {
        res.status(500).json({ error: "Connection failed: " + err.message });
    }).connect({
        host: host.replace(/[\[\]]/g, ''),
        port: 22,
        username,
        password,
        family: 6,
        readyTimeout: 15000
    });
});

app.listen(PORT, () => console.log(`Backend PoC running on port ${PORT}`));