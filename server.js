const express = require('express');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

const app = express();
const PORT = 3000;

// Serve the public folder for the client-side HTML/JS/CSS
app.use(express.static(path.join(__dirname, 'public')));

app.use(express.json());  // Middleware to parse JSON bodies

// Serve images from the GEE/Output/PNGs directory
app.use('/images', express.static(path.join(__dirname, 'GEE/Output/PNGs')));

// Endpoint to list PNG images
app.get('/images', (req, res) => {
    
    const imageDir = path.join(__dirname, 'GEE/Output/PNGs');

    // Read all files in the directory
    fs.readdir(imageDir, (err, files) => {
        
        if (err) {

            return res.status(500).json({ error: 'Failed to load images' });
        }

        // Filter only .png files
        const pngFiles = files.filter(file => file.endsWith('.png'));

        // Respond with the list of .png files
        res.json(pngFiles);
    });
});

// Endpoint to serve timestamps

app.get('/timestamps', (req, res) => {

    const timestampsFile = path.join(__dirname, 'GEE/Output/PNGs/TSs.json');

    fs.readFile(timestampsFile, 'utf-8', (err, data) => {
        
        if (err) {
            
            console.error('Error reading TSs file', err);

        } else {

            res.json(JSON.parse(data)); // Envia TSs como JSON al cliente
        }
    });
});

// Endpoint to trigger Python script
app.post('/run-script', (req, res) => {
    
    const pythonScript = path.join(__dirname, 'GEE/GOES.py');

    // Spawn the Python process
    const process = spawn('py', [pythonScript]);

    // Capture inputTextValue
    const date_oi = req.body.date_oi;
    
    // Variable to send to the python script
    const date_py = JSON.stringify({ date_oi });

    // Send the data to Python script's stdin
    process.stdin.write(date_py);

    // Close the stdin stream
    process.stdin.end();

    // Collect stdout and stderr output
    let output = '';
    let errorOutput = '';

    process.stdout.on('data', (data) => {
        
        output += data.toString();

        console.log(output);
    });

    process.stderr.on('data', (data) => {
        
        errorOutput += data.toString();

        // console.log(errorOutput);
    });

    process.on('close', (code) => {
        
        if (code === 0) {

            res.json({ message: 'Python script executed successfully', output });
        
        } else {

            res.status(500).json({ error: `Script failed with exit code ${code}`, stderr: errorOutput });
        }
    });
});

// Start the server
app.listen(PORT, () => {
    
    console.log(`Server running on: http://localhost:${PORT}`);
});