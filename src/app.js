/**
app.js
---
SelahSearch
Web service API which uses NLP to match worship lyrics with bible references


MVP Features
---------------------------------------------------------
public API routes:
Public routes for anyone to use freely
---------------------------------------------------------
/passage/:id GET [str song]: get the details of a bible passage, including its content and relevant themes
/song/:id GET [str song]: get the details of a worship song, including its lyrics and relevant themes

/passage/:id/matches GET [str passage]: get the songs relating to a bible passage
/song/:id/matches GET [str song]: get the passages relating to a worship song


---------------------------------------------------------
Database API routes:
Routes that will interact directly with the database, some closely relate with equivalent public API route
---------------------------------------------------------
/passages POST: add a bible passage. Returns error if already exists
/themes POST: add a theme. Returns error if already exists
/songs POST: add a worship song. Returns error if already exists

/passage/:id PUT: update the contents of a bible passage
/song/:id PUT: update the lyrics of a worship song

/passage/:id DELETE: delete a bible passage
/theme/:id DELETE: delete a theme
/song/:id DELETE: delete a worship song

/passage/:id GET: get the contents of a bible passage
/song/:id GET: get the lyrics of a worship song
/songs GET: get a list of all songs in the system
/themes GET: get a list of all themes in the system


*/
require('dotenv').config();
const express = require('express');
const axios = require('axios');
const { Client } = require("@gradio/client");
const { extractPassage, getAllLyrics } = require('./extraction');
const { MongoClient, ServerApiVersion } = require('mongodb');

const { spawn } = require('child_process');

const app = express();

const cors = require("cors");
const corsOptions = {
    origin: '*',
    credentials: true,			// access-control-allow-credentials: true
    optionSuccessStatus: 200,
};
app.use(cors(corsOptions));

// mongodb stuff: will not be used for now but exists to allow for database functionality in the future
const username = encodeURIComponent(process.env.MONGODB_USERNAME) // required to % encode this
const password = encodeURIComponent(process.env.MONGODB_PASSWORD) // required to % encode this
const cluster = 'devcluster'
const dbName = 'SelahSearch'
const uri = `mongodb+srv://${ username }:${ password }@${ cluster }.sypen0x.mongodb.net/${ dbName }?retryWrites=true&w=majority&appName=${ cluster }`

const client = new MongoClient(uri, {
    serverApi: {
        version: ServerApiVersion.v1,
        strict: true,
        deprecationErrors: true,
    }
});
// async function run() {
//     try {
//         await client.connect();
//         // const database = client.db("<dbName>");
//         // const ratings = database.collection("<collName>");
//         // const cursor = ratings.find();
//         // await cursor.forEach(doc => console.dir(doc));
//         // Send a ping to confirm a successful connection
//         await client.db("admin").command({ ping: 1 });
//         console.log("Pinged your deployment. You successfully connected to MongoDB!");
//     } finally {
//         // Ensures that the client will close when you finish/error
//         await client.close();
//     }
// }
// run().catch(console.dir);

async function connectToMongo() {
    try {
        // Connect the client to the server
        await client.connect();
        // Send a ping to confirm a successful connection
        await client.db("admin").command({ ping: 1 });
        console.log("✅ Successfully connected to MongoDB Atlas!");
    } catch (err) {
        console.error("❌ MongoDB Connection Error:");
        console.error(err.message);
        // If it's an auth error, specifically warn about credentials
        if (err.message.includes("Authentication failed")) {
            console.warn("TIP: Check your .env file for extra spaces or quotes in MONGODB_PASSWORD.");
        }
    }
}

// TODO: connect database by uncommenting the below
// connectToMongo();

app.use(express.json());

app.get('/healthcheck', (_, res) => {
    return res.status(200).json({ "status": "alive" })
});

