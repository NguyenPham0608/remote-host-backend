const express = require('express');
const { Client } = require('ssh2');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 5000;

app.post('/connect', (req, res) => {
    const { host, username, password, command, cwd } = req.body;
    const conn = new Client();

    // Clean up the host string (removes brackets from IPv6 if present)
    const cleanHost = host ? host.replace(/[\[\]]/g, '') : '';

    conn.on('ready', () => {
        /**
         * The Logic:
         * 1. Move to the directory the user was last in (cwd)
         * 2. Execute the user's command
         * 3. Print a unique delimiter
         * 4. Run 'pwd' to see where we ended up (in case they used 'cd')
         */
        const chainedCommand = `cd ${cwd || '~'} && ${command} && echo "---CWD_DELIMITER---" && pwd`;

        conn.exec(chainedCommand, (err, stream) => {
            if (err) {
                conn.end();
                return res.status(500).json({ error: err.message });
            }

            let data = '';
            let stderr = '';

            stream.on('data', (d) => { data += d; });
            stream.on('stderr', (d) => { stderr += d; });

            stream.on('close', (code) => {
                const fullOutput = data.toString();

                // Split output by our custom delimiter to find the new path
                const parts = fullOutput.split("---CWD_DELIMITER---");
                const commandOutput = parts[0].trim();
                const newPath = parts[1] ? parts[1].trim() : (cwd || '~');

                res.json({
                    output: commandOutput || stderr || (code === 0 ? "" : "Command failed"),
                    newPath: newPath,
                    exitCode: code
                });

                conn.end();
            });
        });
    }).on('error', (err) => {
        console.error('SSH Connection Error:', err.message);
        res.status(500).json({ error: "Connection failed: " + err.message });
    }).connect({
        host: cleanHost,
        port: 22,
        username: username,
        password: password,
        family: 6,           // Supports both IPv4 and IPv6
        readyTimeout: 30000, // 30 seconds to prevent handshake timeouts on slow networks
        keepaliveInterval: 1000,
        keepaliveCountMax: 3
    });
});

app.listen(PORT, () => {
    console.log(`----------------------------------------`);
    console.log(`Terminal Backend PoC Live on Port ${PORT}`);
    console.log(`Ready for SSH commands...`);
    console.log(`----------------------------------------`);
});