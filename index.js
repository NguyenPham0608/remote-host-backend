const express = require('express');
const { Client } = require('ssh2');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 5000;

app.post('/connect', (req, res) => {
    let { host, username, password } = req.body;

    // Clean up the host: Remove [ ] if the user pasted them from a terminal command
    const cleanHost = host.replace(/[\[\]]/g, '');

    const conn = new Client();

    conn.on('ready', () => {
        // We run 'uptime' and 'uname -a' to give you a descriptive PoC output
        conn.exec('uptime && uname -a', (err, stream) => {
            if (err) return res.status(500).json({ error: err.message });

            let data = '';
            stream.on('data', (d) => { data += d; });
            stream.on('close', () => {
                res.json({
                    message: "Successfully connected to Mac!",
                    output: data
                });
                conn.end();
            });
        });
    }).on('error', (err) => {
        console.error('SSH Error:', err.message);
        res.status(500).json({
            error: "Connection failed: " + err.message,
            tip: "Ensure your Mac's IPv6 hasn't changed and Render can reach your network."
        });
    }).connect({
        host: cleanHost,
        port: 22,
        username: username,
        password: password,
        family: 6,           // Forces IPv6 connection
        readyTimeout: 15000, // Increased to 15s for cross-internet latency
        keepaliveInterval: 1000,
        debug: console.log   // This will show connection logs in your Render dashboard
    });
});

app.listen(PORT, () => console.log(`Backend PoC running on port ${PORT}`));