const fs = require('fs');
const path = require('path');

const BIBLE_PATH = 'src/bible.txt';
const LYRICS_DIR = 'src/lyrics/';

function formatBookName(bookInput) {
    let book = bookInput.trim().toLowerCase();
    const aliases = { "song of songs": "song of solomon", "psalm": "psalms" };
    if (aliases[book]) book = aliases[book];
    book = book.replace(/(^\w|\s\w)/g, m => m.toUpperCase());
    return book.replace(/\sOf\s/g, " of ");
}

function retrieveBible() {
    try {
        const data = fs.readFileSync(BIBLE_PATH, 'utf8');
        const lines = data.split('\n').slice(3);
        const bible = new Map();
        const books = new Set();
        lines.forEach(line => {
            if (!line.includes('\t')) return;
            const [ref, content] = line.trim().split('\t');
            bible.set(ref, content);
            const bookName = ref.replace(/[0-9:!@#$%^&*()_+={}\[\]|\\:;"'<>,.?/-]+$/, '').trim();
            books.add(bookName);
        });
        return { bible, books: Array.from(books) };
    } catch (err) {
        return { bible: new Map(), books: [] };
    }
}

function getMaxChapters(bible, book) {
    let maxCh = 0;
    for (let key of bible.keys()) {
        if (key.startsWith(book + " ")) {
            const parts = key.split(" ");
            const chVs = parts[parts.length - 1].split(":");
            maxCh = Math.max(maxCh, parseInt(chVs[0]));
        }
    }
    return maxCh;
}

function getMaxVerses(bible, book, chapter) {
    let count = 0;
    const prefix = `${ book } ${ chapter }:`;
    for (let key of bible.keys()) {
        if (key.startsWith(prefix)) count++;
    }
    return count;
}

function extractPassage(bookInput, startCh, startVs, endCh, endVs) {
    const { bible, books } = retrieveBible();
    if (books.length === 0) throw new Error(`unable to retrieve bible contents: bible does not exist`);
    const book = formatBookName(bookInput);

    if (!books.includes(book)) throw new Error(`book does not exist in the bible`);

    // If any other param exists but startChapter is missing
    if (!startCh && (startVs || endCh || endVs)) {
        throw new Error("startChapter is required when specifying verses or end chapters.");
    }

    let sCh, sVs, eCh, eVs;

    // Resolve chapters
    if (!startCh) {
        // Entire Book Mode
        sCh = 1;
        eCh = getMaxChapters(bible, book);
    } else {
        sCh = parseInt(startCh);
        eCh = endCh ? parseInt(endCh) : sCh;
    }

    // Resolve verses
    const isFullChapterMode = (!startVs && !endVs);

    if (isFullChapterMode) {
        sVs = 1;
        eVs = getMaxVerses(bible, book, eCh);
    } else {
        // Start Verse Logic
        sVs = (startVs === 'start' || !startVs) ? 1 : parseInt(startVs);

        // End Verse Logic
        if (endVs === 'end') {
            eVs = getMaxVerses(bible, book, eCh);
        } else if (!endVs) {
            // If endChapter is different from startChapter, default to end of that chapter
            // Otherwise, default to single verse (startVerse)
            eVs = (eCh !== sCh) ? getMaxVerses(bible, book, eCh) : sVs;
        } else {
            eVs = parseInt(endVs);
        }
    }

    // Validation
    if (eCh < sCh) throw new Error("endChapter must be greater or equal to startChapter");
    if (eCh === sCh && eVs < sVs) throw new Error("endVerse must be greater or equal to startVerse");

    // Coordinate Bounds Check
    const startRef = `${ book } ${ sCh }:${ sVs }`;
    const endRef = `${ book } ${ eCh }:${ eVs }`;
    if (!bible.has(startRef) || !bible.has(endRef)) throw new Error("The chapter and/or verses do not exist in the bible");

    // Extraction
    console.log(`Extracting contents of ${ book } ${ sCh }:${ sVs }-${ eCh }:${ eVs }...`);

    let content = "";
    for (let c = sCh; c <= eCh; c++) {
        const start = (c === sCh) ? sVs : 1;
        const end = (c === eCh) ? eVs : getMaxVerses(bible, book, c);
        for (let v = start; v <= end; v++) {
            content += (bible.get(`${ book } ${ c }:${ v }`) || "") + " ";
        }
    }

    return {
        text: content.trim(),
        resolved: {
            book,
            startChapter: sCh,
            startVerse: sVs,
            endChapter: eCh,
            endVerse: eVs
        }
    };
}

// TODO: refactor this to include the artist name at top of each file and filter that out...
function getAllLyrics() {
    // Current: Reads from /lyrics folder. Future: fetch from MongoDB.
    const files = fs.readdirSync(LYRICS_DIR).filter(f => f.endsWith('.txt')).sort();
    return files.map(file => {
        const fullPath = path.join(LYRICS_DIR, file);
        return {
            filename: file,
            songName: file.replace('.txt', '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
            artist: "", // TODO: fill this in
            lyrics: fs.readFileSync(fullPath, 'utf8').trim()
        };
    });
}

module.exports = { extractPassage, getAllLyrics, formatBookName };