// Route: GET /songs/matches?book=John&startChapter=3&startVerse=16...
app.get('/songs/matches', async (req, res) => {
    console.log("Received request for /songs/matches...");
    try {
        // Extract raw query params
        const { book, startChapter, startVerse, endChapter, endVerse } = req.query;

        if (!book) {
            return res.status(400).json({ error: "Book parameter is required." });
        }

        // Pass raw values to extraction logic
        const passage = extractPassage(
            book,
            startChapter, // String: e.g. "1" or undefined
            startVerse,   // String: e.g. "1", "start", or undefined
            endChapter,   // String: e.g. "1" or undefined
            endVerse      // String: e.g. "2", "end" or undefined
        );

        console.log("Extracting lyrics of all songs...");
        const songs = getAllLyrics().map(s => ({ name: s.songName, lyrics: s.lyrics }));

        // Call to SelahSearch NLP Agent in Hugging Face Space
        const HF_TOKEN = process.env.HF_TOKEN;
        const HF_SPACE_URL = process.env.HF_SPACE_URL; // e.g., https://user-space.hf.space
        // const HF_URL = process.env.HF_SPACE_URL + '/analyse';

        console.log("Connecting to the NLP worker...");
        const client = await Client.connect(HF_SPACE_URL, {
            token: HF_TOKEN // Required for private Spaces
        });

        console.log("Connection successful. Calling the model...");
        const response = await client.predict(`/predict`, {
            // const response = await axiosx.post(`${ HF_SPACE_URL }/run/predict`, {
            passage_text: passage.text,
            songs_json: JSON.stringify(songs)
        }, {
            headers: {
                'Authorization': `Bearer ${ HF_TOKEN }`
            },
            timeout: 60000
        });

        // Gradio returns results inside an 'data' array
        const results = response.data[0];
        if (results && results.error) {
            console.error("NLP Agent Logic Error:", results.error);
            return res.status(422).json({
                error: "The NLP agent processed the request but encountered a logic error.",
                details: results.error
            });
        }

        console.log("Returning response packet...");
        res.json({
            search_query: {
                book: passage.resolved.book,
                startChapter: passage.resolved.startChapter,
                startVerse: passage.resolved.startVerse,
                endChapter: passage.resolved.endChapter,
                endVerse: passage.resolved.endVerse,
                passageSnippet: passage.text.substring(0, 100) + (passage.text.length > 100 ? "..." : "")
            },
            total_matches: results.length,
            matches: results
        });
        // const nlpResponse = await axios.post(HF_URL, {
        //     passage: passage.text,
        //     songs: songs
        // }, {
        //     headers: {
        //         'Authorization': `Bearer ${ HF_TOKEN }`,
        //         'Content-Type': 'application/json'
        //     },
        //     timeout: 30000 // 30-second timeout for large song lists
        // });

        // // 4. Return the structured results
        // const results = nlpResponse.data;
        // res.json({
        //     search_query: {
        //         book: passage.resolved.book,
        //         startChapter: passage.resolved.startChapter,
        //         startVerse: passage.resolved.startVerse,
        //         endChapter: passage.resolved.endChapter,
        //         endVerse: passage.resolved.endVerse,
        //         passageSnippet: passage.text.substring(0, 100) + (passage.text.length > 100 ? "..." : "")
        //     },
        //     total_matches: results.length,
        //     matches: results
        // });

    } catch (error) {
        console.error("Gateway Error:", error.response?.data || error.message);

        if (error.response?.status === 503 || error.code === 'ECONNABORTED') {
            return res.status(503).json({
                error: "NLP Agent is currently waking up or overwhelmed. Please retry in a moment."
            });
        }
        // // Handle "Cold Start" on Hugging Face (if space is sleeping)
        // if (error.code === 'ECONNABORTED' || error.response?.status === 503) {
        //     return res.status(503).json({
        //         error: "NLP Worker is waking up. Please retry in 30 seconds."
        //     });
        // }

        const msg = error.message;
        let statusCode = (msg.includes("does not exist") || msg.includes("out of bounds")) ? 404 : 400;
        res.status(statusCode).json({ error: msg });
    }
});

app.get('/songs/matches/v1', async (req, res) => {
    console.log("Received request for /songs/matches...");
    try {
        // Extract raw query params
        const { book, startChapter, startVerse, endChapter, endVerse } = req.query;

        if (!book) {
            return res.status(400).json({ error: "Book parameter is required." });
        }

        // Pass raw values to extraction logic
        const passage = extractPassage(
            book,
            startChapter, // String: e.g. "1" or undefined
            startVerse,   // String: e.g. "1", "start", or undefined
            endChapter,   // String: e.g. "1" or undefined
            endVerse      // String: e.g. "2", "end" or undefined
        );

        const songs = getAllLyrics().map(s => ({ name: s.songName, lyrics: s.lyrics }));

        // NLP Model Process
        const pyProcess = spawn('python3', ['src/model.py']);
        let pythonData = "";
        let pythonError = "";
        console.log("Running the transformer model...");

        pyProcess.stdin.write(JSON.stringify({ passage: passage.text, songs: songs }));
        pyProcess.stdin.end();

        pyProcess.stdout.on('data', (data) => pythonData += data.toString());
        pyProcess.stderr.on('data', (data) => pythonError += data.toString());

        pyProcess.on('close', (code) => {
            if (code !== 0) {
                return res.status(500).json({ error: "NLP Worker failed", details: pythonError });
            }
            try {
                console.log("Sending response packet...\n");
                const results = JSON.parse(pythonData);

                res.json({
                    search_query: {
                        book: passage.resolved.book,
                        startChapter: passage.resolved.startChapter,
                        startVerse: passage.resolved.startVerse,
                        endChapter: passage.resolved.endChapter,
                        endVerse: passage.resolved.endVerse,
                        passageSnippet: passage.text.substring(0, 100) + (passage.text.length > 100 ? "..." : "")
                    },
                    total_matches: results.length,
                    matches: results
                });
            } catch (e) {
                res.status(500).json({ error: "Failed to parse NLP results" });
            }
        });

    } catch (error) {
        const msg = error.message;
        let statusCode = (msg.includes("does not exist") || msg.includes("out of bounds")) ? 404 : 400;
        res.status(statusCode).json({ error: msg });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`\nSelahSearch API listening on port ${ PORT }...\n`));